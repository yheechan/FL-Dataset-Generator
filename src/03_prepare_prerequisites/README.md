# 02 Prepare prerequisite data
Prerequisite data contains the following contents for each buggy version
1. Coverage of each TCs (in CSV format, row=code lines, col=TC)
2. line-to-function mapping information
3. testsuite_info: contains criteria of each TC (passing, failing, CCT, excluded)
4. lines executed by failing lines (each line key to TCs, json format?)


## 03-1 Initialization stage for preparing prerequisites

### Usage when using single machine
* where
    * ``<buggy-version-set-name>``: is the directory name in ``src/02_select_usable_buggy_versions/<subject-working-dir>/<buggy-version-setname>/`` which contains the set of buggy versions.
```
./general_command --subject <subject-name> --buggy-versions-set <buggy-version-set-name>
```

### Usage when using distributed machines:

* When using distributed machines
```
$ ./general_command.py --subject libxml2
$ ./02-1_initiate_directory.sh
$ ./02-2_distribute_buggy_versions.sh
$ ./03-1_distribute_repo.sh
$ ./04-1_distribute_config.sh
$ ./05-1_distribute_prepare_prerequisites_cmd.sh
```
