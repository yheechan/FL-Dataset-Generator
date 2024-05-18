# Collect Buggy Mutants of target subject

## 01-1 Generate mutants
1. Initialize working directory for target subject ``<subject-name>-working_directory/``
    2. Copies subject source repository
    3. Copies user configurations of target subject
    4. Copies configure and build script to indicated paths
    5. Copies MUSICUP executable to ``external_tools/`` directory in working directory
2. Executes configure and build script in indicated paths
3. Generates mutants using MUSICUP and saves to ``generated_mutants/`` directory in working directory


## 01-2 Assign/distribute mutants to:
* cores in case of utilizing single machine
* cores of each machine in case of utilizing multi-machines


## 01-3 Test mutants & collect buggy mutants
* test mutants on single machine
* test mutants on multi-machines


## 01-4 Retrieve mutants from distributed machines (only in use of multi-machines)


## 01-5 Gather buggy mutants to one directory
