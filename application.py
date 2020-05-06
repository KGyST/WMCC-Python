from flask import Flask
app = Flask(__name__)

from flask import Flask, request
from flask_restful import Resource, Api
from logging.config import dictConfig
import os
import json

import time

_SRC                        = r".\src"
APP_CONFIG                  = os.path.join(_SRC, r"appconfig.json")

with open(APP_CONFIG, "r") as ac:
    appJSON                     = json.load(ac)
    APP_LOG_FILE_LOCATION       = appJSON["APP_LOG_FILE_LOCATION"]
    LOGLEVEL                    = appJSON["LOGLEVEL"]
    JOBDATA_PATH                = os.path.join(_SRC, "Target", appJSON["JOBDATA"])
    RESULTDATA_PATH             = os.path.join(_SRC, "Target", appJSON["RESULTDATA"])

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


from src.WMCC import (
    extractParams,
    enQueueJob,
)

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
        return {"test": "It's working!"}

    def post(self):
        data = request.get_json()

        pid = os.getpid()
        enQueueJob("/", data, pid)

        return getResult(pid)


class CreateLCFEngine(Resource):
    """
    Creating macroset, to be used by internal GDL developers
    """
    def post(self):
        data = request.get_json()

        pid = os.getpid()
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


api.add_resource(ArchicadEngine, '/')
api.add_resource(CreateLCFEngine, '/createmacroset')
api.add_resource(ParameterExtractorEngine, '/extractparams')
api.add_resource(ReceiveFile_Test, '/setfile')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
