#!/usr/bin/env python3

import sys

[referenceFile, resultFile] = sys.argv[1:] 
error = ""

#
# Compare the results....
# 

# Print the output.
if (error):
    print("0.0")
    print(error)
    sys.exit(1)
else:
    print("1.0")
    sys.exit(0)
