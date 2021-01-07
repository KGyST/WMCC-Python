#FIXME keep track and print out a string of unsuccessful tests for pasting them into TEST_ONLY environment variable

import unittest
import os
import json
import http.client
import ssl
import shutil
import tempfile
from subprocess import Popen, PIPE, DEVNULL
import re

from http.server import BaseHTTPRequestHandler, HTTPServer
from azure.storage.blob import BlobServiceClient
from  urllib import request


FOLDER      = "test_BigBang"
SERVER_URL  = os.environ['SERVER_URL'] if "SERVER_URL" in os.environ else "localhost"
TEST_ONLY   = os.environ['TEST_ONLY']  if "TEST_ONLY"  in os.environ else ""            # Delimiter: ; without space, filenames without ext
print(f"Server URL: {SERVER_URL} \n")
RECEIVER_SERVER_PORT = 8080

_SRC        = r".."
APP_CONFIG  = os.path.join(_SRC, "..", r"appconfig.json")   #FIXME relative path not elegant here
with open(APP_CONFIG, "r") as ac:
    APP_JSON = json.load(ac)
    CONTENT_DIR_NAME            = APP_JSON["CONTENT_DIR_NAME"]
    ARCHICAD_LOCATION           = os.path.join(_SRC, "archicad", "LP_XMLConverter_18")

TEST_SEQUENCE_LIST = ['resetjobqueue', "extractparams", "error", "create_macroset"]


class myHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global responseJSON, isMacroset

        content_len = int(self.headers.get('Content-Length'))
        _response = json.loads(self.rfile.read(content_len).decode("utf-8"))
        if "Name" in _response:
            if not "macroset_" in _response["Name"]:
                responseJSON.update({   "placeableName": _response["Name"],
                                        "placeableURL":  _response["DownloadUrl"]})
            else:
                responseJSON.update({   "macrosetName":  _response["Name"],
                                        "macrosetURL":   _response["DownloadUrl"]})
        else:
            #For errors
            responseJSON.update(_response)

        self.wfile.write("HTTP/1.1 200 Ok".encode("utf-8"))

        server.server_close()


server = HTTPServer(('', RECEIVER_SERVER_PORT), myHandler)

container_name = "archicad-local"
connect_str = "DefaultEndpointsProtocol=https;AccountName=falconestorage;AccountKey=xUepXBEtdcKEp74pOfw0iqv6weQmA5YQPsITR7BzmFA4/j/UdFqoKC3Ja0bv4PbxO9HKvwjkZ1PQ3+jC56ezZA==;EndpointSuffix=core.windows.net"

blob_service_client = BlobServiceClient.from_connection_string(connect_str)
container_client = blob_service_client.get_container_client(container_name)

class FileName(str):
    """
    Class for sorting test cases represented by filenames
    """
    def __lt__(self, other):
        _bSelf = [1 if x in str(self).lower() else False for x in TEST_SEQUENCE_LIST]
        if any(_bSelf):
            _selfIdx = _bSelf.index(1)
            _bOther = [1 if x in str(other).lower() else False  for x in TEST_SEQUENCE_LIST]
            if any(_bOther):
                _otherIdx = _bOther.index(1)
                if _selfIdx != _otherIdx:
                    return _selfIdx < _otherIdx
                else:
                    return str(self).upper() < str(other).upper()
            else:
                return True
        elif any([x in str(other).lower() for x in TEST_SEQUENCE_LIST]):
                return False
        else:
            return str(self).upper() < str(other).upper()

    def __gt__(self, other):
        _bSelf = [1 if x in str(self).lower() else False for x in TEST_SEQUENCE_LIST]
        if any(_bSelf):
            _selfIdx = _bSelf.index(1)
            _bOther = [1 if x in str(other).lower() else False for x in TEST_SEQUENCE_LIST]
            if any(_bOther):
                _otherIdx = _bOther.index(1)
                if _selfIdx != _otherIdx:
                    return _selfIdx > _otherIdx
                else:
                    return str(self).upper() > str(other).upper()
            else:
                return False
        elif any([x in str(other).lower() for x in TEST_SEQUENCE_LIST]):
                return True
        else:
            return str(self).upper() > str(other).upper()


