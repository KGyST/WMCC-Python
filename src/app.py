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
    NEW_BRAND_NAME,
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

            # ------ materials ------
            availableMaterials = []
            for material in data['materials']:
                availableMaterials += [ material["material_name"] ]
                materialMacro = addFileRecursively("RAL9003-White", targetFileName=material["material_name"] + "_" + NEW_BRAND_NAME)

                for parameter in material['parameters']:
                    translatedParameter = translation["parameters"][parameter]['ARCHICAD']["Name"]
                    materialMacro.parameters[translatedParameter] = unitConvert(
                        parameter,
                        material['parameters'][parameter],
                        translation
                    )
                materialMacro.parameters["sSurfaceName"] = material["material_name"] + "_" + NEW_BRAND_NAME

            # ------ placeables ------
            for family in data['family_types']:
                destItem = addFileRecursively("Fixed Test Window_WMCC", targetFileName=family["type_name"])

                for parameter in family['parameters']:
                    translatedParameter = translation["parameters"][parameter]['ARCHICAD']["Name"]
                    destItem.parameters[translatedParameter] = unitConvert(
                        parameter,
                        family['parameters'][parameter],
                        translation
                    )
                    # For now:
                    destItem.parameters["sMaterialValS"] = availableMaterials


        # --------------------------------------------------------
        startConversion()

        return {"result": data}


api.add_resource(ArchicadEngine, '/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
