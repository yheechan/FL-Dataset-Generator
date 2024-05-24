#!/usr/bin/python3

import sys
import subprocess as sp
from pathlib import Path
import argparse
import time

import os

subjects = Path('subjects')

# path to gcovr
gcovr = Path('/home/yangheechan/.local/bin/gcovr')

# path to the test case directory
tc_dir = Path('libxml2/testcases')

# path to subject directory
libxml2_dir = Path('libxml2')

# path to coverage directory
cov_dir = Path('cov')

# filter files for coverage
target_files = [
    "libxml2/parser.c",
    "libxml2/HTMLparser.c",
    "libxml2/relaxng.c",
    "libxml2/xmlregexp.c",
    "libxml2/xmlschemas.c"
]
target_files = [file.split('/')[1] for file in target_files]
filtered_files = "|".join(target_files)

target_gcno_gcda = []
for target_file in target_files:
    filename = target_file.split('.')[0]
    gcno_file = '*'+filename+'.gcno'
    target_gcno_gcda.append(gcno_file)
    gcda_file = '*'+filename+'.gcda'
    target_gcno_gcda.append(gcda_file)

# setting environment variable
my_env = os.environ.copy()
lib = Path('libxml2/.libs').resolve()

if 'LD_LIBRARY_PATH' in my_env:
    my_env['LD_LIBRARY_PATH'] = str(lib) + ':' + my_env['LD_LIBRARY_PATH']
else:
    my_env['LD_LIBRARY_PATH'] = str(lib)






def main():
    remove_untargeted_files_for_coverage(target_gcno_gcda)


def remove_untargeted_files_for_coverage(new_targets):
    global libxml2_dir, target_files

    # remove all files that are *.gcno and *.gcda
    # except <target_files>.gcno <target_files>.gcda files
    cmd = ['find', '.', '-type', 'f', '(', '-name', '*.gcno', '-o', '-name', '*.gcda', ')']
             
    for target_file in new_targets:
        cmd.extend(['!', '-name', target_file])
    cmd.extend(['-delete'])

    # print(cmd)
    res = sp.call(cmd, cwd=libxml2_dir)

if __name__ == '__main__':
    main()
