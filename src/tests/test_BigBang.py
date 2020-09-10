#FIXME keep track and print out a string of unsuccessful tests for pasting them into TEST_ONLY environment variable

import unittest
import os
import json
import http.client
import ssl
import shutil
import tempfile
import base64
from subprocess import Popen, PIPE, DEVNULL
import re

FOLDER      = "test_BigBang"
SERVER_URL  = os.environ['SERVER_URL'] if "SERVER_URL" in os.environ else "localhost"
TEST_ONLY   = os.environ['TEST_ONLY']  if "TEST_ONLY"  in os.environ else ""
print(f"Server URL: {SERVER_URL} \n")

_SRC        = r".."
APP_CONFIG  = os.path.join(_SRC, r"appconfig.json")
with open(APP_CONFIG, "r") as ac:
    APP_JSON = json.load(ac)
    CONTENT_DIR_NAME            = APP_JSON["CONTENT_DIR_NAME"]
    ARCHICAD_LOCATION           = os.path.join(_SRC, "archicad", "LP_XMLConverter_18")

TEST_SEQUENCE_LIST = ['resetjobqueue', "extractparams", "error", "create_macroset"]

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
                    print(f"Filename: {fileName}")

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
            outFileName = os.path.join(inDir + "_errors", inFileName)
            if "localhost" in SERVER_URL:
                conn = http.client.HTTPConnection(SERVER_URL)
            else:
                s = ssl.SSLContext()
                conn = http.client.HTTPSConnection(SERVER_URL, context=s)
            headers = {"Content-Type": "application/json"}
            endp = inTestData["endpoint"]
            req = inTestData["request"]
            conn.request("POST", endp, json.dumps(req), headers)
            response = conn.getresponse()

            responseJSON = json.loads(response.read())

            conn.close()

            # FIXME actual day not tested
            # minor_version = datetime.date.today().strftime("%Y%m%d")
            # if "minor_version" in req:
            #     minor_version = req["minor_version"]

            if inTestData["endpoint"] in ("/", "/createmacroset", "/creatematerials"):
                tasks = []
                foldersToExtract = {}
                tempDir = tempfile.mkdtemp()
                if "base64_encoded_object" in responseJSON:
                    placeableTempGSMDir = tempfile.mkdtemp()
                    placeableTempXMLDir = tempfile.mkdtemp()
                    placeableTempImgDir = tempfile.mkdtemp()
                    tasks += [(f'extractcontainer "{os.path.join(tempDir, responseJSON["object_name"])}" "{placeableTempGSMDir}"'),
                              (f'l2x -img "{placeableTempImgDir}" "{placeableTempGSMDir}" "{placeableTempXMLDir}"'), ]
                    foldersToExtract.update({"placeables": placeableTempXMLDir})
                    foldersToExtract.update({"placeables_images": placeableTempImgDir})

                    with open(os.path.join(tempDir, responseJSON['object_name']), 'wb') as objectFile:
                        decode = base64.urlsafe_b64decode(responseJSON['base64_encoded_object'])
                        objectFile.write(decode)
                    del responseJSON['base64_encoded_object']

                if "base64_encoded_macroset" in responseJSON:
                    macrosetTempGSMDir = tempfile.mkdtemp()
                    macrosetTempXMLDir = tempfile.mkdtemp()
                    macrosetTempImgDir = tempfile.mkdtemp()
                    tasks += [(f'extractcontainer "{os.path.join(tempDir, responseJSON["macroset_name"])}" "{macrosetTempGSMDir}"'),
                              (f'l2x -img "{macrosetTempImgDir}" "{macrosetTempGSMDir}" "{macrosetTempXMLDir}"'), ]
                    foldersToExtract.update({"macroset": macrosetTempXMLDir})
                    foldersToExtract.update({"macroset_images": macrosetTempImgDir})

                    with open(os.path.join(tempDir, responseJSON['macroset_name']), 'wb') as objectFile:
                        decode = base64.urlsafe_b64decode(responseJSON['base64_encoded_macroset'])
                        objectFile.write(decode)
                    del responseJSON['base64_encoded_macroset']

                for _dir in tasks:
                    with Popen(f'"{os.path.join(ARCHICAD_LOCATION, "LP_XMLConverter.exe")}" {_dir}',
                               stdout=PIPE, stderr=PIPE, stdin=DEVNULL) as proc:
                        _out, _err = proc.communicate()

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
                    json.dump(inTestData, outputFile, indent=4)
                raise

            #FIXME cleanup
        if "description" in inTestData:
            func.__name__ = inTestData["description"]
        else:
            func.__name__ = "test_" + inFileName[:-5]
        return func