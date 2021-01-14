import pymongo

import os, ssl, http.client, json, tempfile, shutil, sys
import pprint
from subprocess import Popen, PIPE, DEVNULL
from bson.objectid import ObjectId
from urllib.parse import urlparse


from http.server import BaseHTTPRequestHandler, HTTPServer
LOCALHOST_SERVER_PORT = 4443
LOCALHOST_URL = os.getenv("LOCALHOST_URL")

CONNECTION_STRING = "mongodb+srv://template_writer:t0LMjZrGIB71ao5o@archos-ezw4q.azure.mongodb.net/test?authSource=admin&replicaSet=Archos-shard-0&readPreference=primary&appname=MongoDB%20Compass&ssl=true"
MONGO_TABLE = 'falcon-dev'

SERVER_URL = "wmcc.ad.bimobject.com"
CLEANUP = True

_SRC        = r".."
APP_CONFIG  = os.path.join(_SRC, r"appconfig.json")
with open(APP_CONFIG, "r") as ac:
    APP_JSON = json.load(ac)
    CONTENT_DIR_NAME            = APP_JSON["CONTENT_DIR_NAME"]
    ARCHICAD_LOCATION           = os.path.join(_SRC, "src", "archicad", "LP_XMLConverter_18")
    STORAGE_NAME                = APP_JSON["STORAGE_NAME"]
    RESULT_CONTAINER_NAME       = APP_JSON["RESULT_CONTAINER_NAME"]


class myHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global responseJSON, hasMacroSet

        content_len = int(self.headers.get('Content-Length'))
        _response = json.loads(self.rfile.read(content_len).decode("utf-8"))
        if "Name" in _response:
            if "/6/" in self.path:
                # "/6/" for placeable objects, "/61/" for macrosets
                responseJSON.update({   "placeableName": _response["Name"],
                                        "placeableURL":  _response["DownloadUrl"]})
            else:
                responseJSON.update({   "macrosetName":  _response["Name"],
                                        "macrosetURL":   _response["DownloadUrl"]})
        else:
            #For errors
            responseJSON.update(_response)

        self.wfile.write("HTTP/1.1 200 Ok".encode("utf-8"))

        if not hasMacroSet or "macrosetName" in responseJSON:
            server.server_close()

server = HTTPServer(('', LOCALHOST_SERVER_PORT), myHandler)
server.socket = ssl.wrap_socket (server.socket, certfile='./temp_server.pem', server_side=True)


def getSingleObject(inObjectData):
    global responseJSON, server, hasMacroSet

    s = ssl.SSLContext()
    # conn = http.client.HTTPSConnection(SERVER_URL, context=s)
    conn = http.client.HTTPConnection(SERVER_URL)
    headers = {"Content-Type": "application/json"}
    endp = "/"
    req = {
        "productData": {
            "productName": inObjectData["name"],
            "template": "",
            "materialData": [{**m,
                           "Name": m['name']} for m in inObjectData["materials"]],
            "variationsData": [
                {
                    "variationName": inObjectData["name"] + "_teszt",
                    "parameters": [{
                        "name": p["name"],
                        "selectedUnit": "mm",
                        "category": None,
                        "value": min(max(p["min_value"], 999), p["max_value"]),
                        "storageType": 1,
                        "group": 1,
                        "minValue": p["min_value"],
                        "maxValue": p["max_value"],
                    } for p in inObjectData["parameters"] if p["group"] == "dimensional"] + \
                                  [{
                                      "name": p["name"],
                                      "selectedUnit": None,
                                      "category": None,
                                      "value": "Teszt_%s" % p["name"],
                                      "storageType": None,
                                      "group": 2,
                                      "minValue": None,
                                      "maxValue": None,
                                  } for p in inObjectData["parameters"] if p["group"] == "material"],
                    # "materialParameters": [{"name": i,
                    #                         "value": inObjectData["materials"][0]["name"],
                    #                         "category": None} for i in inObjectData["material_parameters"]],
                    "dataParameters": [],
                }
            ],
        },
        "authToken": "",
        "archicadTemplate": inObjectData["ARCHICAD_template"],
        "host": f"{LOCALHOST_URL}:{str(LOCALHOST_SERVER_PORT)}",
        "archicadCallbackForObject":   f"{LOCALHOST_URL}:{str(LOCALHOST_SERVER_PORT)}/6",
        "archicadCallbackForMacroset": f"{LOCALHOST_URL}:{str(LOCALHOST_SERVER_PORT)}/61",
    }
