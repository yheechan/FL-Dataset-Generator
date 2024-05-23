#!/usr/bin/python3

import sys
import subprocess as sp
from pathlib import Path
import argparse
import time
import os

subjects = Path('subjects')
libxml2_dir = Path('libxml2')
testcases_dir = Path('libxml2/testcases')
gcovr = Path('/home/yangheechan/.local/bin/gcovr')
cov_dir = Path('cov')

my_env = os.environ.copy()
lib = Path('libxml2/.libs').resolve()

if 'LD_LIBRARY_PATH' in my_env:
    my_env['LD_LIBRARY_PATH'] = str(lib) + ':' + my_env['LD_LIBRARY_PATH']
else:
    my_env['LD_LIBRARY_PATH'] = str(lib)

def custome_sort(tc_script):
    tc_filename = tc_script.split('.')[0]
    return int(tc_filename[2:])

def get_tc_lists():
    tc_lists = []
    # add test case scripts in testcase directory in order
    for tc_script in testcases_dir.iterdir():
        if tc_script.suffix == '.sh':
            tc_lists.append(tc_script.name)
    tc_lists = sorted(tc_lists, key=custome_sort)
    return tc_lists

def run_tc(tc_script):
    # cmd = ["bash", f"{tc_script}"]
    # cmd = "{}".format(tc_script)
    cmd = f"./{tc_script}"
    try:
        # res = sp.run(cmd, cwd=testcases_dir, stdout=sp.PIPE, stderr=sp.PIPE, timeout=1)
        res = sp.run(cmd, shell=True, cwd=testcases_dir, stdout=sp.PIPE, stderr=sp.PIPE, env=my_env)
    except sp.TimeoutExpired:
        print(f"Testcase {tc_script} timeout")
        return -1

    if res.returncode != 0:
        print(f"Testcase {tc_script} failed")
        print(f"cmd: {cmd}")
        print(f"stdout: {res.stdout}")
        print(f"stderr: {res.stderr}")
        print(f"returncode: {res.returncode}")
    
    return res.returncode

def remove_all_gcda():
    cmd = [
        'find', '.', '-type',
        'f', '-name', '*.gcda',
        '-delete'
    ]
    res = sp.call(cmd, cwd=libxml2_dir)

def remove_untargeted_files_for_coverage(new_targets):
    # remove all files that are *.gcno and *.gcda
    # except <target_files>.gcno <target_files>.gcda files
    cmd = ['find', '.', '-type', 'f', '(', '-name', '*.gcno', '-o', '-name', '*.gcda', ')']
             
    for target_file in new_targets:
        cmd.extend(['!', '-name', target_file])
    cmd.extend(['-delete'])

    # print(cmd)
    res = sp.call(cmd, cwd=libxml2_dir)

def generate_coverage_json(tc_id):
    file_name = tc_id + '.raw.json'
    file_path = cov_dir / file_name
    file_path = file_path.resolve()
    cmd = [
        gcovr,
        '--gcov-executable', 'llvm-cov gcov',
        '--json', '-o', file_path
    ]
    # print(cmd)
    res = sp.call(cmd, cwd=libxml2_dir)
    return file_path

def generate_summary_json(tc_id):
    file_name = tc_id + '.summary.json'
    file_path = cov_dir / file_name
    file_path = file_path.resolve()
    cmd = [
        gcovr,
        '--gcov-executable', 'llvm-cov gcov',
        '--json-summary', '-o', file_path
    ]
    # print(cmd)
    res = sp.call(cmd, cwd=libxml2_dir)
    return file_path

def execute_all_tc(tc_list):
    target_files = [
        "parser.c",
        "HTMLparser.c",
        "relaxng.c",
        "xmlregexp.c",
        "xmlschemas.c"
    ]
    filtered_files = "|".join(target_files)

    refined_gcno_targets = []
    refined_gcda_targets = []
    new_targets = []
    for target_file in target_files:
        filename = target_file.split('.')[0]
        gcno_file = '*'+filename+'.gcno'
        new_targets.append(gcno_file)
        gcda_file = '*'+filename+'.gcda'
        new_targets.append(gcda_file)

    
    failing = []
    passing = []

    time_list = []
    exec_list = []
    cov_list = []

    all_start_time = time.time()

    x = 0
    remove_all_gcda()
    for tc_script in tc_list:

        tc_start_time = time.time()

        # 2. run testcase
        tc_exec_start_time = time.time()
        # print("running {}".format(tc_script))
        res = run_tc(tc_script)
        # print("\t res: {}".format(res))
        if res != 0:
            failing.append(tc_script)
        else:
            passing.append(tc_script)

        tc_exec_end_time = time.time()
        tc_exec_time = tc_exec_end_time - tc_exec_start_time
    

        tc_end_time = time.time()
        tc_time = tc_end_time - tc_start_time

        time_list.append(tc_time)
        exec_list.append(tc_exec_time)
        
        # x += 1
        # if x == 10:
        #     break
    
    remove_untargeted_files_for_coverage(new_targets)
    
    all_end_time = time.time()
    all_total_time = all_end_time - all_start_time
    print(f"\nTotal time: {all_total_time} seconds\n")
    tc_cnt = len(tc_list)
    print(f"Average of {tc_cnt} testcases:")
    print(f"\t - time: {sum(time_list) / len(time_list)} seconds")
    print(f"\t - exec: {sum(exec_list) / len(exec_list)} seconds")


    
    with open('failing_tcs.txt', 'w') as f:
        print(">failings")
        for fail in failing:
            failing_name = fail.split('.')[0]
            f.write(failing_name + '\n')
            print(fail)
    
    with open('passing_tcs.txt', 'w') as f:
        for pass_ in passing:
            passing_name = pass_.split('.')[0]
            f.write(passing_name + '\n')


if __name__ == '__main__':
    tc_list = get_tc_lists()
    execute_all_tc(tc_list)
