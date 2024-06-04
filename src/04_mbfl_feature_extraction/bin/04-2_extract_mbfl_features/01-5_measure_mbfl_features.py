#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import os
import csv
import math

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

    # 2. get lines from postprocessed coverage info
    lines = get_lines_from_postprocessed_coverage(version_dir)

    # 3. get mbfl features of individual lines to mutants
    perfileline_features, total_p2f, total_f2p = get_perfileline_features(version_dir)

    # 4. get test cases
    failing_tc_list = get_tcs(version_dir, 'failing_tcs.txt')
    total_num_failing_tcs = len(failing_tc_list)

    # 5. get max_mutants from configs
    max_mutants = configs['max_mutants']


    # 6. measure mbfl feature on each line
    mbfl_features = measure_mbfl_features(
        perfileline_features, 
        total_p2f, total_f2p,
        total_num_failing_tcs, max_mutants
    )


    # 7. get buggy line key
    buggy_line_key = get_buggy_line_key(version_dir)

    # 8. process to csv
    process2csv(version_dir, mbfl_features, lines, buggy_line_key, max_mutants, total_num_failing_tcs)

    # 9. zip the generated_mutant/<version-name> directory as <versoin-name>.zip
    zip_mutant_dir(core_working_dir, version_name)


def zip_mutant_dir(core_working_dir, version_name):
    mutants_dir = core_working_dir / 'generated_mutants'
    assert mutants_dir.exists(), f"Mutants directory {mutants_dir} does not exist"

    zip_file = mutants_dir / f"{version_name}.zip"
    if zip_file.exists():
        os.remove(zip_file)
    
    res = sp.run(['zip', '-r', f'{version_name}.zip', version_name], cwd=mutants_dir, stdout=sp.PIPE, stderr=sp.PIPE)
    if res.returncode != 0:
        raise Exception(f"Failed to zip the directory {version_name}")
    
    print(f"Zipped the directory {version_name} as {version_name}.zip")

    # remove the directory
    res = sp.run(['rm', '-rf', version_name], cwd=mutants_dir)
    if res.returncode != 0:
        raise Exception(f"Failed to remove the directory {version_name}")
    
    print(f"Removed the directory {version_name} from generated_mutants directory")





