#!/bin/bash -ex

# This script should be run on macOS.
# It will create the following distributions:
# motor-<version>.tar.gz
# motor-<version>-py3-none-any.whl

set -o xtrace   # Write all commands first to stderr
set -o errexit  # Exit the script with error if any of the commands fail

# Only build distributions with Python 3.5.2 or later.
python3 -c "import sys; exit(sys.version_info < (3, 5, 2))"
if [ $? -ne 0 ]; then
  echo "ERROR: Run this script with Python 3.5.2 or later."
  exit 1
fi

# Cleanup destinations
rm -rf build
rm -rf dist

# Build the source dist first
python3 setup.py sdist

# Build the wheel
python3 setup.py bdist_wheel

# Cleanup
rm -rf build
ls dist