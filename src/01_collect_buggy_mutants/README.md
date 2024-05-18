# Collect Buggy Mutants of target subject

## 01-1 Generate mutants
1. Initialize working directory for target subject ``<subject-name>-working_directory/``
    2. Copies subject source repository
    3. Copies user configurations of target subject
    4. Copies configure and build script to indicated paths
    5. Copies MUSICUP executable to ``external_tools/`` directory in working directory
2. Executes configure and build script in indicated paths
3. Generates mutants using MUSICUP and saves to ``generated_mutants/`` directory in working directory

```
./general_command --subject libxml2
```


## 01-2 Prepare for testing mutants to collect buggy mutants
1. Assign/distribute mutants to each cores of each machines (or each cores of a machine)
2. Distribute subject directory
3. Distribute mutation testing bin



## 01-3 Test mutants & collect buggy mutants
* test mutants on single machine
* test mutants on multi-machines


## 01-4 Retrieve mutants from distributed machines (only in use of multi-machines)


## 01-5 Gather buggy mutants to one directory
