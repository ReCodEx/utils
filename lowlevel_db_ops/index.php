<?php

require_once('vendor/autoload.php');


function recodex_lowlevel_db_ops_main($argv) {
    foreach (glob('commands/*.php') as $file) {
        require_once($file);
    }


    array_shift($argv);    // skip script name

    if (empty($argv[0])) {
        echo "No command provided.\n";
        die;
    }

    list($class, $method) = explode(':', array_shift($argv));
    if (!class_exists($class)) {
        throw new Exception("Class $class not found.");
    }

    // Init DB...
    $config = require('config/config.ini.php');
    if (!$config) {
        throw new Exception("No config found");
    }
    $database = new Dibi\Connection($config);

    $command = new $class($database);
    if (!method_exists($command, $method)) {
        throw new Exception("Method $method does not exists in class $class.");
    }
    
    $command->$method(...$argv);
}


try {
    recodex_lowlevel_db_ops_main($argv);
} catch (Exception $e) {
    echo "Error: ", $e->getMessage(), "\n";
    exit(1);
}
