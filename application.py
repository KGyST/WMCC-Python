from flask import Flask
app = Flask(__name__)

from flask import request, jsonify, Response
from flask_restful import Resource, Api
from logging.config import dictConfig
import os
import json
import functools
import logging

import time
import signal
import uuid

from azure.servicebus import ServiceBusClient, QueueClient, Message

from src.WMCC import (
    extractParams,
    enQueueJob,
    RESULTDATA_PATH,
    LOGLEVEL,
    APP_LOG_FILE_LOCATION,
    WMCCException
)

if isinstance(LOGLEVEL, str):
    LOGLEVEL = {'notset':   0,
                'debug':    10,
                'info':     20,
                'warning':  30,
                'error':    40,
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
            'filename': APP_LOG_FILE_LOCATION
        }
    },
    'root': {
        'level': LOGLEVEL,
        'handlers': ['wsgi', 'custom_handler']
    }
})




api = Api(app)

def getResult(inPID):
    result = None
    sPID = str(inPID)

    while not result:
        while not os.access(RESULTDATA_PATH, os.R_OK):
            time.sleep(1)
        with open(RESULTDATA_PATH, "r") as resultFile:
            try:
                resultQueue = json.load(resultFile)
            except json.JSONDecodeError:
                #WTF
                pass
            if sPID in resultQueue:
                result = resultQueue[sPID]
                del resultQueue[sPID]
        if result:
            while not os.access(RESULTDATA_PATH, os.W_OK):
                time.sleep(1)
            with open(RESULTDATA_PATH, "w") as resultFile:
                json.dump(resultQueue, resultFile, indent=4)

    return result


class ArchicadEngine(Resource):
    def get(self):
        logging.debug("ArchicadEngine was called with a GET message")
        return {"GET": "It's working!"}

    def post(self):
        data = request.get_json()

        # -----------------------------------

        try:
            data = {
                **data,
                "productName": data["ProductName"],
                "template":  {**data["Template"],
                              "materials": [{**m,
                                             "name": m["Name"], } for m in data["Template"]["Materials"]],
                              "ARCHICAD_template": data["Template"]["ArchicadTemplate"],
                              },
                "variationsData": [{**vD,
                                    "variationName": vD["VariationName"],
                                    "parameters": [{**p,
                                                    "name": p["Name"],
                                                    "value": p["Value"],} for p in vD["Parameters"] if p["Group"] == 1],
                                    "materialParameters": [{**p,
                                                    "name": p["Name"],
                                                    "value": p["Value"],} for p in vD["Parameters"] if p["Group"] == 2 or p["Group"] == 4],
                                    "dataParameters": [{**p,
                                                    "name": p["Name"],
                                                    "value": p["Value"],} for p in vD["Parameters"] if p["Group"] == 3],
                                    } for vD in data["VariationsData"]],
            }
        except KeyError as e:
            raise WMCCException(WMCCException.ERR_MALFORMED_REQUEST, additional_data={"request": data, "exception data": e.__str__()})

        # -----------------------------------

        pid = str(uuid.uuid4()).upper()
        logging.debug("".join(["/", "PID: ", str(pid)]))
        enQueueJob("/", data, pid)

        return getResult(pid)


class CreateLCFEngine(Resource):
    """
    Creating macroset, to be used by internal GDL developers
    """
    def post(self):
        data = request.get_json()

        pid = str(uuid.uuid4()).upper()
        logging.debug("".join(["/createmacroset", "PID: ", str(pid)]))

        enQueueJob("/createmacroset", data, pid)

        return getResult(pid)


class ParameterExtractorEngine(Resource):
    """
    Extracting all parameters from a given GDL object, returning it in json
    """
    def post(self):
        data = request.get_json()
        params = extractParams(data)
        return params


class ReceiveFile_Test(Resource):
    """
    dummy class mimicing receiver side, only for testing purposes
    """
    def post(self):
        import os
        import base64
        import logging
        TARGET_DIR = os.path.join(r".\src", r"Target2")

        data = request.get_json()

        logging.info(f"ReceiveFile_Test {data['object_name']} ")

        with open(os.path.join(TARGET_DIR, data['object_name']), 'wb') as objectFile:
            decode = base64.urlsafe_b64decode(data['base64_encoded_object'])
            objectFile.write(decode)

        with open(os.path.join(TARGET_DIR, data['macroset_name']), 'wb') as objectFile:
            decode = base64.urlsafe_b64decode(data['base64_encoded_macroset'])
            objectFile.write(decode)

        return ({"result": "00, OK, 00, 00"})


class CreateMaterials(Resource):
    def post(self):
        try:
            data = request.get_json()

            pid = str(uuid.uuid4()).upper()
            logging.debug("".join(["/creatematerials ", "PID: ", str(pid)]))

            #-----------------------------------
            #FIXME some better productName; main_macroset_version
            try:
                data = {
                    **data,
                    "productName": data["ProductName"],
                    "template": {
                        "materialParameters": [],
                        "materials": [{"name": m["VariationName"],
                                       **{p["Name"]: p["Value"] for p in m["Parameters"]},
                                       }  for m in data["VariationsData"]],
                        "ARCHICAD_template": {
                            "category": "commons",
                            "main_macroset_version": "18",
                        }
                    },
                    "variationsData": []
                }
            except KeyError:
                raise WMCCException(WMCCException.ERR_MALFORMED_REQUEST, additional_data={"request": data})

            #-----------------------------------

            enQueueJob("/creatematerials", data, pid)

            return getResult(pid)
        except Exception:
            raise WMCCException(WMCCException.ERR_UNSPECIFIED, additional_data={"request": data if data else None})


api.add_resource(ArchicadEngine,            '/')
api.add_resource(CreateMaterials,           '/creatematerials')
api.add_resource(ParameterExtractorEngine,  '/extractparams')

# To be REMOVED:
api.add_resource(CreateLCFEngine,           '/createmacroset')
api.add_resource(ReceiveFile_Test,          '/setfile')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
