#!/usr/bin/env python

import sys
from pathlib import Path

# Remove the name of the runner
sys.argv.pop(0)

# Read the input file
script = Path(sys.argv[0])
code = script.read_bytes()

# If we received a source file, compile it (and leave bytecode as is)
if script.suffix != ".pyc":
    code = compile(script.read_bytes(), str(script), "exec")

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
