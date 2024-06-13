#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import os

# Current working directory
script_path = Path(__file__).resolve()
mbfl_feature_extraction_dir = script_path.parent
bin_dir = mbfl_feature_extraction_dir.parent
extract_mbfl_features_cmd_dir = bin_dir.parent

# General directories
src_dir = extract_mbfl_features_cmd_dir.parent
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
real_world_buggy_versions = 'real_world_buggy_versions'

my_env = os.environ.copy()

not_using_operators = [
    "DirVarAriNeg", "DirVarBitNeg", "DirVarLogNeg", "DirVarIncDec",
    "DirVarRepReq", "DirVarRepCon", "DirVarRepPar", "DirVarRepGlo", 
    "DirVarRepExt", "DirVarRepLoc", "IndVarAriNeg", "IndVarBitNeg", 
    "IndVarLogNeg", "IndVarIncDec", "IndVarRepReq", "IndVarRepCon", 
    "IndVarRepPar", "IndVarRepGlo", "IndVarRepExt", "IndVarRepLoc",
    "STRI"
]

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.worker, args.version)


def start_process(subject_name, worker_name, version_name):
    subject_working_dir = extract_mbfl_features_cmd_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    core_working_dir = subject_working_dir / 'workers_extracting_mbfl_features' / worker_name
    assert core_working_dir.exists(), f"Core working directory {core_working_dir} does not exist"

    assigned_buggy_versions_dir = core_working_dir / 'assigned_buggy_versions'
    assert assigned_buggy_versions_dir.exists(), f"Assigned buggy versions directory {assigned_buggy_versions_dir} does not exist"

    version_dir = assigned_buggy_versions_dir / version_name
    assert version_dir.exists(), f"Version directory {version_dir} does not exist"


    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)


    # 2. get bug_info
    target_code_file_path, buggy_code_filename, buggy_lineno = get_bug_info(version_dir)
    # print(f"Target code file: {target_code_file_path}")
    # print(f"Buggy code filename: {buggy_code_filename}")
    # print(f"Buggy line number: {buggy_lineno}")
    assert version_name == buggy_code_filename, f"Version name {version_name} does not match with buggy code filename {buggy_code_filename}"

    # 4. get buggy code file
    buggy_code_file = get_buggy_code_file(version_dir, buggy_code_filename)
    # print(f"Buggy code file: {buggy_code_file.name}")

    # 5. get extractor
    music = subject_working_dir / 'external_tools/music'
    assert music.exists(), f"Music directory {music} does not exist"


    # 6. get lines executed by failing test cases per target files
    # IT ALSO VALIDATES THE LINES EXECUTED BY FAILING TC CONTAINS THE BUGGY LINE
    lines_executed_by_failing_tc = get_lines_executed_by_failing_tcs(version_dir, target_code_file_path, buggy_lineno, configs['target_files'])
    print(f"Lines executed by failing test cases:")
    for target_file, lines in lines_executed_by_failing_tc.items():
        print(f"{target_file}: {len(lines)}")

    version_name_zip = version_name + '.zip'
    version_mutant_zip = core_working_dir / 'generated_mutants' / version_name_zip

    version_mutant_dir = core_working_dir / 'generated_mutants' / version_name

    if not version_mutant_zip.exists() and not version_mutant_dir.exists():
        # 7. conduct run tests on buggy version with failing test cases
        generate_mutants(
            configs, core_working_dir, version_name, 
            target_code_file_path, buggy_code_file, 
            music, version_dir, lines_executed_by_failing_tc
        )
    elif version_mutant_zip.exists() and not version_mutant_dir.exists():
        # 7. unzip the mutants
        unzip_mutants(version_mutant_zip, version_mutant_dir)
    elif not version_mutant_zip.exists() and version_mutant_dir.exists():
        print(f"Mutants for {version_name} already generated")


def unzip_mutants(version_mutant_zip, version_mutant_dir):
    cmd = ['unzip', version_mutant_zip]
    res = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    if res.returncode != 0:
        raise Exception(f'Failed to unzip mutants for {version_mutant_zip.name}')
    
    print(f'Unzipped mutants for {version_mutant_zip.name}')

    assert version_mutant_dir.exists(), f"Mutants directory {version_mutant_dir} does not exist"

