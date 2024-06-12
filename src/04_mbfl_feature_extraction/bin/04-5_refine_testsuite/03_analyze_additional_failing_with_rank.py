#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import csv
import pandas as pd
import sys

# Current working directory
script_path = Path(__file__).resolve()
refine_testsuite_dir = script_path.parent
bin_dir = refine_testsuite_dir.parent
mbfl_feature_extraction_dir = bin_dir.parent

# General directories
src_dir = mbfl_feature_extraction_dir.parent
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
use_distributed_machines = 'use_distributed_machines'
copy_real_world_buggy_versions = 'copy_real_world_buggy_versions'

# file names
failing_txt = 'failing_tcs.txt'
passing_txt = 'passing_tcs.txt'
ccts_txt = 'ccts.txt'
excluded_failing_txt = 'excluded_failing_tcs.txt'
excluded_passing_txt = 'excluded_passing_tcs.txt'
# excluded_txt = 'excluded_tcs.txt'
additional_failing_txt = 'additional_failing_tcs.txt'


def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.mbfl_set_name, args.rank_summary_file_name)


def start_process(subject_name, mbfl_set_name, rank_summary_file_name):
    global configure_json_file

    subject_working_dir = mbfl_feature_extraction_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. read test suite and generate summary of statistics
    mbfl_features_per_bug = get_buggy_versions(subject_working_dir, mbfl_set_name)

    # 3. rank buggy line with mbfl features
    mbfl_summary = start_analysis(configs, mbfl_features_per_bug)

    # 4. save the summary to a file
    mbfl_feature_summary_file = subject_working_dir / rank_summary_file_name
    with mbfl_feature_summary_file.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=mbfl_summary[0].keys())
        writer.writeheader()
        for data in mbfl_summary:
            writer.writerow(data)


