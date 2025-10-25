#!/bin/bash
pushd ../ >/dev/null 2>&1
git restore -s  "$1" "$2" 
popd ../ >/dev/null 2>&1