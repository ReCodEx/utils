<?php

require_once(__DIR__ . '/BaseCommand.php');
require_once(__DIR__ . '/helpers.php');


class Runtimes extends BaseCommand
{
    private function updateExerciseConfigs($updater, $printProgress = false)
    {
        $configs = $this->getExercisesConfigs();
        foreach ($configs as $id => $config) {
            $yaml = @yaml_parse($config);
            if ($yaml === false) {
                echo "Config $id is not valid YAML.\n";
                yaml_parse($config); // this way we'll see the errors
                continue;
            }
            
            $newYaml = $updater($id, $yaml);
            if ($newYaml !== $yaml) {
                $this->db->query('UPDATE exercise_config SET', ['config' => yaml_emit($newYaml)], 'WHERE id = ?', $id);
            }

            if ($printProgress) {
                echo ".";
            }
        }
    }

    private static function matchPipelineParams($p1, $p2)
    {
        if (count($p1) !== count($p2)) return false;
        foreach ($p1 as $key => $value) {
            if (!array_key_exists($key, $p2) || $value !== $p2[$key]) return false;
        }
        return true;
    }

    private function matchPipelinesByProperties($oldPipelines, $newPipelines)
    {
        $newPipelinesFlags = [];
        foreach ($newPipelines as $p) {
            $newPipelinesFlags[$p] = $this->getPipelineBoolParameters($p);
        }
        
        $pipelinesMapping = [];
        foreach ($oldPipelines as $p) {
            $params = $this->getPipelineBoolParameters($p);
            $candidates = array_filter($newPipelines, function ($new) use ($newPipelinesFlags, $params) {
                return self::matchPipelineParams($params, $newPipelinesFlags[$new]);
            });

            if (count($candidates) !== 1) {
                echo "Pipeline $p has no match in new environment.\n";
                return false;
            }

            $new = reset($candidates);
            $pipelinesMapping[$p] = $new;
            $newPipelines = array_filter($newPipelines, function ($p) use ($new) { return $p !== $new; });
        }
        return $pipelinesMapping;
    }


    /*
     * Public interface
     */

    /**
     * Try to migrate all exercises, assignments, and solutions from one environment to another one.
     * The environments must have compatible pipelines -- i.e., for each pipeline of old environments must be exactly
     * one matching pipeline in the new environment (and it must have the same input variables).
     */
    public function migrate($oldEnv, $newEnv)
    {
        echo "Migration of environment $oldEnv to $newEnv.\n";
        $this->db->begin();

        try {
            $oldPipelines = $this->getRuntimePipelinesIds($oldEnv);
            $newPipelines = $this->getRuntimePipelinesIds($newEnv);
            if (count($oldPipelines) !== count($newPipelines)) {
                echo "Unable to match pipeline!\n";
                $this->db->rollback();
                return;
            }

            $pipelinesMapping = $this->matchPipelinesByProperties($oldPipelines, $newPipelines);
            if (!$pipelinesMapping) {
                echo "Unable to match pipelines!\n";
                $this->db->rollback();
                return;
            }

            // Start with simple table FK updates...
            $tables = [
                'exercise_runtime_environment',
                'exercise_environment_config',
                'exercise_limits',
                'assignment_runtime_environment',
                'assignment_disabled_runtime_environments',
                'solution'
            ];
            foreach ($tables as $table) {
                echo "Updating $table table...\n";
                $this->db->query("UPDATE $table SET", ['runtime_environment_id' => $newEnv], 'WHERE runtime_environment_id = ?', $oldEnv);
            }
        
            echo "\nThe migration will use the following mapping of the pipelines:\n";
            foreach ($pipelinesMapping as $old => $new) {
                echo $this->getPipeline($old)['name'], ' -> ', $this->getPipeline($new)['name'], "\n";
            }

            echo "\nUpdating exercise configs ...";
            $this->updateExerciseConfigs(function ($id, $config) use ($oldEnv, $newEnv, $pipelinesMapping) {
                if (in_array($oldEnv, $config['environments']) && !in_array($newEnv, $config['environments'])) {
                    // Replace environment name
                    $config['environments'] = array_map(function ($env) use ($oldEnv, $newEnv) {
                        return ($env === $oldEnv) ? $newEnv : $env;
                    }, $config['environments']);

                    foreach ($config['tests'] as &$test) {
                        if (!array_key_exists($oldEnv, $test['environments']) || array_key_exists($newEnv, $test['environments'])) {
                            continue;
                        }

                        $newPipelines = [];
                        foreach ($test['environments'][$oldEnv]['pipelines'] as $pipeline) {
                            if (!array_key_exists($pipeline['name'], $pipelinesMapping)) {
                                echo "Unable to find match for pipeline {$pipeline['name']} in exercise $id!\n";
                                return $config;
                            }
                            $pipeline['name'] = $pipelinesMapping[$pipeline['name']];
                            $newPipelines[] = $pipeline;
                        }
                        $test['environments'][$newEnv] = $test['environments'][$oldEnv];
                        $test['environments'][$newEnv]['pipelines'] = $newPipelines;
                        unset($test['environments'][$oldEnv]);
                    }
                }
                return $config;
            }, true);
            echo "\n";

            $this->db->commit();
            echo "COMIT!\n";
        } catch (Exception $e) {
            $this->db->rollback();
            throw $e;
        }
    }
}
