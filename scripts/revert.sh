#!/bin/bash
pushd ../ >/dev/null 2>&1
git restore -s  "$1" nbdir 
popd ../ >/dev/null 2>&1