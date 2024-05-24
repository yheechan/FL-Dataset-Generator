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
    parser = make_parser()
    args = parser.parse_args()
    tc_list = get_tc_lists(args.testsuite_name)
    run_testsuite(tc_list)


def run_testsuite(tc_list):
    global target_gcno_gcda, filtered_files

    failing_tc = []
    passing_tc = []

    time_list = []
    exec_list = []

    all_start_time = time.time()
    
    for tc_script in tc_list:
        # tc_script: (ex TC123.sh)

        tc_start_time = time.time()

        # 1. reset coverage
        remove_all_gcda()

        # 2. run testcase
        tc_exec_start_time = time.time()
        res = run_tc(tc_script)
        res = run_tc(tc_script)
        if res == 0:
            passing_tc.append(tc_script)
        else:
            failing_tc.append(tc_script)
        tc_exec_end_time = time.time()
        tc_exec_time = tc_exec_end_time - tc_exec_start_time

        # 3. limit to target files
        remove_untargeted_files_for_coverage(target_gcno_gcda)

        # 4. generate coverage json
        raw_cov = generate_coverage_json(tc_script, filtered_files)
        # summary_cov = generate_summary_json(tc_script, filtered_files)

        tc_end_time = time.time()
        tc_time = tc_end_time - tc_start_time

        # save time and exec time
        time_list.append(tc_time)
        exec_list.append(tc_exec_time)

    all_end_time = time.time()
    all_total_time = all_end_time - all_start_time

    print(f"\nTotal time: {all_total_time} seconds\n")
    tc_cnt = len(tc_list)
    print(f"Average of {tc_cnt} testcases:")
    print(f"\t - time: {sum(time_list) / len(time_list)} seconds")
    print(f"\t - exec: {sum(exec_list) / len(exec_list)} seconds")

    print("> failing TCs:")
    for idx, failing in enumerate(failing_tc):
        print(f"\t{idx+1}. {failing}")



def run_tc(tc_script):
    global my_env, tc_dir
    cmd = f"./{tc_script}"
    res = sp.run(cmd, shell=True, cwd=tc_dir, stdout=sp.PIPE, stderr=sp.PIPE, env=my_env) #, timeout=1)

    # if res.returncode != 0:
    #     print(f"Testcase {tc_script} failed")
    #     print(f"cmd: {cmd}")
    #     print(f"stdout: {res.stdout}")
    #     print(f"stderr: {res.stderr}")
    #     print(f"returncode: {res.returncode}")
    
    return res.returncode




def get_tc_lists(testsuite_name):
    testsuite_file = Path(testsuite_name)
    assert testsuite_file.exists(), f"Test suite file {testsuite_file} does not exist"

    tc_list = []
    with open(testsuite_file, 'r') as f:
        for line in f:
            tc_list.append(line.strip())
    
    tc_list = sorted(tc_list, key=custome_sort)

    return tc_list

def custome_sort(tc_script):
    tc_filename = tc_script.split('.')[0]
    return int(tc_filename[2:])


def remove_all_gcda():
    global libxml2_dir
    cmd = [
        'find', '.', '-type',
        'f', '-name', '*.gcda',
        '-delete'
    ]
    res = sp.call(cmd, cwd=libxml2_dir)

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


def generate_coverage_json(tc_id, filtered_files):
    global gcovr, libxml2_dir, cov_dir

    tc_name = tc_id.split('.')[0]
    file_name = tc_name + '.raw.json'
    file_path = cov_dir / file_name
    file_path = file_path.resolve()
    cmd = [
        gcovr,
        '--filter', filtered_files,
        '--gcov-executable', 'llvm-cov gcov',
        # '--json',
        '--json-pretty',
        '-o', file_path
    ]
    # print(cmd)
    res = sp.call(cmd, cwd=libxml2_dir)
    return file_path

def generate_summary_json(tc_id, filtered_files):
    global gcovr, libxml2_dir, cov_dir

    tc_name = tc_id.split('.')[0]
    file_name = tc_name + '.summary.json'
    file_path = cov_dir / file_name
    file_path = file_path.resolve()
    cmd = [
        gcovr,
        '--filter', filtered_files,
        '--gcov-executable', 'llvm-cov gcov',
        # '--json-summary',
        '--json-summary-pretty',
        '-o', file_path
    ]
    # print(cmd)
    res = sp.call(cmd, cwd=libxml2_dir)
    return file_path


def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--testsuite-name', type=str, help='Name of testsuite file', required=True)
    return parser

if __name__ == '__main__':
    main()
