import asyncio
import os

from pymongo.encryption import Algorithm
from pymongo.encryption_options import AutoEncryptionOpts

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorClientEncryption


async def main():
    # This must be the same master key that was used to create
    # the encryption key.
    local_master_key = os.urandom(96)
    kms_providers = {"local": {"key": local_master_key}}

    # The MongoDB namespace (db.collection) used to store
    # the encryption data keys.
    key_vault_namespace = "encryption.__pymongoTestKeyVault"
    key_vault_db_name, key_vault_coll_name = key_vault_namespace.split(".", 1)

    # bypass_auto_encryption=True disable automatic encryption but keeps
    # the automatic _decryption_ behavior. bypass_auto_encryption will
    # also disable spawning mongocryptd.
    auto_encryption_opts = AutoEncryptionOpts(
        kms_providers, key_vault_namespace, bypass_auto_encryption=True
    )

    client = AsyncIOMotorClient(auto_encryption_opts=auto_encryption_opts)
    coll = client.test.coll
    # Clear old data
    await coll.drop()

    # Set up the key vault (key_vault_namespace) for this example.
    key_vault = client[key_vault_db_name][key_vault_coll_name]
    # Ensure that two data keys cannot share the same keyAltName.
    await key_vault.drop()
    await key_vault.create_index(
        "keyAltNames", unique=True, partialFilterExpression={"keyAltNames": {"$exists": True}}
    )

    client_encryption = AsyncIOMotorClientEncryption(
        kms_providers,
        key_vault_namespace,
        # The MotorClient to use for reading/writing to the key vault.
        # This can be the same MotorClient used by the main application.
        client,
        # The CodecOptions class used for encrypting and decrypting.
        # This should be the same CodecOptions instance you have configured
        # on MotorClient, Database, or Collection.
        coll.codec_options,
    )

    # Create a new data key for the encryptedField.
    _ = await client_encryption.create_data_key(
        "local", key_alt_names=["pymongo_encryption_example_4"]
    )

    # Explicitly encrypt a field:
    encrypted_field = await client_encryption.encrypt(
        "123456789",
        Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic,
        key_alt_name="pymongo_encryption_example_4",
    )
    await coll.insert_one({"encryptedField": encrypted_field})
    # Automatically decrypts any encrypted fields.
    doc = await coll.find_one()
    print("Decrypted document: %s" % (doc,))
    unencrypted_coll = AsyncIOMotorClient().test.coll
    print("Encrypted document: %s" % (await unencrypted_coll.find_one(),))

    # Cleanup resources.
    await client_encryption.close()


if __name__ == "__main__":
    asyncio.run(main())
