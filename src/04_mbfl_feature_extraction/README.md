# 04 MBFL feature extraction stage
* This stage extracts MBFL features for each buggy versions (specifically buggy versions in ``03_prepare_prerequisites/<subject-name>-working_directory/prerequisite_data/`` directory). 

Specific steps includes:
1. Generate mutants
    * Apply buggy version code to the subject repository.
    * Configure & Build the project (do make clean)
    * Execute music to generate mutants
2. Select mutants to utilize (the amount given by user in configure)
3. Apply each mutant and run the test suite (passing and failing TCs)
    * Take into account of mutants that are not compilable
    * Take into account of the outcome of each test case (p2p, f2f, p2f, f2p)
4. Measure the mbfl features.


## 04-1 Initialization stage for mbfl feature extraction

### What it does
* Initializes directories and distributed buggy versions (w/ prerequisite data)
    1. Initialization of working directory: ``<subject-name>-working_directory/``
    2. Assign/Distribute buggy versions (w/ prerequisite data)
    3. Distribute subject repository
    4. Distribute user configurations
    5. Distribute command directory for preparing prerequisites
    6. Distribute external tools specifically ``music`` to extract line2function information.

### Usage:
* When using single machine
```
$ ./general_command --subject <subject-name>
```


* When using multiple distributed machines
```
$ ./general_command.py --subject libxml2
$ ./02-1_initiate_directory.sh
$ ./02-2_distribute_buggy_versions.sh
$ ./03-1_distribute_repo.sh
$ ./04-1_distribute_config.sh
$ ./05-1_distribute_prepare_prerequisites_cmd.sh
$ ./06-1_distribute_external_tools.sh
$ ./07-1_distribute_refine_testsuite_cmd.sh
```


## 04-2 Extracting MBFL features from buggy versions
### What it does
1. Generate mutants
    * Apply buggy version code to the subject repository.
    * Configure & Build the project (do make clean)
    * Execute music to generate mutants
2. Select mutants to utilize (``max_mutants`` given by user in configure file)
3. Apply each mutant and run the test suite (passing and failing TCs)
    * Take into account of mutants that are not compilable
    * Take into account of the outcome of each test case (p2p, f2f, p2f, f2p)
4. Measure the mbfl features. (MUSE and Metallaxis)


### Usage:
* When using single machine (execution on all cores)
```
$ ./general_command_all_local_cores.py --subject libxml2
```

* When using single machine (execution on single core)
```
$ ./general_command --subject <subject-name> --worker gaster23.swtc/core0
```

* When using single machine (execution on single version of single core)
```
$ ./01-2_generate_mutants --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
$ ./01-3_select_mutants --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
$ ./01-4_test_mutants --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
$ ./01-5_measure_mbfl_features --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
```

* When using multiple distributed machines (executes all cores of all machines)
```
$ ./02_extract_mbfl_features_on_distributed_machines.py --subject libxml2
$ ./02-1_extract_mbfl_features_on_distributed_machines.sh
```


## 04-3_gather_mbfl_features
### What it does
1. Generate directory ``mbfl_features/``
2. copies the buggy versions with its mbfl feature data collected from each core of machine(s)

### Usage:
* When using single machine
```
$ ./01_gather_buggy_versions.py --subject libxml2
```

* When using multiple distributed machines
```
$ ./01_gather_buggy_versions.py --subject libxml2
$ ./01-1_retrieve_usable_buggy_versions.sh
```

## 04-4_analyze_mbfl_dataset
### What it does and usage
1. ``01_validate_mbfl_dataset.py``: Validation criteria are...
    * existance of ``mbfl_features.csv`` file for each buggy version
    * existance of ``selected_mutants.csv`` file for each buggy version
    * existance of ``mutation_testing_results.csv`` file for each buggy version
    * that only 1 buggy line exists within ``mbfl_features.csv`` file
```
$ ./01_validate_mbfl_dataset.py --subject libxml2
```

2. ``02_rank_mbfl.py``: measures the rank of buggy function with scores of MUSE and metallaxis
    * writes the results in ``<rank-summary-file-name>`` of ``<subject-name>-working_directory/``
    * where:
        * ``<mbfl-set-name>``: is the directory of the buggy version set
        * ``<rank-summary-file-name>``: is the file name of rank summary
```
$./02_rank_mbfl.py --subject libxml2 --mbfl_set_name <mbfl-set-name> --rank-summary-file-name <rank-summary-file-name>
```

3. ``03_analyze_subset_buggy_versions.py``: analyzes the buggy version set and forms a new subset of buggy version with exclusion that meet the condition (``{both-BF-NBF,BF,NBF}``)
    * ``BF``: excludes buggy versions in which the total f2p (from all mutants) of the buggy line is 0.
    * ``NBF``: excludes buggy versions in which the ``# of bad_lines`` (from lines of non-buggy-function) exceed a certain ``threshold``.
    * ``both-BF-NBF``: excludes buggy versions that follow both conditions of ``BF`` and ``NBF``.
    * options:
        * ``<subject>``: subject name
        * ``<subset-type>``: {both-BF-NBF,BF,NBF}
        * ``new-set-name``: the name of the directory of new subset
```
$ ./03_analyze_subset_buggy_verisons.py --subject libxml2 --subset-type both-BF-NBF --new-set-name mbfl_features-both-BF-NBF
```

## 04-5_refine_testsuite
### What it does (currently 240611)
1. Apply each mutant generated on buggy line and run the test suite (excluded failing TCs)
    * Take into account of mutants that are not compilable
    * Save that are passing in mutants of buggy line to ``additional_failing_tcs.txt``
2. Use gather command for retreiving buggy version with updated ``testsuite_info/`` directory.

### Usage:
* When using single machine (execution on single core)
```
$ ./general_command --subject <subject-name> --worker gaster23.swtc/core0
```

* When using single machine (execution on single version of single core)
```
$ ./01-2_test_mutants_for_additional_f2p_on_buggy_line.py --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
```

* When using multiple distributed machines
```
$ ./02_test_for_reffining_testsuite.py
$ ./02-1_test_for_refining_testsuite.sh
```

### What it does and usage
3. ``03_analyze_additional_failing_with_rank.py``: shows rank information with statistics on test case (with additional_failing_tcs)
```
$ ./03_analyze_additional_failing_with_rank.py --subject libxml2 --mbfl-set-name mbfl_features --rank-summary-file-name additional_failing_tcs_with_rank.csv
```

4. ``04_add_total_additional_testsuite.py``: makes new file ``total_additional_failing_tcs.txt`` in ``testsuite_info/`` directory.
```
$ ./04_add_additional_testsuite.py --subject libxml2 --mbfl-set-name mbfl_features
```

# About mbfl dataset
### mbfl_features
* number of buggy versions: 193
* rank is bad

* libxml2-working_directory-193-240604
    * mbfl features with additional failing TCs
