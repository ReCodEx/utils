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
except AssertionError:
    sys.exit(101)
except TypeError:
    sys.exit(102)
except NameError:
    sys.exit(103)
except EOFError:
    sys.exit(104)
except AttributeError:
    sys.exit(105)
except IOError:
    sys.exit(106)
except OSError:
    sys.exit(107)
except LookupError:
    sys.exit(108)
except ValueError:
    sys.exit(109)
except ZeroDivisionError:
    sys.exit(110)
except ArithmeticError:
    sys.exit(111)
except ImportError:
    sys.exit(112)
except MemoryError:
    sys.exit(113)
except SyntaxError:
    sys.exit(114)
except SystemExit:
    raise
except BaseException:
    sys.exit(1)
