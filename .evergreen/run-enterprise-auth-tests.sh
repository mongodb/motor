#!/bin/bash

# Don't trace to avoid secrets showing up in the logs
set -o errexit

echo "Running enterprise authentication tests"

export DB_USER="bob"
export DB_PASSWORD="pwd123"

echo "Writing keytab"
echo ${KEYTAB_BASE64} | base64 -d > ${PROJECT_DIRECTORY}/.evergreen/drivers.keytab
echo "Running kinit"
kinit -k -t ${PROJECT_DIRECTORY}/.evergreen/drivers.keytab -p ${PRINCIPAL}

echo "Setting GSSAPI variables"
export GSSAPI_HOST=${SASL_HOST}
export GSSAPI_PORT=${SASL_PORT}
export GSSAPI_PRINCIPAL=${PRINCIPAL}

echo "Running tests"
if [ ${PYTHON_VERSION} = "2.7" ]; then
  ENV="tornado4-py27"
else
  ENV="tornado4-py36"
fi

${TOX_BINARY} -e "$TOX_ENV"
