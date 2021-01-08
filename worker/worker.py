import os
from azure.servicebus import ServiceBusClient, exceptions

import json
import logging
import shutil
from logging.config import dictConfig
import uuid
from urllib.parse import urlparse

from azure.storage.blob import BlobServiceClient

import http, ssl

os.chdir(r"..")

from src.WMCC import (
    createBrandedProduct,
    RESULTDATA_PATH,
    LOGLEVEL,
    WORKER_LOG_FILE_LOCATION,
    CONNECTION_STRING,
    SERVICEBUS_QUEUE_NAME,
    TARGET_GDL_DIR_NAME,
    CLEANUP,
    WMCCException,
    STORAGE_NAME,
    RESULT_CONTAINER_NAME,
    RESULT_CONN_STRING
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
    logging.info("worker started")
    container_name  = RESULT_CONTAINER_NAME
    connect_str     = RESULT_CONN_STRING

    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    # container_client = blob_service_client.get_container_client(container_name)

    with open(RESULTDATA_PATH, "w") as resultFile:
        json.dump({} , resultFile, indent=4)

    queue_client = ServiceBusClient.from_connection_string(CONNECTION_STRING)

    with queue_client.get_queue_receiver(SERVICEBUS_QUEUE_NAME) as queue_receiver:
        with queue_receiver:
            for message in queue_receiver:
                job = json.loads(str(message))

                logging.debug(f"**** Job started: {job['PID']} ****")

                endPoint = job['endPoint']

                resultDict = {}
                result = None
                placeableLCFDir = None

                try:
                    if endPoint == "/":
                        result, placeableLCFDir = createBrandedProduct(job['data'])
                    elif endPoint == "/creatematerials":
                        result, placeableLCFDir = createBrandedProduct(job['data'])
                except WMCCException as e:
                    result = e.description
                except Exception as e:
                    we = WMCCException(WMCCException.ERR_UNSPECIFIED, additional_data={"error_message": e.args,
                                                                                       "request": job['data']})
                    result = we.description

                if "localhost" in job["data"]["host"]:
                    conn = http.client.HTTPConnection(job["data"]["host"])
                else:
                    s = ssl.SSLContext()
                    conn = http.client.HTTPSConnection(job["data"]["host"], context=s)
                headers = {"Content-Type": "application/json"}

                response = None

                try:
                    if "placeableName" in result:
                        endp = urlparse(job["data"]["archicadCallbackForObject"])
                        endp = "?".join((endp.path, endp.query,))
                        blobName = str(uuid.uuid4())
                        result["placeableURL"] = f"https://{STORAGE_NAME}.blob.core.windows.net/{container_name}/{blobName}"
                        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blobName)
                        with open(os.path.join(placeableLCFDir, result["placeableName"]), "rb") as placeable:
                            blob_client.upload_blob(placeable, overwrite=True)
                        req = {"Name": result["placeableName"],
                               "DownloadUrl": result["placeableURL"]}
                        conn.request("POST", endp, json.dumps(req), headers)
                        response = conn.getresponse()

                    if "macrosetName" in result:
                        endp = urlparse(job["data"]["archicadCallbackForMacroset"])
                        endp = "?".join((endp.path, endp.query,))
                        blobName = str(uuid.uuid4())
                        result["macrosetURL"] = f"https://{STORAGE_NAME}.blob.core.windows.net/{container_name}/{blobName}"
                        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blobName)
                        with open(os.path.join(TARGET_GDL_DIR_NAME, result["macrosetName"]), "rb") as macroset:
                            blob_client.upload_blob(macroset, overwrite=True)
                        req = {"Name": result["macrosetName"],
                               "DownloadUrl": result["macrosetURL"]}
                        conn.request("POST", endp, json.dumps(req), headers)
                        response = conn.getresponse()

                    if not response:
                        conn.request("POST", endp, json.dumps(result), headers)
                        response = conn.getresponse()

                except (ConnectionRefusedError, ConnectionResetError):
                    logging.debug("ConnectionRefusedError: nobody at receiver side")

                if CLEANUP:
                    shutil.rmtree(result["placeableLCFPath"])
                    os.remove(os.path.join(TARGET_GDL_DIR_NAME, result["placeableName"]))

                if os.path.exists(RESULTDATA_PATH):
                    resultDict = json.load(open(RESULTDATA_PATH, "r"))

                resultDict.update({str(job["PID"]): result})

                with open(RESULTDATA_PATH, "w") as resultFile:
                    json.dump(resultDict, resultFile, indent=4)

                resultFile.close()
                try:
                    queue_receiver.complete_message(message)
                except (exceptions.MessageLockLostError, exceptions.ServiceBusError):
                    logging.error("MessageLockExpired exception caught")


if __name__ == '__main__':
    testWorker()