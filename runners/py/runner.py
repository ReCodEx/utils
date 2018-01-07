#!/usr/bin/env python

import sys
from pathlib import Path
from pkgutil import read_code

# Remove the name of the runner
sys.argv.pop(0)

# Read the input file
script = Path(sys.argv[0])

with script.open('rb') as script_file:
    # If we received a source file, compile it (and leave bytecode as is)
    if script.suffix != ".pyc":
        code = compile(script_file.read(), str(script), "exec")
    else:
        code = read_code(script_file)

# Run the code and convert exceptions to error codes
try:
    exec(code)
except IOError:
    sys.exit(106);
except OSError:
    sys.exit(107)
except IndexError:
    sys.exit(108)
except KeyError:
    sys.exit(108)
except ValueError:
    sys.exit(108)
except ZeroDivisionError:
    sys.exit(109)
except ArithmeticError:
    sys.exit(110)
except ModuleNotFoundError:
    sys.exit(111)
except BaseException:
    sys.exit(1)
