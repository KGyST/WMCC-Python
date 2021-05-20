import os
from azure.servicebus import ServiceBusClient, exceptions

import json
import logging
from logging.config import dictConfig

os.chdir(r"..")

from src.WMCC import (
    createBrandedProduct,
    buildMacroSet,
    RESULTDATA_PATH,
    LOGLEVEL,
    WORKER_LOG_FILE_LOCATION,
    CONNECTION_STRING,
    SERVICEBUS_QUEUE_NAME,
    WMCCException,
    RABBITMQ,
    RABBITMQ_HOST_URL,
)

if isinstance(LOGLEVEL, str):
    LOGLEVEL = {'notset': 0,
                'debug': 10,
                'info': 20,
                'warning': 30,
                'error': 40,
                'critical': 50, }[LOGLEVEL]

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        },
        'custom_handler': {
            'class': 'logging.FileHandler',
            'formatter': 'default',
            'filename': WORKER_LOG_FILE_LOCATION
        }
    },
    'root': {
        'level': LOGLEVEL,
        'handlers': ['wsgi', 'custom_handler']
    }
})


def worker_shell():
    logging.info("worker started")
    with open(RESULTDATA_PATH, "w") as resultFile:
        json.dump({} , resultFile, indent=4)

    if RABBITMQ:
        import pika
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST_URL))
        channel = connection.channel()

        channel.queue_declare(queue=SERVICEBUS_QUEUE_NAME)

        channel.basic_consume(queue=SERVICEBUS_QUEUE_NAME, on_message_callback=worker_callback)

        channel.start_consuming()
    else:
        queue_client = ServiceBusClient.from_connection_string(CONNECTION_STRING)

        with queue_client.get_queue_receiver(SERVICEBUS_QUEUE_NAME) as queue_receiver:
            with queue_receiver:
                for message in queue_receiver:
                    worker_callback(None, None, None, str(message))

                    try:
                        queue_receiver.complete_message(message)
                    except (exceptions.MessageLockLostError, exceptions.ServiceBusError):
                        logging.error("MessageLockExpired exception caught")

def worker_callback(ch, method, properties, message):
    job = json.loads(message)

    logging.debug(f"**** Job started: {job['PID']} ****")

    endPoint = job['endPoint']

    resultDict = {}

    try:
        if endPoint == "/":
            result = createBrandedProduct(job['data'])
        elif endPoint == "/createmacroset":
            # FIXME remove this since not called anymore through web, now only for tests
            result = buildMacroSet(job['data'])
        elif endPoint == "/creatematerials":
            result = createBrandedProduct(job['data'])
    except WMCCException as e:
        result = e.description
    except Exception as e:
        we = WMCCException(WMCCException.ERR_UNSPECIFIED, additional_data={"error_message": e.args,
                                                                           "request": job['data']})
        result = we.description

    if os.path.exists(RESULTDATA_PATH):
        resultDict = json.load(open(RESULTDATA_PATH, "r"))

    resultDict.update({str(job["PID"]): result})

    with open(RESULTDATA_PATH, "w") as resultFile:
        json.dump(resultDict, resultFile, indent=4)

    resultFile.close()

    if ch and method:
        ch.basic_ack(delivery_tag=method.delivery_tag)



if __name__ == '__main__':
    worker_shell()