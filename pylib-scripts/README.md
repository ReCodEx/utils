# ReCodEx script samples

These scripts demonstrate usage of ReCodEx API via [pylib](https://github.com/ReCodEx/pylib) library. You may use them as an inspiration for your own scripts.
You may install the pylib and the CLI tool via pip (some scripts may require additional dependencies):
```
pip install recodex-pylib recodex-cli
```

The pylib is expected to be used with [ReCodEx CLI](https://github.com/ReCodEx/cli). You can initialize your session by generating an API token via ReCodEx web interface (user settings page) and then running the following command in your terminal:
```
recodex login --api-url <url-to-your-recodex-api> --token <your-auth-token>
```
or possibly
```
recodex login --api-url <url-to-your-recodex-api> --prompt-token
```
You may also log in by entering your username and password, if you have a local account:
```
recodex login --api-url <url-to-your-recodex-api> --prompt-credentials
```
Use `recodex login --help` for more options and check `recodex status` to verify that you are logged in properly.

Once you initialized your local recodex session using the CLI tool, the pylib scripts can load the session info and initialize your `Client` object simply using
```python
from recodex import client_factory
client = client_factory.get_client_from_session()
```

**Scripts:**
- [groups.py](groups.py) - lists all root groups (and their admins) as a tree
- [students.py](students.py) - gather all students from a particular subtree of the groups hierarchy and output them in a CSV format