def get_lines_executed_by_failing_tcs(version_dir, target_code_file_path, buggy_lineno, target_files):
    lines_executed_by_failing_tc_file = version_dir / 'coverage_info/lines_executed_by_failing_tc.json'
    assert lines_executed_by_failing_tc_file.exists(), f"Lines executed by failing test cases file {lines_executed_by_failing_tc_file} does not exist"

    lines_executed_by_failing_tc_json = json.loads(lines_executed_by_failing_tc_file.read_text())

    execed_lines = {}
    for target_file in target_files:
        filename = target_file.split('/')[-1]
        execed_lines[filename] = []

    # read the file and return the content
    buggy_filename = target_code_file_path.split('/')[-1]
    executed_buggy_line = False
    for key, tcs in lines_executed_by_failing_tc_json.items():
        info = key.split('#')
        filename = info[0].split('/')[-1]
        function_name = info[1]
        lineno = info[2]

        if filename not in execed_lines:
            execed_lines[filename] = []
        execed_lines[filename].append(lineno)

        if filename == buggy_filename and lineno == buggy_lineno:
            executed_buggy_line = True

    assert executed_buggy_line, f"Buggy line {buggy_lineno} is not executed by any failing test cases"

    return execed_lines


def get_bug_info(version_dir):
    bug_info_csv = version_dir / 'bug_info.csv'
    assert bug_info_csv.exists(), f"Bug info csv file {bug_info_csv} does not exist"

    with open(bug_info_csv, 'r') as f:
        lines = f.readlines()
        target_code_file, buggy_code_filename, buggy_lineno = lines[1].strip().split(',')
        return target_code_file, buggy_code_filename, buggy_lineno


def get_buggy_code_file(version_dir, buggy_code_filename):
    buggy_code_file_dir = version_dir / 'buggy_code_file'
    assert buggy_code_file_dir.exists(), f"Buggy code file directory {buggy_code_file_dir} does not exist"

    buggy_code_file = buggy_code_file_dir / buggy_code_filename
    assert buggy_code_file.exists(), f"Buggy code file {buggy_code_file} does not exist"

    return buggy_code_file



def generate_mutants(
        configs, core_working_dir, version_name, 
        target_code_file_path, buggy_code_file, 
        music, version_dir, lines_executed_by_failing_tc):

    # --- prepare needed directories
    max_mutants = configs['max_mutants']
    worksTodo = intitiate_mutants_dir(core_working_dir, version_name, configs['target_files'])

    # --- start generating mutants
    # 1. Make patch file
    patch_file = make_patch_file(target_code_file_path, buggy_code_file, core_working_dir)

    # 2. Apply patch
    apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, False)

    # 3. clean Execute configure and Build the subject, if build fails, skip the mutant
    res = execute_clean_script(configs[build_sh_wd_key], core_working_dir)
    # if res != 0:
    #     print('Failed to clean on {}'.format(version_name))
    #     apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)
    #     exit(1)

    res = execute_configure_script(configs[config_sh_wd_key], core_working_dir)
    if res != 0:
        print('Failed to configure on {}'.format(version_name))
        apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)
        exit(1)
    
    res = execute_build_script(configs[build_sh_wd_key], core_working_dir)
    if res != 0:
        print('Failed to build on {}'.format(version_name))
        apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)
        exit(1)
    
    # 4. get compile command
    compile_command = core_working_dir / configs['compile_command_path']
    assert compile_command.exists(), f"Compile command {compile_command} does not exist"

    # 5. generate mutants
    # target_file: libxml2/parser.c
    # key file: HTMLparser.c#htmlnamePush(htmlParserCtxtPtr ctxt, const xmlChar * value)#151
    for target_file, output_dir in worksTodo:
        filename = target_file.name
        lines = lines_executed_by_failing_tc[filename]
        if len(lines) == 0:
            print(f"No lines executed by failing test cases for {filename}")
            continue
        gen_mutants_work(target_file, output_dir, compile_command, max_mutants, music, lines)
    
    # 7. Apply patch reverse
    apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)

    # 6. Show statistics
    show_statistics(worksTodo)


def show_statistics(worksTodo):
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
        print(f'{target_file.name}: {mutant_cnt}')



