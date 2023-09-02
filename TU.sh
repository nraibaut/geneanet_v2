#!/bin/bash

CURDIR=$(pwd)
export PYTHONPATH=$CURDIR:$CURDIR/gedcomw:$PYTHONPATH
echo "PYTHONPATH=$PYTHONPATH"
#python tests/TestParser.py > tests/TestParser.log 2>&1

python tests/TestDateConverter.py 2>&1 | tee tests/TestDateConverter.log

