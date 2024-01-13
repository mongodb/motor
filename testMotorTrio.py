import trio

from motor.motor_trio import TrioMotorClient


async def main():
    client = TrioMotorClient()

    db = client["database"]
    collection = db["collection"]

    await collection.insert_one({"test": "test"})


trio.run(main)