def process2csv(version_dir, mbfl_features, lines, buggy_line_key, max_mutants, total_num_failing_tcs):

    csv_file = version_dir / 'mbfl_features.csv'

    mutant_key_default = {}
    for i in range(1, max_mutants+1):
        mutant_key_default[f'm{i}:f2p'] = -1
        mutant_key_default[f'm{i}:p2f'] = -1
    
    default = {
        '# of totfailed_TCs': total_num_failing_tcs,
        '# of mutants': max_mutants,
        '|muse(s)|': 0, 'total_f2p': 0, 'total_p2f': 0,
        'line_total_f2p': 0, 'line_total_p2f': 0,
        'muse_1': 0, 'muse_2': 0, 'muse_3': 0, 'muse_4': 0,
        'muse susp. score': 0.0, 'met susp. score': 0.0, 'bug': 0,
        **mutant_key_default
    }

    fieldnames = ['key', '# of totfailed_TCs', '# of mutants'] + list(mutant_key_default.keys()) + [
        '|muse(s)|', 'total_f2p', 'total_p2f', 'line_total_f2p', 'line_total_p2f',
        'muse_1', 'muse_2', 'muse_3', 'muse_4', 'muse susp. score', 'met susp. score',
        'bug'
    ]

    with open(csv_file, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for line in lines:
            line_info = line.strip().split('#')
            target_file = line_info[0].split('/')[-1]
            lineno = line_info[-1]

            buggy_stat = 0
            if line == buggy_line_key:
                buggy_stat = 1
            
            if target_file in mbfl_features and lineno in mbfl_features[target_file]:
                mbfl_features[target_file][lineno]['bug'] = buggy_stat
                writer.writerow({
                    'key': line, **mbfl_features[target_file][lineno]
                })
            else:
                default['bug'] = buggy_stat
                writer.writerow({'key': line, **default})



def measure_mbfl_features(
    perfileline_features, total_p2f, total_f2p,
    total_num_failing_tcs, max_mutants
):
    mbfl_features = {}

    for target_file, lineno_mutants in perfileline_features.items():
        if target_file not in mbfl_features:
            mbfl_features[target_file] = {}

        for lineno, mutants in lineno_mutants.items():
            if lineno not in mbfl_features[target_file]:
                mbfl_features[target_file][lineno] = {}
            
            mbfl_features[target_file][lineno]['# of totfailed_TCs'] = total_num_failing_tcs
            mbfl_features[target_file][lineno]['# of mutants'] = max_mutants
            
            mutant_cnt = 0
            mutant_key_list = []
            for mutant in mutants:
                mutant_id = mutant['mutant_id']
                p2f = mutant['p2f']
                p2p = mutant['p2p']
                f2p = mutant['f2p']
                f2f = mutant['f2f']

                # ps. perfileline_features does not contain mutants that failed to build

                mutant_cnt += 1
                p2f_name = f"m{mutant_cnt}:p2f"
                f2p_name = f"m{mutant_cnt}:f2p"
                mutant_key_list.append((p2f_name, f2p_name))

                mbfl_features[target_file][lineno][p2f_name] = p2f
                mbfl_features[target_file][lineno][f2p_name] = f2p
                # if f2p > 0:
                #     print(f"Mutant {lineno} {mutant_id} ({p2f}, {p2p}, {f2p}, {f2f})")

            for i in range(0, max_mutants - len(mutants)):
                mutant_cnt += 1
                p2f_name = f"m{mutant_cnt}:p2f"
                f2p_name = f"m{mutant_cnt}:f2p"
                mutant_key_list.append((p2f_name, f2p_name))

                mbfl_features[target_file][lineno][p2f_name] = -1
                mbfl_features[target_file][lineno][f2p_name] = -1
        
            met_score = measure_metallaxis(mbfl_features[target_file][lineno], mutant_key_list)
            mbfl_features[target_file][lineno]['met susp. score'] = met_score

            muse_data = measure_muse(mbfl_features[target_file][lineno], total_p2f, total_f2p, mutant_key_list)
            for key, value in muse_data.items():
                mbfl_features[target_file][lineno][key] = value
    
    # print(json.dumps(mbfl_features, indent=4))
    
    return mbfl_features

def measure_muse(features, total_p2f, total_f2p, mutant_key_list):
    utilized_mutant_cnt = 0
    line_total_p2f = 0
    line_total_f2p = 0

    final_muse_score = 0.0

    for p2f_m, f2p_m in mutant_key_list:
        p2f = features[p2f_m]
        f2p = features[f2p_m]

        if p2f == -1 or f2p == -1:
            continue

        utilized_mutant_cnt += 1
        line_total_p2f += p2f
        line_total_f2p += f2p

    muse_1 = (1 / ((utilized_mutant_cnt + 1) * (total_f2p + 1)))
    muse_2 = (1 / ((utilized_mutant_cnt + 1) * (total_p2f + 1)))

    muse_3 = muse_1 * line_total_f2p
    muse_4 = muse_2 * line_total_p2f

    final_muse_score = muse_3 - muse_4

    muse_data = {
        '|muse(s)|': utilized_mutant_cnt,
        'total_f2p': total_f2p,
        'total_p2f': total_p2f,
        'line_total_f2p': line_total_f2p,
        'line_total_p2f': line_total_p2f,
        'muse_1': muse_1,
        'muse_2': muse_2,
        'muse_3': muse_3,
        'muse_4': muse_4,
        'muse susp. score': final_muse_score
    }

    return muse_data

def measure_metallaxis(features, mutant_key_list):
    tot_failing_tcs = features['# of totfailed_TCs']
    met_score_list = []

    for p2f_m, f2p_m in mutant_key_list:
        p2f = features[p2f_m]
        f2p = features[f2p_m]

        if p2f == -1 or f2p == -1:
            continue

        score = 0.0
        if f2p + p2f == 0:
            score = 0.0
        else:
            score = ((f2p) / math.sqrt(tot_failing_tcs * (f2p + p2f)))

        met_score_list.append(score)

    final_met_score = max(met_score_list)
    return final_met_score


def get_buggy_line_key(version_dir):
    buggy_line_key_file = version_dir / 'buggy_line_key.txt'
    assert buggy_line_key_file.exists(), f"Buggy line key file {buggy_line_key_file} does not exist"

    with open(buggy_line_key_file, 'r') as f:
        line = f.readline().strip()
        return line

def get_perfileline_features(version_dir):
    mutation_testing_result_file = version_dir / 'mutation_testing_results.csv'
    assert mutation_testing_result_file.exists(), f"Mutation testing result file {mutation_testing_result_file} does not exist"

    perfileline_features = {}
    total_p2f = 0
    total_f2p = 0

    with open(mutation_testing_result_file, 'r') as f:
        lines = f.readlines()
        for line in lines[1:]:
            info = line.strip().split(',')
            target_file = info[0]
            mutant_id = info[1]
            lineno = info[2]
            build_result = info[3]

            if build_result == 'FAIL':
                continue

            p2f = int(info[4])
            p2p = int(info[5])
            f2p = int(info[6])
            f2f = int(info[7])

            total_p2f += p2f
            total_f2p += f2p

            if target_file not in perfileline_features:
                perfileline_features[target_file] = {}

            if lineno not in perfileline_features[target_file]:
                perfileline_features[target_file][lineno] = []
            
            perfileline_features[target_file][lineno].append({
                'mutant_id': mutant_id,
                'p2f': p2f,
                'p2p': p2p,
                'f2p': f2p,
                'f2f': f2f
            })
    
    # print(json.dumps(perfileline_features, indent=4))
    
    return perfileline_features, total_p2f, total_f2p



def get_lines_from_postprocessed_coverage(version_dir):
    cov_data_csv = version_dir / 'coverage_info/postprocessed_coverage.csv'
    assert cov_data_csv.exists(), f'{cov_data_csv} does not exist'

    lines_list = []
    with open(cov_data_csv, 'r') as csv_fp:
        csv_reader = csv.reader(csv_fp)
        next(csv_reader)
        for row in csv_reader:
            lines_list.append(row[0])
    return lines_list






def custome_sort(tc_script):
    tc_filename = tc_script.split('.')[0]
    return int(tc_filename[2:])
    
def get_tcs(version_dir, tc_file):
    testsuite_info_dir = version_dir / 'testsuite_info'
    assert testsuite_info_dir.exists(), f"Testsuite info directory {testsuite_info_dir} does not exist"

    tc_file_txt = testsuite_info_dir / tc_file
    assert tc_file_txt.exists(), f"Failing test cases file {tc_file_txt} does not exist"

    tcs_list = []

    with open(tc_file_txt, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            tcs_list.append(line)
        
    tcs_list = sorted(tcs_list, key=custome_sort)

    return tcs_list





def get_bug_info(version_dir):
    bug_info_csv = version_dir / 'bug_info.csv'
    assert bug_info_csv.exists(), f"Bug info csv file {bug_info_csv} does not exist"

    with open(bug_info_csv, 'r') as f:
        lines = f.readlines()
        target_code_file, buggy_code_filename, buggy_lineno = lines[1].strip().split(',')
        return target_code_file, buggy_code_filename, buggy_lineno


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
