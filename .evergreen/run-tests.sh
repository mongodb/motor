#!/bin/sh
set -o xtrace   # Write all commands first to stderr
set -o errexit  # Exit the script with error if any of the commands fail

# Supported/used environment variables:
#       AUTH                    Set to enable authentication. Defaults to "noauth"
#       SSL                     Set to enable SSL. Defaults to "nossl"
#       MONGODB_URI             Set the suggested connection MONGODB_URI (including credentials and topology info)
#       MARCH                   Machine Architecture. Defaults to lowercase uname -m


AUTH=${AUTH:-noauth}
SSL=${SSL:-nossl}
MONGODB_URI=${MONGODB_URI:-}

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
[ -z "$MARCH" ] && MARCH=$(uname -m | tr '[:upper:]' '[:lower:]')


if [ "$AUTH" != "noauth" ]; then
  export DB_USER="bob"
  export DB_PASSWORD="pwd123"
fi

if [ "$SSL" != "nossl" ]; then
   export CERT_DIR="$DRIVERS_TOOLS/.evergreen/x509gen"
fi

echo "Running $AUTH tests over $SSL, connecting to $MONGODB_URI"

export DB_IP=localhost
export ASYNC_TEST_TIMEOUT=30
export TOX_TESTENV_PASSENV="JENKINS DB_IP ASYNC_TEST_TIMEOUT"

export MOTOR_TEST_DEPENDENCIES="pytest"
export MOTOR_TEST_RUNNER="python -m pytest -x --junitxml={envname}-results.xml"

# Don't rely on build machine having pip and virtualenv installed globally.
curl -LO https://pypi.python.org/packages/d4/0c/9840c08189e030873387a73b90ada981885010dd9aea134d6de30cd24cb8/virtualenv-15.1.0.tar.gz
tar xzf virtualenv-15.1.0.tar.gz
python3 ./virtualenv-15.1.0/virtualenv.py .tox-venv
./.tox-venv/bin/pip install tox

# TODO: run all environments:
# tox or tox --skip-missing-interpreters
./.tox-venv/bin/python3 -m tox -e py35-tornado4
