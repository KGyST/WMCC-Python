import re, sys

import googleapiclient.errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pickle

COL_ID          = 0
COL_AC_NAME     = 1
COL_CATEGORY    = 2
COL_MAIN_VER    = 3
COL_FIRST_DATA  = 4

import pymongo

import sys
import pprint
from bson.objectid import ObjectId

import argparse


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
            else:
                raise NoGoogleCredentialsException

        except (NoGoogleCredentialsException, WindowsError):
            flow = InstalledAppFlow.from_client_config(client_config,
                                                       GoogleSpreadsheetConnector.GOOGLE_SPREADSHEET_SCOPES, inSheetName=inSheetName)
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

    client = pymongo.MongoClient(CONNECTION_STRING)

    db = client[DB_NAME]
    posts = db[TABLE_NAME]

    for row in googleSpreadsheet:
        objectData = posts.find_one({"_id": ObjectId(row[COL_ID])})

        print(f"{objectData['name']}")
        _parmameters = []
        _translations = {}

        for firstRow, cell in zip(googleSpreadsheet.headers, row[COL_FIRST_DATA:]):
            splitPars = firstRow.split(" ")
            parName = splitPars[0]
            ap = ArgParse(add_help=False)
            ap.add_argument("-i", "--integer", action='store_true')
            ap.add_argument("-n", "--number", action='store_true')
            ap.add_argument("-p", "--parameter", action='store_true')
            ap.add_argument("-u", "--unit")
            ap.add_argument("-t", "--type")
            ap.add_argument("-1", "--firstposition")
            ap.add_argument("-2", "--secondposition")

            parsedArgs = ap.parse_known_args(splitPars)[0]

            if cell.replace(" ", ""):
                if parsedArgs.parameter:
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
                    _trans = {"ARCHICAD": {"Name": parName, }}
                    if parsedArgs.unit:
                        _trans["ARCHICAD"][ "Measurement"] = parsedArgs.unit
                    if parsedArgs.firstposition:
                        _trans["ARCHICAD"]["FirstPosition"] = int(parsedArgs.firstposition)
                    if parsedArgs.secondposition:
                        _trans["ARCHICAD"]["SecondPosition"] = int(parsedArgs.secondposition)
                    _translations[cell] = _trans



        ARCHICAD_template= {
            "category": row[COL_CATEGORY],
            "main_macroset_version": row[COL_MAIN_VER],
            "source_file": row[COL_AC_NAME],
            "parameters":   _parmameters,
            "translations": _translations}

        pprint.pprint(ARCHICAD_template)

        res = db[TABLE_NAME].update_one({"_id": ObjectId(row[COL_ID])},
                                        {"$set": {"ARCHICAD_template": ARCHICAD_template}})


if __name__ == "__main__":
    configureObjectsDB(sys.argv[1:])