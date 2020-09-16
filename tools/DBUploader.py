import pymongo

import os, ssl, http.client, json, tempfile, base64, shutil, sys
import pprint
from subprocess import Popen, PIPE, DEVNULL

import googleapiclient.errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

CONNECTION_STRING = "mongodb+srv://template_writer:t0LMjZrGIB71ao5o@archos-ezw4q.azure.mongodb.net/test?authSource=admin&replicaSet=Archos-shard-0&readPreference=primary&appname=MongoDB%20Compass&ssl=true"
SERVER_URL = "wmcc.ad.bimobject.com"
CLEANUP = True
GOOGLE_SPREADSHEET_ID = "1uwGtx7b2LKGpjUWmS1csyTf-O19rZpVtvJvHZCz7HmI"

_SRC = r"..\src"
APP_CONFIG = os.path.join(_SRC, r"appconfig.json")
with open(APP_CONFIG, "r") as ac:
    APP_JSON = json.load(ac)
    CONTENT_DIR_NAME = APP_JSON["CONTENT_DIR_NAME"]
    ARCHICAD_LOCATION = os.path.join(_SRC, "archicad", "LP_XMLConverter_18")

COL_OBJECT_NAME = 4
COL_COMPILE_OK  = 1


# gs = None


# ------------------- Google Spreadsheet API connectivity --------------------------------------------------------------


# class NoGoogleCredentialsException(Exception):
#     pass


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

        flow = InstalledAppFlow.from_client_config(client_config, GoogleSpreadsheetConnector.GOOGLE_SPREADSHEET_SCOPES)
        self.googleCreds = flow.run_local_server()

        service = build('sheets', 'v4', credentials=self.googleCreds)

        sheet = service.spreadsheets()

        sheetName = sheet.get(spreadsheetId=inSpreadsheetID,
                              includeGridData=True).execute()['sheets'][1]['properties']['title']

        result = sheet.values().get(spreadsheetId=inSpreadsheetID,
                                    range=sheetName).execute()

        self.values = result.get('values', [])

        if not self.values:
            print('No data found.')


def uploadSingleRecord(inObjectData):
    global devPosts, prodPosts

    res = prodPosts.update_one({"name": inObjectData["name"]}, {"$set": {"ARCHICAD_template": inObjectData["ARCHICAD_template"]}})
    # print(res.__repr__() )


def uploadRecords(inObjectNameS):
    global gs, devPosts, prodPosts
    client = pymongo.MongoClient(CONNECTION_STRING)

    devDB = client['falcon-dev']
    devPosts = devDB['templates']

    prodDB = client['archos']
    prodPosts = prodDB['templates']

    gs = GoogleSpreadsheetConnector(GOOGLE_SPREADSHEET_ID)

    gsDict = {row[4] for row in gs.values if len(row) > 4 and row[1] == 'OK' and row[2] == 'OK'}

    if inObjectNameS:
        for objName in inObjectNameS:
            if objName in gsDict:
                objectData = devPosts.find_one({"name": objName})
                print(objectData["name"])
                uploadSingleRecord(objectData)
            else:
                print(f"Object is not marked to be uploaded: {objName}")
    else:
        _i = 1
        for objectData in  devPosts.find({"ARCHICAD_template": {"$exists": True}}):
            if objectData["name"] in gsDict:
                print(f"{_i}: {objectData['name']}")
                uploadSingleRecord(objectData)
                _i += 1
            else:
                print(f"Object is not marked to be uploaded: {objectData['name']}")


if __name__ == "__main__":
    uploadRecords(sys.argv[1:])