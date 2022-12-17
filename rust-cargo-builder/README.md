The builder creates a project template package `project.zip` which is to be used in the cargo rust compilation pipeline. The project contains vendor-locked dependencies and their pre-compiled binaries.

Before executing `build-project.sh`, make sure that `/box` directory exists and the current user can write into it.

The `compile.sh` is the compilation wrapper used in the pipeline (not actually part of the builder, but it is related).
