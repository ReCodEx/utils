# C# Runtime

### Simple C# execution

The simple C# environment uses direct compilation by Roslyn, so it does not require `.csproj` files. However, for execution, the `Program.runtimeconfig.json` file is required to specify the target framework. This file is present in both execution pipelines and it must be updated if the target framework changes on the workers.


### Project C# execution

The compilation is performed using `dotnet build` and allows access to the internet (to download NuGet packages). For safety reasons, there are some limitations imposed by the `build-dotnet.sh` script (which wraps the build). The script:
- Makes sure there is one `.csproj` file in the root of the solution.
- The project uses `Microsoft.NET.Sdk` and does not employ any steps that will trigger code during the build phase (no `<Target>`, `<UsingTask>`, or `<Import>` elements).
- The project does not contain any `.props`, `.targets`, or `.dll` files.
- The loader executable is renamed to `__recodex_exe__`, so it can be easily found by the execution pipeline.
- The whole output directory is zipped to a single file for easier transfer between compilation and execution steps (which are sandbox-ed separately).

The execution also needs a wrapper, but only to invoke the executable file within the binary directory (currently not achievable directly by ReCodEx pipelines). Otherwise, the execution is identical to the simple ELF execution.

### Additional files

- `Reader.cs` - Contains the `Reader` class for reading data. This class was originally created to ease the transition from Pascal to C# where the users were used to simple operations for reading text files. It is mostly deprecated, but preserved for backward compatibility.
- `Wrapper.cs` - Contains the `Wrapper` class which wraps the execution of programs in simple C# environment. The wrapper finds the main method provided by the tested solution (using reflection) and executes it. If the solution throws an exception, the wrapper catches it and returns appropriate exit code (the exit codes are translated to error messages by ReCodEx frontend).

