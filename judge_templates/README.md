# Judge Templates

Here we present templates for ReCodEx judges in various languages. Please remember, that the judge receives two command line parameters -- first one is expected output, second one result from tested program. The judge reports its result primarily by its exit code:

* 0 = solution is OK
* 1 = solution is wrong
* 2 = internal error

If the tested output is deemed OK, the judge may optionally yield a float number between `1.0` and `0.0` which indicate actual correctness (`1.0` meaning 100% correct solution). It is allowed to yield OK as exit code and `0.0` as the correctness value. Semantics of such judgement is that the result is formally OK, but does not deserve any points. ReCodEx uses the float value yielded by the judge as a scoring weight (actual points received for the test are multiplied by this float and rounded).

Additionally, the judge may write a log to the stdout. All lines (except the first line, where the float value is) are collected as a log. This log is displayed directly in ReCodEx individually for each failed test. Please note, that there are size limits imposed, so it is a good idea to keep the log as brief as possible.


## ELF Judges

First option is to create a judge a statically linked ELF. All current workers use most recent version of CentOS, so it is higly recommended to compile the ELF on compatible linux system.

In case of C++, no judge template is provided, but you may utilize [ReCodEx Token Judge](https://github.com/ReCodEx/worker/tree/master/judges/recodex_token_judge), which is part of the [worker](https://github.com/ReCodEx/worker).


## Script Judges

Script judges can be executed as well, but they must have correct first line that identifies the interpret application. For instance
```
#!/usr/bin/bash
```

Some interprets has to be called in special manner (e.g., Python) or require alternate config file (e.g., PHP). See the presented templates which are already tailored for our workers and their environment.


## Judges Executed in Runtimes

This concerns judges written in Java or C#, so they need JRE or Mono to execute them. At present, it is rather tricky to use these judges. In general, you need to write a bootstrap wrapper (e.g., as a script judge), which will start them. The problem is that under current configuration, a judge has to be a single file, so you need a safe way how to wrap the Java/C# judge into the script file itself (which may be rather ugly).

There is one exception -- *Data-only* exercises. Data-only exercise allows *extra files* to be passed on to the judge. So jar or C# executable can be passed on to the judge as extra file and judge (e.g., bash script) only executes this file and pass on the command line arguments.


## Judges in Data-only Exercises

Data-only exercises need judges as well. In fact, in data-only exercise, the judge takes place of regular solution execution, so it is subjected to time and memory limits. There is a slight difference in data-only judges in the interface as this judge does not get any arguments automatically. Instead, it may get custom (execution) arguments set in the config form. Submitted files along with the script itself and extra files end up in one directory which is the working directory when the script is executed. Please note that the sandbox may have additional temporary files in there like a `.stdout` file which collects the std. output of the judge.  
