#!/bin/bash -ex

# This script should be run on macOS.
# It will create the following distributions:
# motor-<version>.tar.gz
# motor-<version>-py3-none-any.whl

set -o xtrace   # Write all commands first to stderr
set -o errexit  # Exit the script with error if any of the commands fail

# Cleanup destinations
rm -rf build
rm -rf dist

# Install deps
python3 -m pip install build

# Build the source dist and wheel
python3 -m build .

# Cleanup
rm -rf build
ls dist
