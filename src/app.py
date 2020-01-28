from flask import Flask, request
from flask_restful import Resource, Api
import json, jsonpickle
import os
import tempfile
from subprocess import check_output


from archicad.WMCC import (
    createBrandedProduct,
    buildMacroSet,
)

app = Flask(__name__)
api = Api(app)


class ArchicadEngine(Resource):
    def get(self):
        return {"test": "it's working!"}

    def post(self):
        data = request.get_json()

        createBrandedProduct(data)

        return {"result": data}


class CreateLCFEngine(Resource):
    def post(selfs):
        data = request.get_json()
        buildMacroSet(data['folder_names'])
        return 0


api.add_resource(ArchicadEngine, '/')
api.add_resource(CreateLCFEngine, '/createlcf')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
