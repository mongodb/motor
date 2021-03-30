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

    if [ "Windows_NT" = "$OS" ]; then # Magic variable in cygwin
        $PYTHON -m pip install -U setuptools
    fi

    if [ -z "$LIBMONGOCRYPT_URL" ]; then
        echo "Cannot test client side encryption without LIBMONGOCRYPT_URL!"
        exit 1
    fi
    curl -O "$LIBMONGOCRYPT_URL"
    mkdir libmongocrypt
    tar xzf libmongocrypt.tar.gz -C ./libmongocrypt
    ls -la libmongocrypt
    ls -la libmongocrypt/nocrypto
    # Use the nocrypto build to avoid dependency issues with older windows/python versions.
    BASE=$(pwd)/libmongocrypt/nocrypto
    if [ -f "${BASE}/lib/libmongocrypt.so" ]; then
        export PYMONGOCRYPT_LIB=${BASE}/lib/libmongocrypt.so
    elif [ -f "${BASE}/lib/libmongocrypt.dylib" ]; then
        export PYMONGOCRYPT_LIB=${BASE}/lib/libmongocrypt.dylib
    elif [ -f "${BASE}/bin/mongocrypt.dll" ]; then
        PYMONGOCRYPT_LIB=${BASE}/bin/mongocrypt.dll
        # libmongocrypt's windows dll is not marked executable.
        chmod +x $PYMONGOCRYPT_LIB
        export PYMONGOCRYPT_LIB=$(cygpath -m $PYMONGOCRYPT_LIB)
    elif [ -f "${BASE}/lib64/libmongocrypt.so" ]; then
        export PYMONGOCRYPT_LIB=${BASE}/lib64/libmongocrypt.so
    else
        echo "Cannot find libmongocrypt shared object file"
        exit 1
    fi

    # TODO: Test with 'pip install pymongocrypt'
    git clone --branch master https://github.com/mongodb/libmongocrypt.git libmongocrypt_git
    python -m pip install --prefer-binary -r .evergreen/test-encryption-requirements.txt
    python -m pip install ./libmongocrypt_git/bindings/python
    python -c "import pymongocrypt; print('pymongocrypt version: '+pymongocrypt.__version__)"
    python -c "import pymongocrypt; print('libmongocrypt version: '+pymongocrypt.libmongocrypt_version())"
    # PATH is updated by PREPARE_SHELL for access to mongocryptd.

    # Get access to the AWS temporary credentials:
    # CSFLE_AWS_TEMP_ACCESS_KEY_ID, CSFLE_AWS_TEMP_SECRET_ACCESS_KEY, CSFLE_AWS_TEMP_SESSION_TOKEN
    . $DRIVERS_TOOLS/.evergreen/csfle/set-temp-creds.sh
fi

# Run the tests, and store the results in Evergreen compatible XUnit XML
${TOX_BINARY} -e ${TOX_ENV} ${SETUP_ARGS} "$@"
