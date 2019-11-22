from flask import Flask, request
from flask_restful import Resource, Api
import json

from archicad.WMCC import (
    scanFolders,
    SOURCE_XML_DIR_NAME,
    SOURCE_IMAGE_DIR_NAME,
    addFileRecursively,
    unitConvert,
    startConversion,
    TRANSLATIONS_JSON,
)

app = Flask(__name__)
api = Api(app)


class ArchicadEngine(Resource):
    def get(self):
        return {"test": "it's working!"}

    def post(self):
        data = request.get_json()

        scanFolders(SOURCE_XML_DIR_NAME, SOURCE_XML_DIR_NAME)
        scanFolders(SOURCE_IMAGE_DIR_NAME, SOURCE_IMAGE_DIR_NAME)

        # --------------------------------------------------------
        with open(TRANSLATIONS_JSON, "r") as translatorJSON:
            translation = json.loads(translatorJSON.read())
            for family in data['family_types']:
                testDestItem = addFileRecursively("Fixed Test Window_WMCC", targetFileName=family["type_name"])

                for parameter in family['parameters']:
                    translatedParameter = translation["parameters"][parameter]['ARCHICAD']["Name"]
                    testDestItem.parameters[translatedParameter] = unitConvert(
                        parameter,
                        family['parameters'][parameter],
                        translation
                    )

        # --------------------------------------------------------
        startConversion()

        return {"result": data}


api.add_resource(ArchicadEngine, '/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
