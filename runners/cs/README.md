# C# Runtime

### Simple C# execution

The simple C# environment uses direct compilation by Roslyn, so it does not require `.csproj` files. However, for execution, the `Program.runtimeconfig.json` file is required to specify the target framework. This file is present in both execution pipelines and it must be updated if the target framework changes on the workers.

### Additional files

- `Reader.cs` - Contains the `Reader` class for reading data. This class was originally created to ease the transition from Pascal to C# where the users were used to simple operations for reading text files. It is mostly deprecated, but preserved for backward compatibility.
- `Wrapper.cs` - Contains the `Wrapper` class which wraps the execution of programs in simple C# environment. The wrapper finds the main method provided by the tested solution (using reflection) and executes it. If the solution throws an exception, the wrapper catches it and returns appropriate exit code (the exit codes are translated to error messages by ReCodEx frontend).

