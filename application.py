from flask import Flask             #, request
from flask_restful import Resource, Api
# from archicad.WMCC import (
#     createBrandedProduct,
#     buildMacroSet,
#     extractParams,
# )

app = Flask(__name__)
api = Api(app)

# @app.route("/")
# def hello():
#     return "Hello World!"


# class ArchicadEngine(Resource):
#     def get(self):
#         return {"ArchicadEngine test": "it's working!"}
#
#     def post(self):
#         data = request.get_json()
#
#         result = createBrandedProduct(data)
#
#         return result


# class CreateLCFEngine(Resource):
#     """
#     Creating macroset, to be used by internal GDL developers
#     """
#     def post(self):
#         data = request.get_json()
#         reData = buildMacroSet(data)
#         #FIXME what to do with older versions of this file?
#         return reData
#
#
# class ParameterExtractorEngine(Resource):
#     """
#     Extracting all parameters from a given GDL object, returning it in json
#     """
#     def post(self):
#         data = request.get_json()
#         params = extractParams(data)
#         return params


class TestEngine(Resource):
    def get(self):
        return {"test": "TestEngine 2 is working!"}


api.add_resource(TestEngine, '/')
# api.add_resource(ArchicadEngine, '/')
# api.add_resource(CreateLCFEngine, '/createlcf')
# api.add_resource(ParameterExtractorEngine, '/extractparams')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
