#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import time
import multiprocessing

script_path = Path(__file__).resolve()
bin_dir = script_path.parent
action_dir = bin_dir.parent
src_dir = action_dir.parent

root_dir = src_dir.parent
working_dir = root_dir / 'working_directory'
working_dir.mkdir(exist_ok=True)
user_configs_dir = root_dir / 'user_configs'
subjects_dir = root_dir / 'subjects'
datasets_dir = root_dir / 'datasets'

config_sh_wd = 'configure_script_working_directory'
build_sh_wd = 'build_script_working_directory'
configure_script = 'configure_no_cov_script.sh'
build_script = 'build_script.sh'

musicup = root_dir / 'external_tools' / 'MUSICUP' / 'music'

# /home/yangheechan/mbfl-dataset-gen/structure-project/MUSICUP/music
# /home/yangheechan/mbfl-dataset-gen/structure-project/MUSICUP/jsoncpp_template/src/lib_json/json_reader.cpp
# -o /home/yangheechan/mbfl-dataset-gen/structure-project/MUSICUP/outputs.0/mutations-json_reader.cpp
# -l 1 -p /home/yangheechan/mbfl-dataset-gen/structure-project/MUSICUP/jsoncpp_template/build/compile_commands.json
# > /home/yangheechan/mbfl-dataset-gen/structure-project/MUSICUP/outputs.0/mutations-json_reader.cpp/output.0 2>&1



def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    return parser


def read_configs(subject_name):
    config_json = user_configs_dir / subject_name / 'configurations.json'
    
    configs = None
    with config_json.open() as f:
        configs = json.load(f)
    
    if configs is None:
        raise Exception('Configurations are not loaded')
    
    return configs


def execute_configure_script(config_sh_wd):
    config_sh_wd = working_dir / config_sh_wd
    cmd = ['bash', configure_script]
    res = sp.run(cmd, cwd=config_sh_wd)
    if res.returncode != 0:
        raise Exception('Failed to execute configure script')
    
    print('Executed configure script')

def execute_build_script(build_sh_wd):
    build_sh_wd = working_dir / build_sh_wd
    cmd = ['bash', build_script]
    res = sp.run(cmd, cwd=build_sh_wd)
    if res.returncode != 0:
        raise Exception('Failed to execute build script')
    
    print('Executed build script')

def initiate_mutants_dir(subject_name, target_files):
    mutants_dir = datasets_dir / subject_name / 'generated_mutants'
    mutants_dir.mkdir(exist_ok=True, parents=True)

    target_file_pair = []

    for target_file in target_files:
        target_file_path = working_dir / Path(target_file)
        assert target_file_path.exists(), f'{target_file_path} does not exist'

        target_file_name = target_file_path.name
        single_file_mutant_dir_name = f"mutants-{target_file_name}"
        single_file_mutant_dir = mutants_dir / single_file_mutant_dir_name
        single_file_mutant_dir.mkdir(exist_ok=True, parents=True)

        target_file_pair.append((target_file_path, single_file_mutant_dir))
    
    print('Initiated mutants directory')
    return target_file_pair

# ./../../external_tools/MUSICUP/music
# /home/yangheechan/mbfl-dataset-gen/LIGNex1_FL_dataset_LIBXML2/working_directory/libxml2/parser.c
#  -o /home/yangheechan/mbfl-dataset-gen/LIGNex1_FL_dataset_LIBXML2/working_directory/libxml2/mutations/parser.c
# -l 1 -p /home/yangheechan/mbfl-dataset-gen/LIGNex1_FL_dataset_LIBXML2/working_directory/libxml2/compile_commands.json

not_using_operators = [
    "DirVarAriNeg", "DirVarBitNeg", "DirVarLogNeg", "DirVarIncDec",
    "DirVarRepReq", "DirVarRepCon", "DirVarRepPar", "DirVarRepGlo", 
    "DirVarRepExt", "DirVarRepLoc", "IndVarAriNeg", "IndVarBitNeg", 
    "IndVarLogNeg", "IndVarIncDec", "IndVarRepReq", "IndVarRepCon", 
    "IndVarRepPar", "IndVarRepGlo", "IndVarRepExt", "IndVarRepLoc",
    "SSDL", "CovAllNod", "CovAllEdg", "STRP", "STRI", "VDTR",
    "RetStaDel", "FunCalDel"
]

def gen_mutants_worker(target_file, output_dir, compile_command):
    unused_ops = ",".join(not_using_operators)

    cmd = [
        musicup,
        str(target_file),
        '-o', str(output_dir),
        '-ll', '2',
        '-l', '2',
        '-d', unused_ops,
        '-p', str(compile_command)
    ]
    print(cmd)

    print(f'Generating mutants for {target_file}...')
    start_time = time.time()
    res = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    end_time = time.time()
    total_time = end_time - start_time

    if res.returncode != 0:
        raise Exception(f'Failed to generate mutants for {target_file}')
    
    print(f'Finished generating mutants for {target_file}, time taken: {total_time} seconds')

def generate_mutants(subject_name, target_file_pair, compile_command):
    compile_command = working_dir / compile_command
    assert compile_command.exists(), f'{compile_command} does not exist'

    start_time = time.time()
    individual_time_list = []

    jobs = []
    for target_file, output_dir in target_file_pair:
        proc = multiprocessing.Process(
            target=gen_mutants_worker,
            args=(target_file, output_dir, compile_command)
        )
        jobs.append(proc)
        proc.start()
    
    for job in jobs:
        job.join()
    
    end_time = time.time()
    total_time = end_time - start_time
    print(f'Total time taken: {total_time} seconds')
    
    

def start_gen_mutants(subject_name):
    assert musicup.exists(), 'MUSICUP is not built. Please build MUSICUP first.'

    # 1. Read configurations
    configs = read_configs(subject_name)

    # 2. make mutations directory for subject in datasets directory
    target_file_pair = initiate_mutants_dir(subject_name, configs['target_files'])

    # 3 generate mutants
    generate_mutants(subject_name, target_file_pair, configs['compile_command_path'])

    


if __name__ == "__main__":
    parser = make_parser()
    args = parser.parse_args()
    

    start_gen_mutants(args.subject)