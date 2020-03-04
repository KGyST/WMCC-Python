from flask import Flask
app = Flask(__name__)


@app.route("/teszt")
def hello():
    return "teszt"


from flask import Flask, request
from flask_restful import Resource, Api
# import json, jsonpickle
# import os
# import tempfile
# from subprocess import check_output


from archicad.WMCC import (
    createBrandedProduct,
    buildMacroSet,
    extractParams,
)

app = Flask(__name__)
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


api.add_resource(ArchicadEngine, '/')
api.add_resource(CreateLCFEngine, '/createlcf')
api.add_resource(ParameterExtractorEngine, '/extractparams')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