def start_analysis(configs, mbfl_features_per_bug):
    max_mutants = configs['max_mutants']
    mutant_keys = get_mutant_keys(max_mutants)

    bugs_list = []

    acc5_met = []
    acc5_muse = []
    acc10_met = []
    acc10_muse = []

    for idx, bug_dir in enumerate(mbfl_features_per_bug):
        bug_name = bug_dir.name
        # if bug_name != 'relaxng.MUT4445.c': continue
        print(f"\n{idx+1}/{len(mbfl_features_per_bug)}: {bug_name}")

        # GET: mbfl_features.csv
        mbfl_features_csv_file = bug_dir / 'mbfl_features.csv'
        assert mbfl_features_csv_file.exists(), f"MBFL features file {mbfl_features_csv_file} does not exist"

        # GET: list of failing TCs
        failing_tcs = get_tcs(bug_dir, 'failing_tcs.txt')
        passing_tcs = get_tcs(bug_dir, 'passing_tcs.txt')
        ccts = get_tcs(bug_dir, 'ccts.txt')
        excluded_failing_tcs = get_tcs(bug_dir, 'excluded_failing_tcs.txt')
        excluded_passing_tcs = get_tcs(bug_dir, 'excluded_passing_tcs.txt')
        # excluded_tcs = get_tcs(bug_dir, 'excluded_tcs.txt')
        additional_failing_tcs = get_tcs(bug_dir, 'additional_failing_tcs.txt')


        # GET: buggy line key
        buggy_line_key = get_buggy_line_key(bug_dir)

        # GET: get lines executed by failing TCs
        # key: <target-file>#<function-name>#<line-number> WHICH IS JUST LIKE BUGGY_LINE_KEY
        # value: list of failing TCs [TC1, TC2, ...]
        lines_executed_by_failing_tcs = get_lines_executed_by_failing_tcs(bug_dir)

        # VALIDATE: buggy_line_key exists as line in lines_executed_by_failing_tcs
        assert buggy_line_key in lines_executed_by_failing_tcs, f"Buggy line key {buggy_line_key} does not exist in lines executed by failing TCs"

        # GET: mutants data
        mutants_data = get_mutants_data(bug_dir, buggy_line_key)

        # GET: mbfl_features, suspiciousness scores
        # susp_scores_buggy_line = get_susp_scores_buggy_line(mbfl_features_csv_file, buggy_line_key)

        # get rank
        met_key = 'met susp. score'
        muse_key = 'muse susp. score'
        formulas = [met_key, muse_key]
        ranks = {}
        for formula in formulas:
            rank_data = get_rank_at_method_level(mbfl_features_csv_file, buggy_line_key, formula, mutant_keys)
            ranks[formula] = rank_data
        
        bug_rank_key = "rank of buggy function (function level)"
        print(f"\tmet rank: {ranks[met_key][bug_rank_key]}")
        print(f"\tmuse rank: {ranks[muse_key][bug_rank_key]}")

        bugs_list.append({
            'bug_name': bug_name,
            'buggy_line_key': buggy_line_key,

            '# of failing tcs': len(failing_tcs),
            '# of passing tcs': len(passing_tcs),
            '# of ccts': len(ccts),
            '# of excluded failing tcs': len(excluded_failing_tcs),
            '# of excluded passing tcs': len(excluded_passing_tcs),
            # '# of excluded tcs': len(excluded_tcs),
            '# of additional failing tcs': len(additional_failing_tcs),

            '# of lines executed by failing TCs': len(lines_executed_by_failing_tcs),
            
            '# of mutants': mutants_data['# mutants'],
            '# of uncompilable mutants': mutants_data['# uncompilable mutants'],
            '# of mutans on buggy line': mutants_data['# mutans on buggy line'],
            '# of uncompilable mutants on buggy line': mutants_data['# uncompilable mutants on buggy line'],
            '# of compilable mutants on buggy line': mutants_data['# compilable mutants on buggy line'],

            'total p2f (all mutants)': mutants_data['total_p2f'],
            'total f2p (all mutants)': mutants_data['total_f2p'],

            '# of functions': ranks[met_key]['# of functions'],

            '# of function with same highest met score': ranks[met_key]['# of functions with same highest score'],
            'met score of highest rank': ranks[met_key]['score of highest rank'],
            'rank of buggy function (function level) (met)': ranks[met_key]['rank of buggy function (function level)'],
            'met score of buggy function': ranks[met_key]['score of buggy function'],

            '# of function with same highest muse score': ranks[muse_key]['# of functions with same highest score'],
            'muse score of highest rank': ranks[muse_key]['score of highest rank'],
            'rank of buggy function (function level) (muse)': ranks[muse_key]['rank of buggy function (function level)'],
            'muse score of buggy function': ranks[muse_key]['score of buggy function'],
        })

        if ranks[met_key]['rank of buggy function (function level)'] <= 5:
            acc5_met.append(bug_name)
        if ranks[muse_key]['rank of buggy function (function level)'] <= 5:
            acc5_muse.append(bug_name)
        if ranks[met_key]['rank of buggy function (function level)'] <= 10:
            acc10_met.append(bug_name)
        if ranks[muse_key]['rank of buggy function (function level)'] <= 10:
            acc10_muse.append(bug_name)
    
    print(f"All {len(mbfl_features_per_bug)} bugs have been validated successfully")

    print(f"\nTop 5 MET: {len(acc5_met)}")
    print(f"Top 5 MET percentage: {len(acc5_met) / len(mbfl_features_per_bug)}")
    print(f"Top 10 MET: {len(acc10_met)}")
    print(f"Top 10 MET percentage: {len(acc10_met) / len(mbfl_features_per_bug)}")
    
    print(f"\nTop 5 MUSE: {len(acc5_muse)}")
    print(f"Top 5 MUSE percentage: {len(acc5_muse) / len(mbfl_features_per_bug)}")
    print(f"Top 10 MUSE: {len(acc10_muse)}")
    print(f"Top 10 MUSE percentage: {len(acc10_muse) / len(mbfl_features_per_bug)}")

    return bugs_list


def get_mutant_keys(max_mutants):
    mutant_keys = []
    for i in range(1, max_mutants+1):
        mutant_keys.append(f'm{i}:f2p')
        mutant_keys.append(f'm{i}:p2f')
    return mutant_keys

def custome_sort(tc_script):
    tc_filename = tc_script.split('.')[0]
    return int(tc_filename[2:])