#
    conn.request("POST", endp, json.dumps(req), headers)
    response = conn.getresponse()

    responseJSON = json.loads(response.read())
    hasMacroSet = inObjectData["ARCHICAD_template"]["hasMacroSet"]

    try:
        server.serve_forever()
    except IOError:
        conn.close()
        server.shutdown()

    tasks = []
    tempDir = tempfile.mkdtemp()

    if "placeableName" in responseJSON:
        target_folder = os.path.join("test_objects", responseJSON['placeableName'])
        os.mkdir(target_folder)

        placeableTempGSMDir = os.path.join(target_folder, "placeable")
        os.mkdir(placeableTempGSMDir)
        tasks += [
            (f'extractcontainer "{os.path.join(tempDir, responseJSON["placeableName"])}" "{placeableTempGSMDir}"'), ]

        endp = urlparse(responseJSON["placeableURL"])

        conn = http.client.HTTPSConnection(endp.hostname, context=s)
        conn.request("GET", endp.path)
        response = conn.getresponse()
        with open(os.path.join(tempDir, responseJSON["placeableName"]), "wb") as tF:
            tF.write(response.read())

    if "macrosetName" in responseJSON:
        target_folder = os.path.join("test_macrosets", responseJSON['macrosetName'])

        if not os.path.exists(target_folder):
            os.mkdir(target_folder)

            tasks += [
                (f'extractcontainer "{os.path.join(tempDir, responseJSON["macrosetName"])}" "{target_folder}"'), ]

            endp = urlparse(responseJSON["macrosetURL"])

            conn = http.client.HTTPSConnection(endp.hostname, context=s)
            conn.request("GET", endp.path)
            response = conn.getresponse()
            with open(os.path.join(tempDir, responseJSON["macrosetName"]), "wb") as tF:
                tF.write(response.read())

    if "error_message" in responseJSON:
        pprint.pprint(responseJSON)

    for _dir in tasks:
        with Popen(f'"{os.path.join(ARCHICAD_LOCATION, "LP_XMLConverter.exe")}" {_dir}',
                   stdout=PIPE, stderr=PIPE, stdin=DEVNULL) as proc:
            _out, _err = proc.communicate()

    if CLEANUP:
        shutil.rmtree(tempDir)
    else:
        print(f"tempDir: {tempDir}")


def checkMaterialString(objectData):
    # for mat in objectData["materials"]:
    #     for char in '<>\/:"?':
    #         if char in mat['name']:
    #             print(f"ERROR: object not downloaded: material name cannot be converted to a proper filename: {mat['name']}")
    #             return
    getSingleObject(objectData)



def getObjects(inObjectNameS):
    client = pymongo.MongoClient(CONNECTION_STRING)

    db = client[MONGO_TABLE]
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
                if not objectData:
                    objectData = posts.find_one({"_id": ObjectId(objName)})
                if not objectData:
                    print(f'MISSING object from DB: {objName}')
                    continue
                # pprint.pprint(objectData)
                print(objectData["name"])
                checkMaterialString(objectData)
        else:
            _i = 1
            for objectData in  posts.find({"ARCHICAD_template": {"$exists": True}}):
                print(f"{_i}: {objectData['name']}")
                checkMaterialString(objectData)
                _i += 1
    except PermissionError as e:
        print(f"PermissionError {e}")
    except OSError as e:
        print(f"OSError {e.strerror}")

if __name__ == "__main__":
    getObjects(sys.argv[1:])