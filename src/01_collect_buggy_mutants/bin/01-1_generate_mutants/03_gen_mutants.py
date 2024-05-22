#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import time
import multiprocessing

# Current working directory
script_path = Path(__file__).resolve()
gen_mutants_dir = script_path.parent
bin_dir = gen_mutants_dir.parent
collect_buggy_mutants_dir = bin_dir.parent

# General directories
src_dir = collect_buggy_mutants_dir.parent
root_dir = src_dir.parent
user_configs_dir = root_dir / 'user_configs'
subjects_dir = root_dir / 'subjects'
external_tools_dir = root_dir / 'external_tools'

# keywords in configurations.json
config_sh_wd_key = 'configure_script_working_directory'
build_sh_wd_key = 'build_script_working_directory'

# files in user_configs_dir
configure_no_cov_script = 'configure_no_cov_script.sh'
configure_yes_cov_script = 'configure_yes_cov_script.sh'
build_script = 'build_script.sh'
clean_script = 'clean_script.sh'
machines_json_file = 'machines.json'
configure_json_file = 'configurations.json'

# /home/yangheechan/mbfl-dataset-gen/structure-project/MUSICUP/music
# /home/yangheechan/mbfl-dataset-gen/structure-project/MUSICUP/jsoncpp_template/src/lib_json/json_reader.cpp
# -o /home/yangheechan/mbfl-dataset-gen/structure-project/MUSICUP/outputs.0/mutations-json_reader.cpp
# -l 1 -p /home/yangheechan/mbfl-dataset-gen/structure-project/MUSICUP/jsoncpp_template/build/compile_commands.json
# > /home/yangheechan/mbfl-dataset-gen/structure-project/MUSICUP/outputs.0/mutations-json_reader.cpp/output.0 2>&1

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject)

def read_configs(subject_name, subject_working_dir):
    global configure_json_file

    subject_config_dir = subject_working_dir / f"{subject_name}-configures"
    assert subject_config_dir.exists(), f"Subject configurations directory {subject_config_dir} does not exist"

    config_json = subject_config_dir / configure_json_file
    assert config_json.exists(), f"Configurations file {config_json} does not exist"
    
    configs = None
    with config_json.open() as f:
        configs = json.load(f)
    
    if configs is None:
        raise Exception('Configurations are not loaded')
    
    return configs

def start_process(subject_name):
    global configure_json_file

    subject_working_dir = collect_buggy_mutants_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. initiate mutants directory and return music command
    worksTodo = initiate_mutants_dir(subject_working_dir, configs['target_files'])

    # 3. get music command
    music_cmd = subject_working_dir / 'external_tools/music'
    assert music_cmd.exists(), f'MUSICUP is not built. Please build MUSICUP first.'

    # 4. generate mutants
    generate_mutants(subject_working_dir, worksTodo, music_cmd, configs['compile_command_path'])

    # 5. Show statistics
    show_statistics(subject_working_dir, worksTodo)

    # 6. execute clean_script
    exec_clean_script(configs[build_sh_wd_key], subject_working_dir)


def initiate_mutants_dir(subject_working_dir, target_files):
    mutants_dir = subject_working_dir / 'generated_mutants'
    mutants_dir.mkdir(exist_ok=True, parents=True)

    target_file_pair = []

    for target_file in target_files:
        target_file_path = subject_working_dir / Path(target_file)
        assert target_file_path.exists(), f'{target_file_path} does not exist'

        target_file_name = target_file.replace('/', '-')
        single_file_mutant_dir = mutants_dir / f"{target_file_name}"
        single_file_mutant_dir.mkdir(exist_ok=True, parents=True)

        target_file_pair.append((target_file_path, single_file_mutant_dir))
    
    print('Initiated mutants directory')
    return target_file_pair

def generate_mutants(subject_working_dir, worksTodo, music_cmd, compile_command):
    compile_command = subject_working_dir / compile_command
    assert compile_command.exists(), f'{compile_command} does not exist'

    start_time = time.time()
    individual_time_list = []

    jobs = []
    for target_file, output_dir in worksTodo:
        proc = multiprocessing.Process(
            target=gen_mutants_worker,
            args=(target_file, output_dir, compile_command, music_cmd)
        )
        jobs.append(proc)
        proc.start()
    
    for job in jobs:
        job.join()
    
    end_time = time.time()
    total_time = end_time - start_time
    print(f'Total time taken: {total_time} seconds')


not_using_operators = [
    "DirVarAriNeg", "DirVarBitNeg", "DirVarLogNeg", "DirVarIncDec",
    "DirVarRepReq", "DirVarRepCon", "DirVarRepPar", "DirVarRepGlo", 
    "DirVarRepExt", "DirVarRepLoc", "IndVarAriNeg", "IndVarBitNeg", 
    "IndVarLogNeg", "IndVarIncDec", "IndVarRepReq", "IndVarRepCon", 
    "IndVarRepPar", "IndVarRepGlo", "IndVarRepExt", "IndVarRepLoc",
    "SSDL", "CovAllNod", "CovAllEdg", "STRP", "STRI", "VDTR",
    "RetStaDel", "FunCalDel"
]

def gen_mutants_worker(target_file, output_dir, compile_command, music_cmd):
    unused_ops = ",".join(not_using_operators)

    cmd = [
        music_cmd,
        str(target_file),
        '-o', str(output_dir),
        '-ll', '1',
        '-l', '2',
        '-d', unused_ops,
        '-p', str(compile_command)
    ]
    # print(cmd)

    print(f'Generating mutants for {target_file}...')
    start_time = time.time()
    res = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    end_time = time.time()
    total_time = end_time - start_time

    if res.returncode != 0:
        raise Exception(f'Failed to generate mutants for {target_file}')
    
    print(f'Finished generating mutants for {target_file}, time taken: {total_time} seconds')

# ./../../external_tools/MUSICUP/music
# /home/yangheechan/mbfl-dataset-gen/LIGNex1_FL_dataset_LIBXML2/working_directory/libxml2/parser.c
#  -o /home/yangheechan/mbfl-dataset-gen/LIGNex1_FL_dataset_LIBXML2/working_directory/libxml2/mutations/parser.c
# -l 1 -p /home/yangheechan/mbfl-dataset-gen/LIGNex1_FL_dataset_LIBXML2/working_directory/libxml2/compile_commands.json


def show_statistics(subject_working_dir, worksTodo):
    total_mutant_cnt = 0
    mutant_cnt_per_file = {}

    for target_file, output_dir in worksTodo:
        mutant_files = list(output_dir.glob('*.c'))
        mutant_cnt = len(mutant_files)
        total_mutant_cnt += mutant_cnt
        mutant_cnt_per_file[target_file] = mutant_cnt
    
    print(f'\n\n> Total mutants generated: {total_mutant_cnt}')
    print('>Mutants per file:')
    for target_file, mutant_cnt in mutant_cnt_per_file.items():
        print(f'{target_file}: {mutant_cnt}')


def exec_clean_script(build_sh_wd, subject_working_dir):
    global clean_script

    build_sh_wd = subject_working_dir / build_sh_wd
    clean_build_sh = build_sh_wd / clean_script
    assert clean_build_sh.exists(), f"Clean build script {clean_build_sh} does not exist"

    cmd = ['bash', clean_build_sh]
    res = sp.run(cmd, cwd=build_sh_wd)
    if res.returncode != 0:
        raise Exception('Failed to execute clean build script')
    
    print('Executed clean build script')


    
def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    return parser

if __name__ == "__main__":
    main()
