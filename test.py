#!/usr/bin/python3

import subprocess as sp

sp.run("./test.sh", shell=True)
print("execed")

sp.run("echo $HCY", shell=True)

