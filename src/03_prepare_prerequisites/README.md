# 03 Prepare prerequisite data
* Prerequisite data contains the following contents for each buggy version
    1. Postprocessed coverage of each TCs (in CSV format, row=code lines, col=TC)
        * file: ``coverage_info/postprocessed_coverage.csv``
        * TCs include only passing and failing TCs.
        * according user configuration, CCTs can be excluded, in which the list of CCTs are recorded in ``testsuite_info/ccts.txt`` file
    2. line-to-function mapping information: ``line2function_info/line2function.json``
    3. testsuite_info: contains criteria of each TC
        * passing
        * failing
        * CCT
        * excluded
        * excluded_passing
        * excluded_failing
    4. lines executed by failing lines: ``coverage_info/lines_executed_by_failing_tcs.json``


## 03-1 Initialization stage for preparing prerequisites

### What it does
Initializes directories and distribute buggy versions for preparing prerequisites.
1. Initialization of working directory: ``<subject-name>-working_directory/``
2. Assign/Distribute buggy versions
3. Distribute subject repository
4. Distribute user configurations
5. Distribute command directory for preparing prerequisites
6. Distribute external tools specifically ``extractor`` to extract line2function information.

### Usage:
* When using single machine
* ``general_command.py`` where:
    * ``<buggy-version-set-name>``: is the directory name in ``src/02_select_usable_buggy_versions/<subject-working-dir>/<buggy-version-setname>/`` which contains the set of buggy versions to use (make prerequisite data).
```
$ ./general_command --subject <subject-name> --buggy-versions-set <buggy-version-set-name>
```

* When using multiple distributed machines
```
$ ./general_command.py --subject libxml2 --buggy-versions-set <buggy-version-set-name>
$ ./02-1_initiate_directory.sh
$ ./02-2_distribute_buggy_versions.sh
$ ./03-1_distribute_repo.sh
$ ./04-1_distribute_config.sh
$ ./05-1_distribute_prepare_prerequisites_cmd.sh
$ ./06-1_distribute_external_tools.sh
```

## 03-2 Prepare prerequisites data for bug versions

### What it does
This step first builds the buggy version and extracts line-to-function mapping information. This step then executes utilizing test cases (passing and failing only) and measures the coverage. It then uses the coverage information of each test case to form a postprocess coverage information as CSV file format.
* builds the buggy version
* extracts line2function information
* measures coverage of each test case (passing and failing)
    * if CCT option is True, passings TCs that execute buggy line is excluded (written in ``ccts.txt`` file)
* postprocess the coverage information to CSV format

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
$ ./01_initial_configure_and_build.py --subject libxml2 --worker gaster23.swtv/core0
$ ./02-2_extract_line2function.py --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
$ ./02-3_measure_coverage.py --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
$ ./02-4_postprocess_coverage.py --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
```

* When using multiple distributed machines (executes all cores of all machines)
```
$ ./03_prepare_prerequisites_on_distributed_machines.py --subject libxml2 --buggy-versions-set <buggy-version-set-name>
$ ./03-1_prepare_prerequisites_on_distributed_mahcines.sh
```

## 03-3 Gather buggy versions which includes prerequisite data
### What it does
1. Generate directory ``prerequisite_data/``
2. copies the buggy versions with its prerequisite data collected from each core of machine(s)

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

## 03-4 analyze_buggy_versions (each commands are optional)

### What it does and Usage:
1. ``02_validate_prerequisite_data.py``: Validation criteria are...
    * existance of ``bug_info.csv`` file. This file contains ``target_code_file,buggy_code_file,buggy_lineno`` as features of the buggy version.
    * existance of ``buggy_line_key.txt`` file. This file contains the key string of buggy line.
    * existance of ``coverage_summary.csv`` file. This file contains test cases (failing, passing, cct, excluded failing, excluding passing, excluded) and coverage (lines executed by failing and passing) information.
    * existance of ``posprocessed_coverage.csv`` file. This file contains the real coverage information of each utilized TCs.
    * existance of ``linesd_executed_by_failing_tcs.json`` file.
    * existance of ``line2function_info.json`` file.
    * that all failing TCs execute the buggy line
```
$ ./01_validate_prerequisite_data.py --subject libxml2
```
2. ``statistics_summary.py``: summarizes the ``coverage_summary.csv`` file of each buggy version and writes into ``statistics_summary.csv`` within ``<subject-name>-working_directory/``
```
$ ./02_stastistics_summary.py --subject libxml2
```


## zip data
* libxml2-working_directory-240606-v1.zip and v2
    * saved new v2 to so that this stage can save excluded failing and passing tcs differentially