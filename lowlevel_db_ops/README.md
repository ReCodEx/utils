# ReCodEx Utils: Low Level Database Operations

**Using these operations may be dangerous and may lead to loss of data. Handle with care.**

These operations are designed to operate on ReCodEx API database whilst avoiding ORM model of the API completely. Operations implemented are added on demand and they typically perform integrity checks (which we use for testing complex migrations) or computing statistics for optimization purposes.

To use this utility, you need to set up a `config/config.ini.php` file locally. Use `config/config.ini.php.example` as a template. You will also need to install 3rd party libraries (DiBi) via composer.

The script is a CLI application where `index.php` is the entry point and a crude front-controller/command dispatcher. The call syntax is:

```
$> php ./index.php Module:methodName [ ... args ].
```

The `Module` is the name of the class (e.g., `Exercises`), `methodName` is directly a name of the method of the class (e.g., `verifyTestScores`). Additional CLI arguments are passed on as strings arguments for the method call.
