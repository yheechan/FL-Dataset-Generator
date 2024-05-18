# FOX: **F**unction inf**O**rmation e**X**tractor
This tool, ``extractor``, is built to **extract line-to-function information** when given an input of a ``C/C++`` source code file. The program is built with frontend clang library.


## dependencies
1. Clang/LLVM
  * version: 13.0.1 (not tested with other versions)
  * install instructions: https://apt.llvm.org/
    ```
    wget https://apt.llvm.org/llvm.sh
    chmod +x llvm.sh
    sudo ./llvm.sh 13 all
    ```
  * environment settings needed


## Build step
```
# to build extractor
make -j20
# to clean extractor
make clean
```


## Example
This tool works on both C/C++ source codes.
```
./extractor example.c
# or
./extractor example.cpp
```


## Output Structure
When executing ``./extractor <target source code file>``, line-to-function information is printed on the ``stdout``. The infromation is formatted as follows:
```
<function class name>##<function name>##<start line number>##<end line number>##<info>##<file name>
```
* When a class is not part of a class, ``<function class name>`` is written as ``None``.


included on March 27, 2024
