import pymongo

import os, json, sys

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import pickle

from bson.objectid import ObjectId

from pprint import pprint

COL_NUMBER              = 0
COL_DEVELOPED_OK        = 1
COL_TESTED_OK           = 2
COL_AC_CATEGORY         = 3
COL_REVIT_OBJECT_NAME   = 4
COL_OBJECT_ID_DEV       = 5
COL_OBJECT_ID_PROD      = 6
COL_DEVELOPER           = 7
COL_AC_OBJECT_NAME      = 8

CONNECTION_STRING = "mongodb+srv://template_writer:t0LMjZrGIB71ao5o@archos-ezw4q.azure.mongodb.net/test?authSource=admin&replicaSet=Archos-shard-0&readPreference=primary&appname=MongoDB%20Compass&ssl=true"
TEMPLATE_TABLE = 'templates'
DB_DEV = 'falcon-dev'
# DB_STAG = 'falcon-stag'
DB_PROD = 'archos'

PROD_STRING = "prod"

SERVER_URL = "wmcc.ad.bimobject.com"
CLEANUP = True
GOOGLE_SPREADSHEET_ID = "1uwGtx7b2LKGpjUWmS1csyTf-O19rZpVtvJvHZCz7HmI"

_SRC = r".."
APP_CONFIG = os.path.join(_SRC, r"appconfig.json")
with open(APP_CONFIG, "r") as ac:
    APP_JSON = json.load(ac)
    CONTENT_DIR_NAME = APP_JSON["CONTENT_DIR_NAME"]
    ARCHICAD_LOCATION = os.path.join(_SRC, "archicad", "LP_XMLConverter_18")

COL_OBJECT_NAME = 4
COL_COMPILE_OK  = 1

resultDir = {"Updated": 0,
             "Skipped": 0,
          "ERROR: More objects with the same name in Prod DB": set(),
          "ERROR: DB has no entry in Prod DB": set(),
          "ERROR: More objects with the same name in Dev DB": set(),
          "ERROR: DB has no entry in Dev DB": set(),
             }


# ------------------- Google Spreadsheet API connectivity --------------------------------------------------------------


class NoGoogleCredentialsException(Exception):
    pass


class GoogleSpreadsheetConnector(object):
    GOOGLE_SPREADSHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    def __init__(self, inSpreadsheetID):
        #FIXME renaming/filling out these
        client_config = {"installed": {
            "client_id": "224241213692-7gafn34d4heprhps1rod3clt1b8j07j6.apps.googleusercontent.com",
            "project_id": "quickstart-1558854893881",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "PHWQx7k6ldF73rDkqJE2Cedl",
            "redirect_uris": {
                "urn:ietf:wg:oauth:2.0:oob",
                "http://localhost"}
        }}

        try:
            with open('token.pickle', 'rb') as token:
                self.googleCreds = pickle.load(token)

            if not self.googleCreds.valid:
                if self.googleCreds.expired and self.googleCreds.refresh_token:
                    self.googleCreds.refresh(Request())
                else:
                    raise NoGoogleCredentialsException
            else:
                raise NoGoogleCredentialsException

        except (NoGoogleCredentialsException, WindowsError):
            flow = InstalledAppFlow.from_client_config(client_config,
                                                       GoogleSpreadsheetConnector.GOOGLE_SPREADSHEET_SCOPES)
            self.googleCreds = flow.run_local_server()

            with open('token.pickle', 'wb') as token:
                pickle.dump(self.googleCreds, token)

        service = build('sheets', 'v4', credentials=self.googleCreds)

        sheet = service.spreadsheets()

        sheetName = sheet.get(spreadsheetId=inSpreadsheetID,
                              includeGridData=True).execute()['sheets'][1]['properties']['title']

        result = sheet.values().get(spreadsheetId=inSpreadsheetID,
                                    range=sheetName).execute()

        self.values = result.get('values', [])

        if not self.values:
            print('No data found.')