def gen_mutants_work(target_file, output_dir, compile_command, max_mutants, music_cmd, lines):
    global not_using_operators
    unused_ops = ','.join(not_using_operators)
    execed_lines = ','.join(lines)

    cmd = [
        music_cmd,
        str(target_file),
        '-o', str(output_dir),
        '-ll', str(max_mutants),
        '-l', '2',
        '-d', unused_ops,
        '-i', execed_lines,
        '-p', str(compile_command)
    ]
    print(f'Generating mutants for {target_file.name}...')
    res = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    if res.returncode != 0:
        raise Exception(f'Failed to generate mutants for {target_file.name}')
    
    print(f'Finished generating mutants for {target_file.name}')


def intitiate_mutants_dir(core_working_dir, version_name, target_files):
    mutants_dir = core_working_dir / 'generated_mutants'
    mutants_dir.mkdir(exist_ok=True, parents=True)

    version_mutants_dir = mutants_dir / version_name
    version_mutants_dir.mkdir(exist_ok=True)

    target_file_pair = []

    for target_file in target_files:
        target_file_path = core_working_dir / Path(target_file)
        assert target_file_path.exists(), f'{target_file_path} does not exist'

        target_file_name = target_file.replace('/', '-')
        single_file_mutant_dir = version_mutants_dir / f"{target_file_name}"
        single_file_mutant_dir.mkdir(exist_ok=True, parents=True)

        target_file_pair.append((target_file_path, single_file_mutant_dir))
    
    return target_file_pair

def make_patch_file(target_code_file_path, buggy_code_file, core_working_dir):
    patch_file = core_working_dir / f"buggy.patch"

    target_file = core_working_dir / target_code_file_path
    assert target_file.exists(), f"Target file {target_file} does not exist"

    cmd = ['diff', target_file.__str__(), buggy_code_file.__str__()]
    sp.run(cmd, stdout=patch_file.open('w'))
    
    return patch_file

def apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, revert=False):
    target_file = core_working_dir / target_code_file_path
    assert target_file.exists(), f"Target file {target_file} does not exist"

    cmd = ['patch']
    if revert:
        cmd.append('-R')
    cmd.extend(['-i', patch_file.__str__(), target_file.__str__()])

    res = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    if res.returncode != 0:
        raise Exception(f'Failed to apply patch to {target_file.name} with buggy_version {buggy_code_file.name}')
    
    print(f'Applied patch to {target_file.name} with buggy_version {buggy_code_file.name} : revert={revert}')


def execute_clean_script(clean_sh_wd, core_working_dir):
    global clean_script

    clean_sh_wd = core_working_dir / clean_sh_wd
    clean_sh = clean_sh_wd / clean_script
    assert clean_sh.exists(), f"Clean script {clean_sh} does not exist"

    cmd = ['bash', clean_sh]
    res = sp.run(cmd, cwd=clean_sh_wd, stdout=sp.PIPE, stderr=sp.PIPE)
    
    print('Executed clean script')

    return res.returncode


def execute_configure_script(config_sh_wd, core_working_dir):
    global configure_no_cov_script

    config_sh_wd = core_working_dir / config_sh_wd
    config_sh = config_sh_wd / configure_no_cov_script
    assert config_sh.exists(), f"Configure script {config_sh} does not exist"

    cmd = ['bash', config_sh]
    res = sp.run(cmd, cwd=config_sh_wd, stdout=sp.PIPE, stderr=sp.PIPE)
    
    print('Executed configure script')

    return res.returncode

def execute_build_script(build_sh_wd, core_working_dir):
    global build_script

    build_sh_wd = core_working_dir / build_sh_wd
    build_sh = build_sh_wd / build_script
    assert build_sh.exists(), f"Build script {build_sh} does not exist"

    cmd = ['bash', build_script]
    res = sp.run(cmd, cwd=build_sh_wd, stdout=sp.PIPE, stderr=sp.PIPE)

    print(f"Build script executed: {res.returncode}")
    
    return res.returncode



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

def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    parser.add_argument('--worker', type=str, help='Worker name (e.g., <machine-name>/<core-id>)', required=True)
    parser.add_argument('--version', type=str, help='Version name', required=True)
    return parser

if __name__ == "__main__":
    main()
    exit(0)
