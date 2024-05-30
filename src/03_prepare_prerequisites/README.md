# 03 Prepare prerequisite data
Prerequisite data contains the following contents for each buggy version
1. Postprocessed coverage of each TCs (in CSV format, row=code lines, col=TC)
    * file: ``coverage_info/postprocessed_coverage.csv``
    * TCs include only pasing and failing TCs.
    * according user configuration, CCTs can be excluded, in which the list of CCTs are recorded in ``testsuite_info/ccts.txt`` file
2. line-to-function mapping information: ``line2function_info/line2function.json``
3. testsuite_info: contains criteria of each TC (passing, failing, CCT, excluded)
4. lines executed by failing lines: ``coverage_info/lines_executed_by_failing_tcs.json``


## 03-1 Initialization stage for preparing prerequisites
Initializes directories and distribute buggy versions for preparing prerequisites.
1. Initialization of working directory: ``<subject-name>-working_directory/``
2. Assign/Distribute buggy versions
3. Distribute subject repository
4. Distribute user configurations
5. Distribute command directory for preparing prerequisites
6. Distribute external tools specifically ``extractor`` to extract line2function information.

### Usage when using single machine
* where
    * ``<buggy-version-set-name>``: is the directory name in ``src/02_select_usable_buggy_versions/<subject-working-dir>/<buggy-version-setname>/`` which contains the set of buggy versions.
```
$ ./general_command --subject <subject-name> --buggy-versions-set <buggy-version-set-name>
```

### Usage when using distributed machines:

* When using distributed machines
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
This step first builds the buggy version and extracts line-to-function mapping inforation. This step then executes utilizing test cases and measures the coverage. It then uses the coverage information of each test case to form a postprocess coverage information as CSV file format.

### Usage when executing preparation of prerequisites on single core of a machine
```
$ ./general_command --subject <subject-name> --worker gaster23.swtc/core0
```

### Usage when executing prepartion of prerequisite on single version of a single core
```
$ ./01_inital_configure_and_build.py --subject libxml2 --worker gaster23.swtv/core0
$ ./02-2_extract_line2function.py --subject libxml2 --worker gaster23.swtv/core0 --version parser.issue123.c
$ ./02-3_measure_coverage.py --subject libxml2 --worker gaster23.swt/core0 --version parser.issue123.c
$ ./02-4_postprocess_coverage.py --subject libxml2 --worker gaster23.swtv/core0 --version parser.issue123.c
```

### Usage when executing prepartion of prerequisites on multiple distributed machines
```
$ ./03_prepare_prerequisites_on_distributed_machines.py --subject libxml2 --buggy-versions-set <buggy-version-set-name>
$ ./03-1_prepare_prerequisites_on_distributed_mahcines.sh
```

## 03-3 Gather buggy versions which includes prerequisite data

### Usage when gather buggy versions w/ prerequisites in single machine
```
$ ./01_gather_buggy_versions.py --subject libxml2
```

### Usage when gather buggy version w/ prerequisites on multiple distributed machines
```
$ ./01_gather_buggy_versions.py --subject libxml2
$ ./01-1_retrieve_prerequisites.sh
```