class TestSuite_BigBang(unittest.TestSuite):
    def __init__(self):
        try:
            shutil.rmtree(FOLDER + "_errors")
            os.mkdir(FOLDER + "_errors")
        except PermissionError:
            pass
        except OSError:
            pass

        self._tests = []
        self._fileList = sorted([FileName(f) for f in os.listdir(FOLDER + "_suites")])
        for fileName in self._fileList:
            split = TEST_ONLY.split(";")
            if TEST_ONLY != "" and fileName [:-5] not in split:
                continue
            if not fileName.startswith('_') and os.path.splitext(fileName)[1] == '.json':
                try:
                    testData = json.load(open(os.path.join(FOLDER + "_suites", fileName), "r"))

                    test_case = TestCase_BigBang(testData, FOLDER, fileName)
                    test_case.maxDiff = None
                    self.addTest(test_case)
                except json.decoder.JSONDecodeError:
                    print(f"JSONDecodeError - Filename: {fileName}")

        super(TestSuite_BigBang, self).__init__(self._tests)

    def __contains__(self, inName):
        for test in self._tests:
            if test._testMethodName == inName:
                return True
        return False


class TestCase_BigBang(unittest.TestCase):
    def __init__(self, inTestData, inDir, inFileName):
        func = self.BigBangTestCaseFactory(inTestData, inDir, inFileName)
        setattr(TestCase_BigBang, func.__name__, func)
        super(TestCase_BigBang, self).__init__(func.__name__)

    @staticmethod
    def BigBangTestCaseFactory(inTestData, inDir, inFileName):
        def func(inObj):
            global responseJSON, server, isPlaceable
            isPlaceable = True

            outFileName = os.path.join(inDir + "_errors", inFileName)
            if "localhost" in SERVER_URL:
                conn = http.client.HTTPConnection(SERVER_URL)
            else:
                s = ssl.SSLContext()
                conn = http.client.HTTPSConnection(SERVER_URL, context=s)

            if "textures" in inTestData:
                for textureToUpload in inTestData["textures"]:
                    blob_client = blob_service_client.get_blob_client(container=container_name,
                                                                      blob=textureToUpload)
                    with open(os.path.join(inDir + "_suites", textureToUpload), "rb") as tF:
                        blob_client.upload_blob(tF, overwrite=True)

            headers = {"Content-Type": "application/json"}
            endp = inTestData["endpoint"]
            req = inTestData["request"]
            conn.request("POST", endp, json.dumps(req), headers)
            response = conn.getresponse()
            responseJSON = json.loads(response.read())

            if not responseJSON:
                try:
                    server.serve_forever()
                except IOError:
                    conn.close()
                    server.shutdown()
                    server = HTTPServer(('', RECEIVER_SERVER_PORT), myHandler)

                    if (not "hasMacroset" in inTestData) or inTestData["hasMacroset"]:
                        #By default test cases have macroset
                        try:
                            isPlaceable = False
                            server.serve_forever()
                        except IOError:
                            conn.close()
                            server.shutdown()
                            server = HTTPServer(('', RECEIVER_SERVER_PORT), myHandler)

            # FIXME actual day not tested
            # minor_version = datetime.date.today().strftime("%Y%m%d")
            # if "minor_version" in req:
            #     minor_version = req["minor_version"]

            if inTestData["endpoint"] in ("/", "/creatematerials"):
                #FIXME remove this selector, no other than these two

                tasks = []
                foldersToExtract = {}
                tempDir = tempfile.mkdtemp()
                if "placeableURL" in responseJSON:
                    placeableTempGSMDir = tempfile.mkdtemp()
                    placeableTempXMLDir = tempfile.mkdtemp()
                    placeableTempImgDir = tempfile.mkdtemp()

                    response = request.urlopen(responseJSON["placeableURL"])

                    with open(os.path.join(tempDir, responseJSON["placeableName"]), "wb") as tF:
                        tF.write(response.read())

                    tasks += [(f'extractcontainer "{os.path.join(tempDir, responseJSON["placeableName"])}" "{placeableTempGSMDir}"'),
                              (f'l2x -img "{placeableTempImgDir}" "{placeableTempGSMDir}" "{placeableTempXMLDir}"'), ]
                    foldersToExtract.update({"placeables": placeableTempXMLDir})
                    foldersToExtract.update({"placeables_images": placeableTempImgDir})

                    del responseJSON["placeableURL"]

                if "macrosetURL" in responseJSON:
                    macrosetTempGSMDir = tempfile.mkdtemp()
                    macrosetTempXMLDir = tempfile.mkdtemp()
                    macrosetTempImgDir = tempfile.mkdtemp()

                    response = request.urlopen(responseJSON["macrosetURL"])

                    with open(os.path.join(tempDir, responseJSON["macrosetName"]), "wb") as tF:
                        tF.write(response.read())

                    tasks += [(f'extractcontainer "{os.path.join(tempDir, responseJSON["macrosetName"])}" "{macrosetTempGSMDir}"'),
                              (f'l2x -img "{macrosetTempImgDir}" "{macrosetTempGSMDir}" "{macrosetTempXMLDir}"'), ]
                    foldersToExtract.update({"macroset": macrosetTempXMLDir})
                    foldersToExtract.update({"macroset_images": macrosetTempImgDir})

                    del responseJSON["macrosetURL"]

                for _dir in tasks:
                    with Popen(f'"{os.path.join(ARCHICAD_LOCATION, "LP_XMLConverter.exe")}" {_dir}',
                               stdout=PIPE, stderr=PIPE, stdin=DEVNULL) as proc:
                        _out, _err = proc.communicate()

                if "textures" in inTestData:
                    for textureToUpload in inTestData["textures"]:
                        blob_client = blob_service_client.get_blob_client(container=container_name,
                                                                          blob=textureToUpload)
                        blob_client.delete_blob()

                assErr = None

                for folderToExtract in foldersToExtract.keys():
                    path_join = os.path.join(FOLDER + "_suites", inFileName[:-5], folderToExtract)
                    for root, subfolders, files, in os.walk(foldersToExtract[folderToExtract]):
                        for receivedTestFile in files:
                            relPath = os.path.relpath(root, foldersToExtract[folderToExtract])
                            # if folderToExtract in ("macroset", "macroset_images", ):
                            #     originalRelPath = os.path.join(*relPath.split(os.sep)[1:])
                            # else:
                            #     originalRelPath = relPath
                            originalTestFile = os.path.join(path_join, relPath, receivedTestFile)
                            try:
                                try:
                                    with open(originalTestFile, "rb") as originalTest:
                                        with open(os.path.join(root, receivedTestFile), "rb") as receivedTest:
                                            inObj.assertEqual(originalTest.read(), receivedTest.read())
                                except AssertionError:
                                    "Newlines don't stop us"
                                    with open(originalTestFile, "r") as originalTest:
                                        with open(os.path.join(root, receivedTestFile), "r") as receivedTest:
                                            MAINGUID_RE = r'MainGUID\=\"[0-9A-F]{8}\-[0-9A-F]{4}\-[0-9A-F]{4}\-[0-9A-F]{4}\-[0-9A-F]{12}\"'
                                            MAINGUID_RE2= r'\<MainGUID\>[0-9A-F]{8}\-[0-9A-F]{4}\-[0-9A-F]{4}\-[0-9A-F]{4}\-[0-9A-F]{12}\<\/MainGUID\>'

                                            receivedString = receivedTest.read()
                                            if re.search(MAINGUID_RE, receivedString):
                                                receivedString = re.sub(MAINGUID_RE, 'MainGUID="00000000-0000-0000-0000-000000007E57"', receivedString)
                                                receivedString = re.sub(MAINGUID_RE2, '<MainGUID>00000000-0000-0000-0000-000000007E57</MainGUID>', receivedString)
                                                with open(os.path.join(root, receivedTestFile), "w") as f:
                                                    f.write(receivedString)
                                        with open(os.path.join(root, receivedTestFile), "r") as receivedTest:
                                            inObj.assertEqual(originalTest.read(), receivedTest.read())
                            except (AssertionError, FileNotFoundError) as a:
                                targetFolderPath = os.path.join(FOLDER + "_errors", inFileName[:-5], folderToExtract, relPath)

                                if not os.path.exists(targetFolderPath):
                                    os.makedirs(targetFolderPath)
                                shutil.copyfile(os.path.join(foldersToExtract[folderToExtract], relPath, receivedTestFile), os.path.join(FOLDER + "_errors", inFileName[:-5], folderToExtract, relPath, receivedTestFile))
                                assErr = a
                if assErr:
                    raise assErr

            try:
                inObj.assertEqual(inTestData["result"], responseJSON)
            except AssertionError:
                print(inTestData["description"])
                print(f"Filename: {inFileName[:-5]}")
                with open(outFileName, "w") as outputFile:
                    inTestData.update({"result": responseJSON})
                    json.dump(inTestData, outputFile, indent=2)
                raise

            #FIXME cleanup
        if "description" in inTestData:
            func.__name__ = inFileName[:-5] + ": " + inTestData["description"]
        else:
            func.__name__ = "test_" + inFileName[:-5]
        return func