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

# TODO: run all interpreters:
# tox or tox --skip-missing-interpreters

tox -e tornado4-py27
