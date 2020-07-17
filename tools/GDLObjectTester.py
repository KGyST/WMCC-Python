import pymongo

import os, ssl, http.client, json, tempfile, base64, shutil, sys
import pprint
from subprocess import Popen, PIPE, DEVNULL

CONNECTION_STRING = "mongodb+srv://template_writer:t0LMjZrGIB71ao5o@archos-ezw4q.azure.mongodb.net/test?authSource=admin&replicaSet=Archos-shard-0&readPreference=primary&appname=MongoDB%20Compass&ssl=true"
SERVER_URL = "wmcc.ad.bimobject.com"
CLEANUP = True

_SRC        = r"..\src"
APP_CONFIG  = os.path.join(_SRC, r"appconfig.json")
with open(APP_CONFIG, "r") as ac:
    APP_JSON = json.load(ac)
    CONTENT_DIR_NAME            = APP_JSON["CONTENT_DIR_NAME"]
    ARCHICAD_LOCATION           = os.path.join(_SRC, "archicad", "LP_XMLConverter_18")

def getSingleObject(inObjectData):
    s = ssl.SSLContext()
    conn = http.client.HTTPSConnection(SERVER_URL, context=s)
    headers = {"Content-Type": "application/json"}
    endp = "/"
    req = {
        "productName": inObjectData["name"],
        "template": {
            "materials": inObjectData["materials"],
            "ARCHICAD_template": inObjectData["ARCHICAD_template"]
        },
        "variationsData": [
            {
                "variationName": inObjectData["name"] + "_teszt",
                "parameters": [{
                    "name": p["name"],
                    "selectedUnit": "mm",
                    "category": None,
                    "value": min(max(p["min_value"], 1000), p["max_value"]),
                } for p in inObjectData["parameters"]],
                "materialParameters": [{"name": i,
                                        "value": inObjectData["materials"][0]["name"],
                                        "category": None} for i in inObjectData["material_parameters"]],
                "dataParameters": [],
            }
        ],
    }
#
    conn.request("POST", endp, json.dumps(req), headers)
    response = conn.getresponse()

    responseJSON = json.loads(response.read())

    # pprint.pprint(responseJSON)

    tasks = []
    tempDir = tempfile.mkdtemp()

    if "base64_encoded_object" in responseJSON \
    and 'object_name' in responseJSON:
        target_folder = os.path.join("test_objects", responseJSON['object_name'])
        os.mkdir(target_folder)

        placeableTempGSMDir = os.path.join(target_folder, "placeable")
        os.mkdir(placeableTempGSMDir)
        tasks += [
            (f'extractcontainer "{os.path.join(tempDir, responseJSON["object_name"])}" "{placeableTempGSMDir}"'), ]

        with open(os.path.join(tempDir, responseJSON['object_name']), 'wb') as objectFile:
            decode = base64.urlsafe_b64decode(responseJSON['base64_encoded_object'])
            objectFile.write(decode)

    if  "base64_encoded_macroset" in responseJSON \
    and 'macroset_name' in responseJSON:
        target_folder = os.path.join("test_macrosets", responseJSON['macroset_name'])

        if not os.path.exists(target_folder):
            os.mkdir(target_folder)

            tasks += [
                (f'extractcontainer "{os.path.join(tempDir, responseJSON["macroset_name"])}" "{target_folder}"'), ]

            with open(os.path.join(tempDir, responseJSON['macroset_name']), 'wb') as objectFile:
                decode = base64.urlsafe_b64decode(responseJSON['base64_encoded_macroset'])
                objectFile.write(decode)

    if "error_message" in responseJSON:
        pprint.pprint(responseJSON)

    for _dir in tasks:
        with Popen(f'"{os.path.join(ARCHICAD_LOCATION, "LP_XMLConverter.exe")}" {_dir}',
                   stdout=PIPE, stderr=PIPE, stdin=DEVNULL) as proc:
            _out, _err = proc.communicate()

    if CLEANUP:
        shutil.rmtree(tempDir)


def getObjects(inObjectNameS):
    client = pymongo.MongoClient(CONNECTION_STRING)

    db = client['falcon-dev']
    posts = db['templates']

    try:
        if os.path.exists("test_objects"):
            shutil.rmtree("test_objects")
        os.mkdir("test_objects")

        if os.path.exists("test_macrosets"):
            shutil.rmtree("test_macrosets")
        os.mkdir("test_macrosets")

        if inObjectNameS:
            for objName in inObjectNameS:
                objectData = posts.find_one({"name": objName})
                # pprint.pprint(objectData)
                print(objectData["name"])
                getSingleObject(objectData)
        else:
            _i = 1
            for objectData in  posts.find({"ARCHICAD_template": {"$exists": True}}):
                print(f"{_i}: {objectData['name']}")
                getSingleObject(objectData)
                _i += 1
    except PermissionError:
        print("PermissionError")
    except OSError:
        print("OSError")

if __name__ == "__main__":
    getObjects(sys.argv[1:])