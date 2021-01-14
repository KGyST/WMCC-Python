import os
from azure.servicebus import ServiceBusClient, exceptions
import pprint

os.chdir(r"..")

SERVICEBUS_QUEUE_NAME = os.getenv("SERVICEBUS_QUEUE_NAME")
from src.WMCC import (
    CONNECTION_STRING,
)

queue_client = ServiceBusClient.from_connection_string(CONNECTION_STRING)

with queue_client.get_queue_receiver(SERVICEBUS_QUEUE_NAME) as queue_receiver:
    with queue_receiver:
        for message in queue_receiver:
            pprint.pprint(str(message))
            queue_receiver.complete_message(message)
