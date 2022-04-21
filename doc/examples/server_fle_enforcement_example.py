import asyncio
import os

from bson.binary import STANDARD
from bson.codec_options import CodecOptions
from pymongo.encryption import Algorithm
from pymongo.encryption_options import AutoEncryptionOpts
from pymongo.errors import OperationFailure
from pymongo.write_concern import WriteConcern

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorClientEncryption


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
    data_key_id = await client_encryption.create_data_key(
        "local", key_alt_names=["pymongo_encryption_example_2"]
    )
    json_schema = {
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

    auto_encryption_opts = AutoEncryptionOpts(kms_providers, key_vault_namespace)
    client = AsyncIOMotorClient(auto_encryption_opts=auto_encryption_opts)
    db_name, coll_name = encrypted_namespace.split(".", 1)
    db = client[db_name]
    # Clear old data
    await db.drop_collection(coll_name)
    # Create the collection with the encryption JSON Schema.
    await db.create_collection(
        coll_name,
        # uuid_representation=STANDARD is required to ensure that any
        # UUIDs in the $jsonSchema document are encoded to BSON Binary
        # with the standard UUID subtype 4. This is only needed when
        # running the "create" collection command with an encryption
        # JSON Schema.
        codec_options=CodecOptions(uuid_representation=STANDARD),
        write_concern=WriteConcern(w="majority"),
        validator={"$jsonSchema": json_schema},
    )
    coll = client[db_name][coll_name]

    await coll.insert_one({"encryptedField": "123456789"})
    decrypted_doc = await coll.find_one()
    print("Decrypted document: %s" % (decrypted_doc,))
    unencrypted_coll = AsyncIOMotorClient()[db_name][coll_name]
    encrypted_doc = await unencrypted_coll.find_one()
    print("Encrypted document: %s" % (encrypted_doc,))
    try:
        await unencrypted_coll.insert_one({"encryptedField": "123456789"})
    except OperationFailure as exc:
        print("Unencrypted insert failed: %s" % (exc.details,))


if __name__ == "__main__":
    asyncio.run(main())
