#!/bin/bash

# Don't trace to avoid secrets showing up in the logs
set -o errexit
set +x

echo "Running enterprise authentication tests"
source ./secrets-export.sh

export DB_USER="bob"
export DB_PASSWORD="pwd123"

# BUILD-3830
touch ${PROJECT_DIRECTORY}/.evergreen/krb5.conf.empty
export KRB5_CONFIG=${PROJECT_DIRECTORY}/.evergreen/krb5.conf.empty

echo "Writing keytab"
echo ${KEYTAB_BASE64} | base64 -d > ${PROJECT_DIRECTORY}/.evergreen/drivers.keytab
echo "Running kinit"
kinit -k -t ${PROJECT_DIRECTORY}/.evergreen/drivers.keytab -p ${PRINCIPAL}

echo "Setting GSSAPI variables"
export GSSAPI_HOST=${SASL_HOST}
export GSSAPI_PORT=${SASL_PORT}
export GSSAPI_PRINCIPAL=${PRINCIPAL}

# Pass needed env variables to the test environment.
export TOX_ENV="enterprise-synchro"

bash ${PROJECT_DIRECTORY}/.evergreen/run-tox.sh
