from flask import Flask
app = Flask(__name__)

from flask import request, jsonify, Response
from flask_restful import Resource, Api
from logging.config import dictConfig
import os
import json
import logging

import time
import uuid

from src.WMCC import (
    extractParams,
    enQueueJob,
    RESULTDATA_PATH,
    LOGLEVEL,
    APP_LOG_FILE_LOCATION,
    DUMP_OUT_REQUEST,
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
        if DUMP_OUT_REQUEST:
            logging.debug("request: %s" % data)

        # -----------------------------------

        try:
            data = {
                **data,
                "productName": data["productData"]["productName"],
                "template":  {
                                # **data["productData"]["template"],
                              "materials": data["productData"]["materialData"],
                              "ARCHICAD_template": data["archicadTemplate"],
                              },
                "variationsData": [{**vD,
                                    "parameters": [{**p,
                                                    "name": p["name"],
                                                    "value": p["value"],} for p in vD["parameters"] if p["group"] == "dimensional"],
                                    "materialParameters": [{**p,
                                                    "name": p["name"],
                                                    "value": p["value"],} for p in vD["parameters"] if p["group"] == "material" or p["group"] == "materialAppearance"],
                                    "dataParameters": [{**p,
                                                    "name": p["name"],
                                                    "value": p["value"],} for p in vD["parameters"] if p["group"] == "data"],
                                    } for vD in data["productData"]["variationsData"]],
            }
        except KeyError as e:
            raise WMCCException(WMCCException.ERR_MALFORMED_REQUEST, additional_data={
                "key": e.args,
                "request": data})

        # -----------------------------------

        pid = str(uuid.uuid4()).upper()
        logging.debug("".join(["/", "PID: ", str(pid)]))
        enQueueJob("/", data, pid)

        return {}
        # return getResult(pid)


class ParameterExtractorEngine(Resource):
    """
    Extracting all parameters from a given GDL object, returning it in json
    """
    def post(self):
        data = request.get_json()
        params = extractParams(data)
        return params


class CreateMaterials(Resource):
    def post(self):
        try:
            data = request.get_json()

            if DUMP_OUT_REQUEST:
                logging.debug("request: %s" % data)

            pid = str(uuid.uuid4()).upper()
            logging.debug("".join(["/creatematerials ", "PID: ", str(pid)]))

            #-----------------------------------
            #FIXME some better productName; main_macroset_version
            try:
                data = {
                    **data,
                    "productName": data["productData"]["productName"],
                    "template": {
                        "materialParameters": [],
                        "materials": [{"name": m["variationName"],
                                       **{p["name"]: p["value"] for p in m["parameters"]},
                                       }  for m in data["productData"]["variationsData"]],
                        "ARCHICAD_template": {
                            "category": "commons",
                            "main_macroset_version": "18",
                        }
                    },
                    "variationsData": []
                }
            except KeyError as e:
                raise WMCCException(WMCCException.ERR_MALFORMED_REQUEST, additional_data={"request": data,
                                                                                          "error": e, })

            #-----------------------------------

            enQueueJob("/creatematerials", data, pid)

            # return getResult(pid)
            return {}
        except Exception as e:
            raise WMCCException(WMCCException.ERR_UNSPECIFIED, additional_data={"request": data if data else None,
                                                                                "error": e, })


api.add_resource(ArchicadEngine,            '/')
api.add_resource(CreateMaterials,           '/creatematerials')
api.add_resource(ParameterExtractorEngine,  '/extractparams')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
