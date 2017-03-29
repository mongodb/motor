#!/bin/sh
set -o xtrace   # Write all commands first to stderr
set -o errexit  # Exit the script with error if any of the commands fail

# Supported/used environment variables:
#       AUTH                    Set to enable authentication. Defaults to "noauth"
#       SSL                     Set to enable SSL. Defaults to "nossl"
#       MONGODB_URI             Set the suggested connection MONGODB_URI (including credentials and topology info)
#       TOX_ENV                 Tox environment name, e.g. "tornado4-py36"
#       TOX_BINARY              Path to "tox"

AUTH=${AUTH:-noauth}
SSL=${SSL:-nossl}
MONGODB_URI=${MONGODB_URI:-}

if [ "$AUTH" != "noauth" ]; then
    export DB_USER="bob"
    export DB_PASSWORD="pwd123"
fi

if [ "$SSL" != "nossl" ]; then
    export CLIENT_PEM="$DRIVERS_TOOLS/.evergreen/x509gen/client.pem"
    export CA_PEM="$DRIVERS_TOOLS/.evergreen/x509gen/ca.pem"
fi

# Run the tests, and store the results in Evergreen compatible XUnit XML
$TOX_BINARY -e "$TOX_ENV"
