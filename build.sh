#!/bin/bash

if [ $# -lt 1 ] ; then
  echo "Usage: $0 <main-file>"
  exit 1
fi

set -e
mkdir -p build
cd build
cmake -DMAIN_FILE:STRING="$1" ..
make
cd ..
size build/rlb
