import os
from azure.servicebus import ServiceBusClient, QueueClient, Message

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
    WMCCException
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


def testWorker():
    logging.info("testWorker started")

    queue_client = QueueClient.from_connection_string(CONNECTION_STRING, SERVICEBUS_QUEUE_NAME)

    with queue_client.get_receiver() as queue_receiver:
        message = queue_receiver.next()

        while True:
            job = json.loads(str(message))
            message.complete()

            logging.debug(f"**** Job started: {job['PID']} ****")

            endPoint = job['endPoint']

            resultDict = {}

            try:
                if endPoint == "/":
                    result = createBrandedProduct(job['data'])
                elif endPoint == "/createmacroset":
                    #FIXME remove this since not called anymore through web, now only for tests
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
            message = queue_receiver.next()


if __name__ == '__main__':
    testWorker()