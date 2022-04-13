import asyncio
import os

from bson import json_util
from bson.codec_options import CodecOptions
from pymongo.encryption import Algorithm
from pymongo.encryption_options import AutoEncryptionOpts

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorClientEncryption


async def create_json_schema_file(kms_providers, key_vault_namespace, key_vault_client):
    client_encryption = AsyncIOMotorClientEncryption(
        kms_providers,
        key_vault_namespace,
        key_vault_client,
        # The CodecOptions class used for encrypting and decrypting.
        # This should be the same CodecOptions instance you have configured
        # on MotorClient, Database, or Collection. We will not be calling
        # encrypt() or decrypt() in this example so we can use any
        # CodecOptions.
        CodecOptions(),
    )

    # Create a new data key and json schema for the encryptedField.
    # https://dochub.mongodb.org/core/client-side-field-level-encryption-automatic-encryption-rules
    data_key_id = await client_encryption.create_data_key(
        "local", key_alt_names=["pymongo_encryption_example_1"]
    )
    schema = {
        "properties": {
            "encryptedField": {
                "encrypt": {
                    "keyId": [data_key_id],
                    "bsonType": "string",
                    "algorithm": Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic,
                }
            }
        },
        "bsonType": "object",
    }
    # Use CANONICAL_JSON_OPTIONS so that other drivers and tools will be
    # able to parse the MongoDB extended JSON file.
    json_schema_string = json_util.dumps(schema, json_options=json_util.CANONICAL_JSON_OPTIONS)

    with open("jsonSchema.json", "w") as file:
        file.write(json_schema_string)


async def main():
    # The MongoDB namespace (db.collection) used to store the
    # encrypted documents in this example.
    encrypted_namespace = "test.coll"

    # This must be the same master key that was used to create
    # the encryption key.
    local_master_key = os.urandom(96)
    kms_providers = {"local": {"key": local_master_key}}

    # The MongoDB namespace (db.collection) used to store
    # the encryption data keys.
    key_vault_namespace = "encryption.__pymongoTestKeyVault"
    key_vault_db_name, key_vault_coll_name = key_vault_namespace.split(".", 1)

    # The MotorClient used to access the key vault (key_vault_namespace).
    key_vault_client = AsyncIOMotorClient()
    key_vault = key_vault_client[key_vault_db_name][key_vault_coll_name]
    # Ensure that two data keys cannot share the same keyAltName.
    await key_vault.drop()
    await key_vault.create_index(
        "keyAltNames", unique=True, partialFilterExpression={"keyAltNames": {"$exists": True}}
    )

    await create_json_schema_file(kms_providers, key_vault_namespace, key_vault_client)

    # Load the JSON Schema and construct the local schema_map option.
    with open("jsonSchema.json", "r") as file:
        json_schema_string = file.read()
    json_schema = json_util.loads(json_schema_string)
    schema_map = {encrypted_namespace: json_schema}

    auto_encryption_opts = AutoEncryptionOpts(
        kms_providers, key_vault_namespace, schema_map=schema_map
    )

    client = AsyncIOMotorClient(auto_encryption_opts=auto_encryption_opts)
    db_name, coll_name = encrypted_namespace.split(".", 1)
    coll = client[db_name][coll_name]
    # Clear old data
    await coll.drop()

    await coll.insert_one({"encryptedField": "123456789"})
    decrypted_doc = await coll.find_one()
    print("Decrypted document: %s" % (decrypted_doc,))
    unencrypted_coll = AsyncIOMotorClient()[db_name][coll_name]
    encrypted_doc = await unencrypted_coll.find_one()
    print("Encrypted document: %s" % (encrypted_doc,))


if __name__ == "__main__":
    asyncio.run(main())
