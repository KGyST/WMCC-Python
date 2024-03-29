import re

import googleapiclient.errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

import pymongo

import sys
import pprint
from bson.objectid import ObjectId

import argparse

COL_ID          = 0
COL_REVIT_NAME  = 1
COL_AC_NAME     = 2
COL_CATEGORY    = 3
COL_MAIN_VER    = 4
COL_FIRST_DATA  = 5

CONNECTION_STRING = "mongodb+srv://template_writer:t0LMjZrGIB71ao5o@archos-ezw4q.azure.mongodb.net/test?authSource=admin&replicaSet=Archos-shard-0&readPreference=primary&appname=MongoDB%20Compass&ssl=true"
DB_NAME = 'falcon-dev'
TABLE_NAME = 'templates'

class NoGoogleCredentialsException(Exception):
    pass


class GoogleSpreadsheetConnector(object):
    GOOGLE_SPREADSHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    def __init__(self, inSpreadsheetID, inSheetName=""):
        self.__index = 0

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

        except (NoGoogleCredentialsException, WindowsError, FileNotFoundError):
            flow = InstalledAppFlow.from_client_config(client_config,
                                                       GoogleSpreadsheetConnector.GOOGLE_SPREADSHEET_SCOPES)
            self.googleCreds = flow.run_local_server()

            with open('token.pickle', 'wb') as token:
                pickle.dump(self.googleCreds, token)

        service = build('sheets', 'v4', credentials=self.googleCreds)

        sheet = service.spreadsheets()

        sheetName = sheet.get(spreadsheetId=inSpreadsheetID,
                              includeGridData=True).execute()['sheets'][0]['properties']['title']

        if inSheetName:
            _sheets = [s['properties']['title'] for s in sheet.get(spreadsheetId=inSpreadsheetID,
                                  includeGridData=True).execute()['sheets']]
            if inSheetName in _sheets:
                sheetName = inSheetName
            else:
                print(f"ERROR: In this sheet there is no {inSheetName} tab")
                raise Exception

        print(f"{sheetName} tab used")

        result = sheet.values().get(spreadsheetId=inSpreadsheetID,
                                    range=sheetName).execute()
        self.values = result.get('values', [])

        if not self.values:
            print('No data found.')

        self.headers = self.values[0][COL_FIRST_DATA:]

    def __iter__(self):
        return self

    def __next__(self):
        if self.__index >= len(self.values) - 1:
            raise StopIteration
        else:
            self.__index += 1
            return self.values[self.__index]


class ArgParse(argparse.ArgumentParser):
    # Overriding exit method that stops whole program in case of bad parametrization
    def exit(self, *_):
        try:
            pass
        except TypeError:
            pass


def configureObjectsDB(inParams):
    SSIDRegex = "/spreadsheets/d/([a-zA-Z0-9-_]+)"
    findall = re.findall(SSIDRegex, inParams[0])
    if findall:
        SpreadsheetID = findall[0]
    else:
        SpreadsheetID = findall
    print(f"SpreadsheetID: {SpreadsheetID}")

    try:
        if inParams[1]:
            googleSpreadsheet = GoogleSpreadsheetConnector(SpreadsheetID, inParams[1])
        else:
            googleSpreadsheet = GoogleSpreadsheetConnector(SpreadsheetID)
    except googleapiclient.errors.HttpError:
        print(("HttpError: Spreadsheet ID (%s) seems to be invalid" % SSIDRegex))
        return

    objectsToProcess = set(inParams[2:]) if inParams[2:] else set()

    client = pymongo.MongoClient(CONNECTION_STRING)

    db = client[DB_NAME]
    posts = db[TABLE_NAME]

    ap = ArgParse(add_help=False)
    ap.add_argument("-i", "--integer", action='store_true')
    ap.add_argument("-n", "--number", action='store_true')
    ap.add_argument("-p", "--parameter", action='store_true')
    ap.add_argument("-u", "--unit")
    ap.add_argument("-t", "--type")
    ap.add_argument("-1", "--firstposition")
    ap.add_argument("-2", "--secondposition")

    for row in googleSpreadsheet:
        if objectsToProcess\
        and (row[COL_ID] in objectsToProcess
        or row[COL_REVIT_NAME] in objectsToProcess):
            if posts.count({"name": row[COL_REVIT_NAME]}) == 1:
                objectData = posts.find_one({"name": row[COL_REVIT_NAME]})
            elif row[COL_ID]:
                objectData = posts.find_one({"_id": ObjectId(row[COL_ID])})

                if not objectData:
                    print(f"ERROR: {row[COL_REVIT_NAME]} not found in Database")
                    continue
            else:
                if row[COL_REVIT_NAME]:
                    print(f"ERROR: multiple objects AND no id or id not found in dev DB: {row[COL_REVIT_NAME]}")
                    continue
                else:
                    print(f"ERROR: No Revit name")
                    continue

            print(f"{objectData['name']}")
            _parmameters = []
            _translations = {}

            for firstRow, cell in zip(googleSpreadsheet.headers, row[COL_FIRST_DATA:]):
                splitPars = firstRow.split(" ")
                parName = splitPars[0]

                try:
                    parsedArgs = ap.parse_known_args(splitPars)[0]
                except TypeError as e:
                    print(f"ERROR: Bad parametrization: {firstRow}")
                    return

                if cell.replace(" ", ""):
                    if parsedArgs.parameter:
                        # Fixed parameter
                        if parsedArgs.integer:
                            _v = int(cell)
                        elif parsedArgs.number:
                            _v = float(cell)
                        else:
                            _v = cell
                        _par = {   "name":  parName,
                                   "value": _v, }
                        if parsedArgs.type:
                            _par["Type"] = parsedArgs.type
                        if parsedArgs.firstposition:
                            _par["FirstPosition"] = parsedArgs.firstposition
                        if parsedArgs.secondposition:
                            _par["SecondPosition"] = parsedArgs.secondposition
                        _parmameters.append(_par)
                    else:
                        # Translation
                        _trans = {"ARCHICAD": {"Name": parName, }}
                        if parsedArgs.unit:
                            _trans["ARCHICAD"][ "Measurement"] = parsedArgs.unit
                        if parsedArgs.firstposition:
                            _trans["ARCHICAD"]["FirstPosition"] = int(parsedArgs.firstposition)
                        if parsedArgs.secondposition:
                            _trans["ARCHICAD"]["SecondPosition"] = int(parsedArgs.secondposition)
                        if cell not in _translations:
                            _translations[cell] = _trans
                        else:
                            if not isinstance(_translations[cell]["ARCHICAD"], list):
                                _translations[cell]["ARCHICAD"]  = [_translations[cell]["ARCHICAD"]]
                            _translations[cell]["ARCHICAD"].append(_trans["ARCHICAD"])

            ARCHICAD_template= {
                "category": row[COL_CATEGORY],
                "main_macroset_version": row[COL_MAIN_VER],
                "source_file": row[COL_AC_NAME], }

            if _parmameters:
                ARCHICAD_template["parameters"] = _parmameters
            if _translations:
                ARCHICAD_template["translations"] = _translations

            pprint.pprint(ARCHICAD_template)

            #FIXME error checking: If there is an unit for param in DB but not defined in Google Docs field

            res = db[TABLE_NAME].update_one({"_id": ObjectId(objectData["_id"])},
                                            {"$set": {"ARCHICAD_template": ARCHICAD_template}})


if __name__ == "__main__":
    configureObjectsDB(sys.argv[1:])