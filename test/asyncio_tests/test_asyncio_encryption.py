# Copyright 2021-present MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test Explicit Encryption with AsyncIOMotorClient."""

import unittest
import uuid
from test import env
from test.asyncio_tests import AsyncIOTestCase, asyncio_test

from bson.binary import JAVA_LEGACY, STANDARD, UUID_SUBTYPE, Binary
from bson.codec_options import CodecOptions
from bson.errors import BSONError
from pymongo.encryption import Algorithm
from pymongo.errors import InvalidOperation

from motor.motor_asyncio import AsyncIOMotorClientEncryption

KMS_PROVIDERS = {"local": {"key": b"\x00" * 96}}

OPTS = CodecOptions(uuid_representation=STANDARD)


class TestExplicitSimple(AsyncIOTestCase):
    @env.require_csfle
    def setUp(self):
        super().setUp()

    def assertEncrypted(self, val):
        self.assertIsInstance(val, Binary)
        self.assertEqual(val.subtype, 6)

    def assertBinaryUUID(self, val):
        self.assertIsInstance(val, Binary)
        self.assertEqual(val.subtype, UUID_SUBTYPE)

    @asyncio_test
    async def test_encrypt_decrypt(self):
        client = self.asyncio_client()
        client_encryption = AsyncIOMotorClientEncryption(
            KMS_PROVIDERS, "keyvault.datakeys", client, OPTS
        )
        # Use standard UUID representation.
        key_vault = client.keyvault.get_collection("datakeys", codec_options=OPTS)

        # Create the encrypted field's data key.
        key_id = await client_encryption.create_data_key("local", key_alt_names=["name"])
        self.assertBinaryUUID(key_id)
        self.assertTrue(await key_vault.find_one({"_id": key_id}))

        # Create an unused data key to make sure filtering works.
        unused_key_id = await client_encryption.create_data_key("local", key_alt_names=["unused"])
        self.assertBinaryUUID(unused_key_id)
        self.assertTrue(await key_vault.find_one({"_id": unused_key_id}))

        doc = {"_id": 0, "ssn": "000"}
        encrypted_ssn = await client_encryption.encrypt(
            doc["ssn"], Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic, key_id=key_id
        )

        # Ensure encryption via key_alt_name for the same key produces the
        # same output.
        encrypted_ssn2 = await client_encryption.encrypt(
            doc["ssn"], Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic, key_alt_name="name"
        )
        self.assertEqual(encrypted_ssn, encrypted_ssn2)

        # Test decryption.
        decrypted_ssn = await client_encryption.decrypt(encrypted_ssn)
        self.assertEqual(decrypted_ssn, doc["ssn"])

        await key_vault.drop()
        await client_encryption.close()

    @asyncio_test
    async def test_validation(self):
        client = self.asyncio_client()
        client_encryption = AsyncIOMotorClientEncryption(
            KMS_PROVIDERS, "keyvault.datakeys", client, OPTS
        )

        msg = "value to decrypt must be a bson.binary.Binary with subtype 6"
        with self.assertRaisesRegex(TypeError, msg):
            await client_encryption.decrypt("str")
        with self.assertRaisesRegex(TypeError, msg):
            await client_encryption.decrypt(Binary(b"123"))

        msg = "key_id must be a bson.binary.Binary with subtype 4"
        algo = Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic
        with self.assertRaisesRegex(TypeError, msg):
            await client_encryption.encrypt("str", algo, key_id=uuid.uuid4())
        with self.assertRaisesRegex(TypeError, msg):
            await client_encryption.encrypt("str", algo, key_id=Binary(b"123"))

        await client_encryption.close()

    @asyncio_test
    async def test_bson_errors(self):
        client = self.asyncio_client()
        client_encryption = AsyncIOMotorClientEncryption(
            KMS_PROVIDERS, "keyvault.datakeys", client, OPTS
        )

        # Attempt to encrypt an unencodable object.
        unencodable_value = object()
        with self.assertRaises(BSONError):
            await client_encryption.encrypt(
                unencodable_value,
                Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic,
                key_id=Binary(uuid.uuid4().bytes, UUID_SUBTYPE),
            )

        await client_encryption.close()

    @asyncio_test
    async def test_codec_options(self):
        client = self.asyncio_client()
        with self.assertRaisesRegex(TypeError, "codec_options must be"):
            AsyncIOMotorClientEncryption(KMS_PROVIDERS, "keyvault.datakeys", client, None)

        opts = CodecOptions(uuid_representation=JAVA_LEGACY)
        client_encryption_legacy = AsyncIOMotorClientEncryption(
            KMS_PROVIDERS, "keyvault.datakeys", client, opts
        )

        # Create the encrypted field's data key.
        key_id = await client_encryption_legacy.create_data_key("local")

        # Encrypt a UUID with JAVA_LEGACY codec options.
        value = uuid.uuid4()
        encrypted_legacy = await client_encryption_legacy.encrypt(
            value, Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic, key_id=key_id
        )
        decrypted_value_legacy = await client_encryption_legacy.decrypt(encrypted_legacy)
        self.assertEqual(decrypted_value_legacy, value)

        # Encrypt the same UUID with STANDARD codec options.
        client_encryption = AsyncIOMotorClientEncryption(
            KMS_PROVIDERS, "keyvault.datakeys", client, OPTS
        )
        encrypted_standard = await client_encryption.encrypt(
            value, Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic, key_id=key_id
        )
        decrypted_standard = await client_encryption.decrypt(encrypted_standard)
        self.assertEqual(decrypted_standard, value)

        # Test that codec_options is applied during encryption.
        self.assertNotEqual(encrypted_standard, encrypted_legacy)
        # Test that codec_options is applied during decryption.
        self.assertEqual(
            await client_encryption_legacy.decrypt(encrypted_standard),
            Binary.from_uuid(value, uuid_representation=STANDARD),
        )
        self.assertNotEqual(await client_encryption.decrypt(encrypted_legacy), value)

        await client_encryption_legacy.close()
        await client_encryption.close()

    @asyncio_test
    async def test_close(self):
        client = self.asyncio_client()
        client_encryption = AsyncIOMotorClientEncryption(
            KMS_PROVIDERS, "keyvault.datakeys", client, OPTS
        )
        await client_encryption.close()
        # Close can be called multiple times.
        await client_encryption.close()
        algo = Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Deterministic
        msg = "Cannot use closed ClientEncryption"
        with self.assertRaisesRegex(InvalidOperation, msg):
            await client_encryption.create_data_key("local")
        with self.assertRaisesRegex(InvalidOperation, msg):
            await client_encryption.encrypt("val", algo, key_alt_name="name")
        with self.assertRaisesRegex(InvalidOperation, msg):
            await client_encryption.decrypt(Binary(b"", 6))

    @asyncio_test
    async def test_with_statement(self):
        client = self.asyncio_client()
        async with AsyncIOMotorClientEncryption(
            KMS_PROVIDERS, "keyvault.datakeys", client, OPTS
        ) as client_encryption:
            pass
        with self.assertRaisesRegex(InvalidOperation, "Cannot use closed ClientEncryption"):
            await client_encryption.create_data_key("local")


if __name__ == "__main__":
    unittest.main()
