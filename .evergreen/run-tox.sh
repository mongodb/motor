#!/bin/bash
set -o xtrace   # Write all commands first to stderr
set -o errexit  # Exit the script with error if any of the commands fail

# Supported/used environment variables:
#       AUTH                    Set to enable authentication. Defaults to "noauth"
#       SSL                     Set to enable SSL. Defaults to "nossl"
#       TOX_ENV                 Tox environment name, e.g. "synchro", required.
#       PYTHON_BINARY           Path to python, required.

AUTH=${AUTH:-noauth}
SSL=${SSL:-nossl}

if [ -z $PYTHON_BINARY ]; then
    echo "PYTHON_BINARY is undefined!"
    exit 1
fi

if [ -z $TOX_ENV ]; then
    echo "TOX_ENV is undefined!"
    exit 1
fi

if [ "$AUTH" != "noauth" ]; then
    export DB_USER="bob"
    export DB_PASSWORD="pwd123"
fi

if [ "$SSL" != "nossl" ]; then
    export CLIENT_PEM="$DRIVERS_TOOLS/.evergreen/x509gen/client.pem"
    export CA_PEM="$DRIVERS_TOOLS/.evergreen/x509gen/ca.pem"
fi

if [ -f secrets-export.sh ]; then
    source secrets-export.sh
fi

# Usage:
# createvirtualenv /path/to/python /output/path/for/venv
# * param1: Python binary to use for the virtualenv
# * param2: Path to the virtualenv to create
createvirtualenv () {
    PYTHON=$1
    VENVPATH=$2
    if $PYTHON -m virtualenv --version; then
        VIRTUALENV="$PYTHON -m virtualenv"
    elif $PYTHON -m venv -h > /dev/null; then
        # System virtualenv might not be compatible with the python3 on our path
        VIRTUALENV="$PYTHON -m venv"
    else
        echo "Cannot test without virtualenv"
        exit 1
    fi
    # Workaround for bug in older versions of virtualenv.
    $VIRTUALENV $VENVPATH || $PYTHON -m venv $VENVPATH
    if [ "Windows_NT" = "$OS" ]; then
        # Workaround https://bugs.python.org/issue32451:
        # mongovenv/Scripts/activate: line 3: $'\r': command not found
        dos2unix $VENVPATH/Scripts/activate || true
        . $VENVPATH/Scripts/activate
    else
        . $VENVPATH/bin/activate
    fi

    python -m pip install -q --upgrade pip
    python -m pip install -q --upgrade tox
}


if $PYTHON_BINARY -m tox --version; then
    run_tox() {
      $PYTHON_BINARY -m tox -m $TOX_ENV "$@"
    }
else # No toolchain present, set up virtualenv before installing tox
    createvirtualenv "$PYTHON_BINARY" toxenv
    trap "deactivate; rm -rf toxenv" EXIT HUP
    python -m pip install tox
    run_tox() {
      python -m tox -m $TOX_ENV "$@"
    }
fi

run_tox "${@:1}"