def uploadSingleRecord(inObjectData, inTargetDataBase, inPodID = None):
    global devPosts, resultDir

    if inPodID:
        #FIXME to search for name and category etc or exit if more than one instance
        res = inTargetDataBase.update_one({"_id": ObjectId(inPodID)}, {"$set": {"ARCHICAD_template": inObjectData["ARCHICAD_template"]}})
        # print(res.__repr__() )
        print(f"Updated: {inObjectData['name']} in {inTargetDataBase.database.name}")
        resultDir["Updated"] += 1
    else:
        found_count = inTargetDataBase.find({"name": inObjectData["name"]}).count()
        if  found_count == 0:
            print(f"ERROR: {inTargetDataBase.database.name} has no entry {inObjectData['name']}")
            resultDir["ERROR: DB has no entry in Prod DB"].add(inObjectData['name'])
        elif found_count == 1:
            res = inTargetDataBase.update_one({"name": inObjectData["name"]}, {"$set": {"ARCHICAD_template": inObjectData["ARCHICAD_template"]}})
            print(f"Updated: {inObjectData['name']} in {inTargetDataBase.database.name}")
            resultDir["Updated"] += 1
        else:
            print(f"ERROR: More objects with the name {inObjectData['name']} in {inTargetDataBase.database.name}, you have to update object's id (in target DB) to column F")
            resultDir["ERROR: More objects with the same name in Prod DB"].add(inObjectData['name'])


def uploadRecords(inObjectNameS):
    # if inObjectNameS[0] == PROD_STRING:
    #     isProduction = True
    #     inObjectNameS = inObjectNameS[1:]
    # else:
    #     isProduction = False

    global gs, devPosts, prodPosts, resultDir
    client = pymongo.MongoClient(CONNECTION_STRING)

    devPosts = client[DB_DEV][TEMPLATE_TABLE]

    # stagingTable = client[DB_STAG][TEMPLATE_TABLE]

    prodTable= client[DB_PROD][TEMPLATE_TABLE]

    gs = GoogleSpreadsheetConnector(GOOGLE_SPREADSHEET_ID)

    ready_to_update_dict = {row[COL_REVIT_OBJECT_NAME]: {COL_OBJECT_ID_DEV: row[COL_OBJECT_ID_DEV],
                                                         COL_OBJECT_ID_PROD: row[COL_OBJECT_ID_PROD]}
                                                            for row in gs.values if len(row) > 4
                                                                and row[COL_DEVELOPED_OK] == 'OK'
                                                                and row[COL_TESTED_OK] == 'OK'}
    ready_to_update_dict.update({row[COL_OBJECT_ID_DEV]: {COL_OBJECT_ID_DEV: row[COL_OBJECT_ID_DEV],
                                                         COL_OBJECT_ID_PROD: row[COL_OBJECT_ID_PROD]}
                                                            for row in gs.values if len(row) > 4
                                                                and row[COL_DEVELOPED_OK] == 'OK'
                                                                and row[COL_TESTED_OK] == 'OK'
                                                                and row[COL_OBJECT_ID_DEV]})

    #Such a mess
    if inObjectNameS:
        for objName in inObjectNameS:
            if objName in ready_to_update_dict:
                if ready_to_update_dict[objName][COL_OBJECT_ID_DEV]:
                    objectData = devPosts.find_one({"_id": ObjectId(ready_to_update_dict[objName][COL_OBJECT_ID_DEV])})
                    uploadSingleRecord(objectData, prodTable, ready_to_update_dict[objName][COL_OBJECT_ID_PROD])
                else:
                    found_count = devPosts.find({"name": objName}).count()
                    if found_count == 0:
                        print(f"ERROR: Dev DB has no entry {objName}")
                        resultDir["ERROR: More objects with the same name in Dev DB"].add(objName)
                    elif found_count == 1:
                        objectData = devPosts.find_one({"name": objName})
                        uploadSingleRecord(objectData, prodTable)
                        # print(objectData["name"])
                        # uploadSingleRecord(objectData, stagingTable)
                        # if isProduction:
                    else:
                        print(f"ERROR: Dev DB has more entries with name {objName}, You have to fill _id value in column F")
                        resultDir["ERROR: More objects with the same name in Dev DB"].add(objName)
            else:
                print(f"Object is not marked to be uploaded: {objName}")
                resultDir["Skipped"] += 1
    else:
        # Update all
        # _i = 1
        for objectData in  devPosts.find({"ARCHICAD_template": {"$exists": True}}):
            if objectData["name"] in ready_to_update_dict:
                # print(f"{_i}: {objectData['name']}")
                # uploadSingleRecord(objectData, stagingTable)
                # if isProduction:
                uploadSingleRecord(objectData, prodTable, ready_to_update_dict[objectData["name"]][COL_OBJECT_ID_PROD])
                # _i += 1
            else:
                print(f"Object is not marked to be uploaded: {objectData['name']}")
                resultDir["Skipped"] += 1


if __name__ == "__main__":
    uploadRecords(sys.argv[1:])
    print("* * * RESULTS * * *")
    pprint(resultDir)