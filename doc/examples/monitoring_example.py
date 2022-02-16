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
            "Command {0.command_name} with request id "
            "{0.request_id} started on server "
            "{0.connection_id}".format(event)
        )

    def succeeded(self, event):
        logging.info(
            "Command {0.command_name} with request id "
            "{0.request_id} on server {0.connection_id} "
            "succeeded in {0.duration_micros} "
            "microseconds".format(event)
        )

    def failed(self, event):
        logging.info(
            "Command {0.command_name} with request id "
            "{0.request_id} on server {0.connection_id} "
            "failed in {0.duration_micros} "
            "microseconds".format(event)
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
        logging.info("Server {0.server_address} added to topology {0.topology_id}".format(event))

    def description_changed(self, event):
        previous_server_type = event.previous_description.server_type
        new_server_type = event.new_description.server_type
        if new_server_type != previous_server_type:
            logging.info(
                "Server {0.server_address} changed type from "
                "{0.previous_description.server_type_name} to "
                "{0.new_description.server_type_name}".format(event)
            )

    def closed(self, event):
        logging.warning(
            "Server {0.server_address} removed from topology {0.topology_id}".format(event)
        )


monitoring.register(ServerLogger())
# server logger end


# topology logger start
class TopologyLogger(monitoring.TopologyListener):
    def opened(self, event):
        logging.info("Topology with id {0.topology_id} opened".format(event))

    def description_changed(self, event):
        logging.info("Topology description updated for topology id {0.topology_id}".format(event))
        previous_topology_type = event.previous_description.topology_type
        new_topology_type = event.new_description.topology_type
        if new_topology_type != previous_topology_type:
            logging.info(
                "Topology {0.topology_id} changed type from "
                "{0.previous_description.topology_type_name} to "
                "{0.new_description.topology_type_name}".format(event)
            )

    def closed(self, event):
        logging.info("Topology with id {0.topology_id} closed".format(event))


monitoring.register(TopologyLogger())
# topology logger end


# heartbeat logger start
class HeartbeatLogger(monitoring.ServerHeartbeatListener):
    def started(self, event):
        logging.info("Heartbeat sent to server {0.connection_id}".format(event))

    def succeeded(self, event):
        logging.info(
            "Heartbeat to server {0.connection_id} "
            "succeeded with reply "
            "{0.reply.document}".format(event)
        )

    def failed(self, event):
        logging.warning(
            "Heartbeat to server {0.connection_id} failed with error {0.reply}".format(event)
        )


monitoring.register(HeartbeatLogger())
# heartbeat logger end
