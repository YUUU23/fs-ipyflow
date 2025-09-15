#!/bin/bash

git add nbdir >/dev/null 2>&1
git commit -m "status update" >/dev/null 2>&1
git push >/dev/null 2>&1
git rev-parse HEAD