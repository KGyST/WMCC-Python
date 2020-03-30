from flask import Flask
app = Flask(__name__)

from flask import Flask, request
from flask_restful import Resource, Api
from logging.config import dictConfig
import os
import json

_SRC                        = r".\src"
APP_CONFIG                  = os.path.join(_SRC, r"appconfig.json")

with open(APP_CONFIG, "r") as ac:
    appJSON                     = json.load(ac)
    APP_LOG_FILE_LOCATION       = appJSON["APP_LOG_FILE_LOCATION"]
    LOGLEVEL                    = appJSON["LOGLEVEL"]

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
    createBrandedProduct,
    buildMacroSet,
    extractParams,
)

api = Api(app)

class ArchicadEngine(Resource):
    def get(self):
        return {"test": "it's working!"}

    def post(self):
        data = request.get_json()

        result = createBrandedProduct(data)

        return result


class CreateLCFEngine(Resource):
    """
    Creating macroset, to be used by internal GDL developers
    """
    def post(self):
        data = request.get_json()
        reData = buildMacroSet(data)
        #FIXME what to do with older versions of this file?
        return reData


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

        # string = data['base64_encoded_object']
        # padding = 4 - (len(string) % 4)
        # string = string + ("=" * padding)

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