def get_tcs(version_dir, tc_file):
    testsuite_info_dir = version_dir / 'testsuite_info'
    assert testsuite_info_dir.exists(), f"Testsuite info directory {testsuite_info_dir} does not exist"

    tc_file_txt = testsuite_info_dir / tc_file
    if not tc_file_txt.exists():
        return []

    tcs_list = []

    with open(tc_file_txt, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            tcs_list.append(line)
        
    tcs_list = sorted(tcs_list, key=custome_sort)

    return tcs_list

def get_rank_at_method_level(mbfl_features_csv_file, buggy_line_key, formula, mutant_keys):

    buggy_target_file = buggy_line_key.split('#')[0].split('/')[-1]
    buggy_function_name = buggy_line_key.split('#')[1]
    buggy_lineno = int(buggy_line_key.split('#')[-1])

    mbfl_features_df = pd.read_csv(mbfl_features_csv_file)

    # 1. SET ALL BUGGY LINE OF BUGGY FUNCTION TO 1
    for index, row in mbfl_features_df.iterrows():
        key = row['key']
        target_file = key.split('#')[0].split('/')[-1]
        function_name = key.split('#')[1]
        line_num = int(key.split('#')[-1])

        # split key to target_file, function_name, line_num (individual column)
        mbfl_features_df.at[index, 'target_file'] = target_file
        mbfl_features_df.at[index, 'function_name'] = function_name
        mbfl_features_df.at[index, 'line_num'] = line_num

        # check if the row is one of the buggy lines of the buggy function
        if target_file == buggy_target_file and function_name == buggy_function_name:
            mbfl_features_df.at[index, 'bug'] = 1
        else:
            mbfl_features_df.at[index, 'bug'] = 0
    

    # 2. DROP THE KEY COLUMN
    mbfl_features_df = mbfl_features_df.drop(columns=['key'])
    # mbfl_features_df = mbfl_features_df[[
    #     'target_file', 'function_name', 'line_num',
    #     'met_1', 'met_2', 'met_3', 'met_4',
    #     'muse_a', 'muse_b', 'muse_c',
    #     'muse_1', 'muse_2', 'muse_3', 'muse_4', 'muse_5', 'muse_6',
    #     'bug'
    # ]]
    mbfl_features_df = mbfl_features_df[[
        'target_file', 'function_name', 'line_num',
        '# of totfailed_TCs', '# of mutants'] + mutant_keys + [
        '|muse(s)|', 'total_f2p', 'total_p2f', 'line_total_f2p', 'line_total_p2f',
        'muse_1', 'muse_2', 'muse_3', 'muse_4',
        'muse susp. score', 'met susp. score', 'bug'

    ]]



    # 3. GROUP ROWS BY THE SAME FUNCTION NAME AND
    # APPLY THE VALUE OF THE LINE WITH THE HIGHEST MUSE_6 SCORE
    mbfl_features_df = mbfl_features_df.groupby(
        ['target_file', 'function_name']).apply(
            lambda x: x.nlargest(1, formula)
        ).reset_index(drop=True)
    

    # 4. SORT THE ROWS BY THE FORMULA VALUE
    mbfl_features_df = mbfl_features_df.sort_values(by=[formula], ascending=False).reset_index(drop=True)

    
    # 5. ADD A RANK COLUMN TO THE DF
    # THE RANK IS BASED ON FORMULA VALUE
    # IF THE RANK IS A TIE, THE RANK IS THE UPPER BOUND OF THE TIERS
    mbfl_features_df['rank'] = mbfl_features_df[formula].rank(method='max', ascending=False).astype(int)
    # mbfl_features_df.to_csv('ranked-function-level.csv', index=False)


    # 6. GET THE RANK OF THE BUGGY LINE
    # AND THE MINIMUM RANK OF THE FORMULA
    # AND THE SCORE
    func_n = mbfl_features_df.shape[0]
    total_num_of_func = 0
    best_rank = sys.maxsize
    best_score = None
    bug_rank = -1
    bug_score = None

    for index, row in mbfl_features_df.iterrows():
        total_num_of_func += 1
        curr_rank = row['rank']
        curr_target_file = row['target_file']
        curr_function_name = row['function_name']
        curr_score = row[formula]

        # assign the best rank number
        if curr_rank < best_rank:
            best_rank = curr_rank
            best_score = curr_score
        
        if curr_rank == best_rank:
            assert curr_score == best_score, f"score is not the same"


        # assign the rank of the buggy line
        if curr_target_file == buggy_target_file and \
            curr_function_name == buggy_function_name:
            bug_rank = curr_rank
            bug_score = curr_score
            assert row['bug'] == 1, f"bug is not 1"
        
    assert best_rank != 0, f"min_rank is 0"
    assert best_rank != sys.maxsize, f"min_rank is sys.maxsize"
    assert best_score is not None, f"best_score is None"

    assert bug_rank != -1, f"rank_bug is -1"
    assert bug_score is not None, f"bug_score is None"

    assert func_n == total_num_of_func, f"func_n != total_num_of_func"

    # print(formula, best_rank, best_score, bug_rank, bug_score)
    data = {
        f'# of functions': total_num_of_func,
        f'# of functions with same highest score': best_rank,
        f'score of highest rank': best_score,
        f'rank of buggy function (function level)': bug_rank,
        f'score of buggy function': bug_score
    }
    return data


def get_susp_scores_buggy_line(mbfl_features_csv_file, buggy_line_key):
    with open(mbfl_features_csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row['key']
            if key == buggy_line_key:
                met_score = float(row['met susp. score'])
                muse_score = float(row['muse susp. score'])
                is_bug = row['bug']

                assert is_bug == '1', f"Line {buggy_line_key} is not a bug"
                susp_scores_buggy_line = {
                    'met_score': met_score,
                    'muse_score': muse_score
                }
                return susp_scores_buggy_line
            
    raise Exception(f"Line {buggy_line_key} does not exist in MBFL features file {mbfl_features_csv_file}")

def get_mutants_data(bug_dir, buggy_line_key):
    mutation_testing_results_csv = bug_dir / 'mutation_testing_results.csv'

    buggy_target_file = buggy_line_key.split('#')[0].split('/')[-1]
    buggy_lineno = buggy_line_key.split('#')[-1]

    mutants_data = {
        '# mutants': 0,
        '# uncompilable mutants': 0,
        '# mutans on buggy line': 0,
        '# uncompilable mutants on buggy line': 0,
        '# compilable mutants on buggy line': 0,
        'total_p2f': 0,
        'total_f2p': 0,
    }

    with open(mutation_testing_results_csv, 'r') as f:
        lines = f.readlines()

        for line in lines[1:]:
            mutants_data['# mutants'] += 1

            info = line.strip().split(',')
            target_file = info[0].split('/')[-1]
            mutant_name = info[1]
            mutant_lineno = info[2]
            mutant_build_result = info[3]
            mutant_p2f = info[4]
            mutant_p2p = info[5]
            mutant_f2p = info[6]
            mutant_f2f = info[7]

            if mutant_build_result == 'FAIL':
                mutants_data['# uncompilable mutants'] += 1
            else:
                mutants_data['total_p2f'] += int(mutant_p2f)
                mutants_data['total_f2p'] += int(mutant_f2p)
            
            if target_file == buggy_target_file and mutant_lineno == buggy_lineno:
                mutants_data['# mutans on buggy line'] += 1

                if mutant_build_result == 'PASS':
                    mutants_data['# compilable mutants on buggy line'] += 1
                else:
                    mutants_data['# uncompilable mutants on buggy line'] += 1
    
    return mutants_data


def get_buggy_line_key(bug_dir):
    buggy_line_key_file = bug_dir / 'buggy_line_key.txt'
    buggy_line_key = None

    with buggy_line_key_file.open() as f:
        buggy_line_key = f.readline().strip()

    return buggy_line_key

def get_lines_executed_by_failing_tcs(bug_dir):
    get_lines_executed_by_failing_tcs_file = bug_dir / 'coverage_info/lines_executed_by_failing_tc.json'
    assert get_lines_executed_by_failing_tcs_file.exists(), f"Lines executed by failing TCs file {get_lines_executed_by_failing_tcs_file} does not exist"

    lines_executed_by_failing_tcs = None
    with get_lines_executed_by_failing_tcs_file.open() as f:
        lines_executed_by_failing_tcs = json.load(f)

    return lines_executed_by_failing_tcs


def get_buggy_versions(subject_working_dir, versions_set_name):
    buggy_versions_dir = subject_working_dir / versions_set_name
    assert buggy_versions_dir.exists(), f"Buggy versions directory {buggy_versions_dir} does not exist"

    buggy_versions = []
    for buggy_version in buggy_versions_dir.iterdir():
        if buggy_version.is_dir():
            buggy_versions.append(buggy_version)

    return buggy_versions



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
    parser.add_argument('--mbfl-set-name', type=str, help='MBFL set name', required=True)
    parser.add_argument('--rank-summary-file-name', type=str, help='Rank summary file name', required=True)
    return parser
    


if __name__ == "__main__":
    main()