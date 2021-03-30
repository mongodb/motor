#!/bin/sh
set -o xtrace   # Write all commands first to stderr
set -o errexit  # Exit the script with error if any of the commands fail

# Supported/used environment variables:
#       AUTH                    Set to enable authentication. Defaults to "noauth"
#       SSL                     Set to enable SSL. Defaults to "nossl"
#       TOX_ENV                 Tox environment name, e.g. "tornado4-py36"
#       TOX_BINARY              Path to tox executable
#       INSTALL_TOX             Whether to install tox in a virtualenv
#       PYTHON_BINARY           Path to python
#       VIRTUALENV              Path to virtualenv script
#       TEST_ENCRYPTION         If non-empty, install pymongocrypt.


AUTH=${AUTH:-noauth}
SSL=${SSL:-nossl}
TEST_ENCRYPTION=${TEST_ENCRYPTION:-}

if [ "$AUTH" != "noauth" ]; then
    export DB_USER="bob"
    export DB_PASSWORD="pwd123"
fi

if [ "$SSL" != "nossl" ]; then
    export CLIENT_PEM="$DRIVERS_TOOLS/.evergreen/x509gen/client.pem"
    export CA_PEM="$DRIVERS_TOOLS/.evergreen/x509gen/ca.pem"
fi

if [ "$TOX_ENV" = "synchro37" ]; then
    SETUP_ARGS="-- --check-exclude-patterns"
fi

if [ "${INSTALL_TOX}" = "true" ]; then
    $VIRTUALENV motorenv
    set +o xtrace
    if [ -f motorenv/bin/activate ]; then
        source motorenv/bin/activate
    else
        # Windows.
        ls -l motorenv
        source motorenv/Scripts/activate
    fi
    set -o xtrace
    pip install tox
    TOX_BINARY=tox
fi

# For createvirtualenv.
. .evergreen/utils.sh

if [ -n "$TEST_ENCRYPTION" ]; then
    createvirtualenv $PYTHON_BINARY venv-encryption
    trap "deactivate; rm -rf venv-encryption" EXIT HUP
    PYTHON=python
    python -m pip install pymongo[encryption]
fi

# Run the tests, and store the results in Evergreen compatible XUnit XML
${TOX_BINARY} -e ${TOX_ENV} ${SETUP_ARGS} "$@"
