import os, json, shutil
import pprint

FOLDER = "test_BigBang"

fileList = os.listdir(FOLDER + "_suites")
CONVERT_ONLY = os.environ[
    'CONVERT_ONLY'] if "CONVERT_ONLY" in os.environ else ""  # Delimiter: ; without space, filenames without ext

for fileName in fileList:
    split = CONVERT_ONLY.split(";")
    if CONVERT_ONLY != "" and fileName[:-5] not in split:
        continue
    if not fileName.startswith('_') and os.path.splitext(fileName)[1] == '.json':
        print(fileName)
        _targetName = f"__{fileName}"
        if not os.path.exists(os.path.join(f"{FOLDER}_suites", _targetName)):
            shutil.copyfile(os.path.join(f"{FOLDER}_suites", fileName), os.path.join(f"{FOLDER}_suites", _targetName))

        with open(os.path.join(f"{FOLDER}_suites", _targetName), "r") as sourceFile:
            sourceDir = json.load(sourceFile)

        pprint.pprint(sourceDir)

        targetDict = {**sourceDir,
            'request': {**sourceDir['request'],
                'productData': {
                    'productName': sourceDir['request']['ProductName'],
                    'materialData': [
                        *sourceDir['request']['Template']['Materials']
                    ],
                    'variationsData': [{'variationName': vD['VariationName'],
                                        'parameters': [{**p,
                                                        'name': p['Name'],
                                                        'value': p['Value']} for p in vD['Parameters']]} for vD in sourceDir['request']['VariationsData']]
                },
                'archicadTemplate': {
                    **sourceDir['request']['Template']['ArchicadTemplate'],
                    'hasMacroSet': True if 'macrosetName' in sourceDir['result'] else False,
                },
                'authToken': "",
                'host': "127.0.0.1:4443",
                'archicadCallbackForObject': "127.0.0.1:4443/6/",
                'archicadCallbackForMacroset': "127.0.0.1:4443/61/",
                'template': ""
            }
        }

        del targetDict['request']['ProductName']
        del targetDict['request']['Template']
        del targetDict['request']['Webhook']
        del targetDict['request']['VariationsData']

        for vD in targetDict['request']['productData']['variationsData']:
            for p in vD['parameters']:
                if p['Group'] == 1:
                    p['group'] = 'dimensional'
                # if p['Group'] == 2:
                #     p['group'] = 'material'
                if p['Group'] == 3:
                    p['group'] = 'data'
                # if p['Group'] == 4:
                #     p['group'] = 'materialAppearance'
                del p['Group']
                del p['Name']
                del p['Value']

        with open( os.path.join(f"{FOLDER}_suites", fileName), "w") as targetFile:
            json.dump(targetDict, targetFile, indent=4)

            # data = {
            #     **data,
            #     "productName": data["productData"]["productName"],
            #     "template":  {
            #                     # **data["productData"]["template"],
            #                   "materials": data["productData"]["materialData"],
            #                   "ARCHICAD_template": data["archicadTemplate"],
            #                   },
            #     "variationsData": [{**vD,
            #                         "parameters": [{**p,
            #                                         "name": p["name"],
            #                                         "value": p["value"],} for p in vD["parameters"] if p["group"] == "dimensional"],
            #                         "materialParameters": [{**p,
            #                                         "name": p["name"],
            #                                         "value": p["value"],} for p in vD["parameters"] if p["group"] == "material" or p["group"] == "materialAppearance"],
            #                         "dataParameters": [{**p,
            #                                         "name": p["name"],
            #                                         "value": p["value"],} for p in vD["parameters"] if p["group"] == "data"],
            #                         } for vD in data["productData"]["variationsData"]],
            # }

            print("\n\n")
            pprint.pprint(targetDict)
