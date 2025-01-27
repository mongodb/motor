# Copyright 2016 MongoDB, Inc.
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


"""Application Performance Monitoring (APM) example"""

# command logger start
import logging
import sys

from pymongo import monitoring

logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class CommandLogger(monitoring.CommandListener):
    def started(self, event):
        logging.info(
            f"Command {event.command_name} with request id "
            f"{event.request_id} started on server "
            f"{event.connection_id}"
        )

    def succeeded(self, event):
        logging.info(
            f"Command {event.command_name} with request id "
            f"{event.request_id} on server {event.connection_id} "
            f"succeeded in {event.duration_micros} "
            "microseconds"
        )

    def failed(self, event):
        logging.info(
            f"Command {event.command_name} with request id "
            f"{event.request_id} on server {event.connection_id} "
            f"failed in {event.duration_micros} "
            "microseconds"
        )


# command logger end

# command logger register start
monitoring.register(CommandLogger())
# command logger register end

# motorclient start
from tornado import gen, ioloop

from motor import MotorClient

client = MotorClient()


async def do_insert():
    await client.test.collection.insert_one({"message": "hi!"})

    # For this example, wait 10 seconds for more monitoring events to fire.
    await gen.sleep(10)


ioloop.IOLoop.current().run_sync(do_insert)
# motorclient end


# server logger start
class ServerLogger(monitoring.ServerListener):
    def opened(self, event):
        logging.info(f"Server {event.server_address} added to topology {event.topology_id}")

    def description_changed(self, event):
        previous_server_type = event.previous_description.server_type
        new_server_type = event.new_description.server_type
        if new_server_type != previous_server_type:
            logging.info(
                f"Server {event.server_address} changed type from "
                f"{event.previous_description.server_type_name} to "
                f"{event.new_description.server_type_name}"
            )

    def closed(self, event):
        logging.warning(f"Server {event.server_address} removed from topology {event.topology_id}")


monitoring.register(ServerLogger())
# server logger end


# topology logger start
class TopologyLogger(monitoring.TopologyListener):
    def opened(self, event):
        logging.info(f"Topology with id {event.topology_id} opened")

    def description_changed(self, event):
        logging.info(f"Topology description updated for topology id {event.topology_id}")
        previous_topology_type = event.previous_description.topology_type
        new_topology_type = event.new_description.topology_type
        if new_topology_type != previous_topology_type:
            logging.info(
                f"Topology {event.topology_id} changed type from "
                f"{event.previous_description.topology_type_name} to "
                f"{event.new_description.topology_type_name}"
            )

    def closed(self, event):
        logging.info(f"Topology with id {event.topology_id} closed")


monitoring.register(TopologyLogger())
# topology logger end


# heartbeat logger start
class HeartbeatLogger(monitoring.ServerHeartbeatListener):
    def started(self, event):
        logging.info(f"Heartbeat sent to server {event.connection_id}")

    def succeeded(self, event):
        logging.info(
            f"Heartbeat to server {event.connection_id} "
            "succeeded with reply "
            f"{event.reply.document}"
        )

    def failed(self, event):
        logging.warning(
            f"Heartbeat to server {event.connection_id} failed with error {event.reply}"
        )


monitoring.register(HeartbeatLogger())
# heartbeat logger end
