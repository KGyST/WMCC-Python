import unittest
import os
import json
import http.client
import ssl
import datetime
import shutil
import tempfile
import base64
from subprocess import Popen, PIPE, DEVNULL

FOLDER      = "test_BigBang"
SERVER_URL  = os.environ['SERVER_URL'] if "SERVER_URL" in os.environ else "localhost"
print(SERVER_URL)
_SRC        = r".."
APP_CONFIG  = os.path.join(_SRC, r"appconfig.json")
SOURCE_DIR_NAME             = os.path.join(_SRC, r"archicad")
ARCHICAD_LOCATION           = os.path.join(SOURCE_DIR_NAME, "LP_XMLConverter_18")

class FileName(str):
    """
    Class for sorting test cases represented by filenames
    """
    def __gt__(self, other):
        if self.startswith('resetjobqueue'):
            return False
        elif self.startswith("create_macroset") and not other.startswith("create_macroset"):
            return False
        elif not self.startswith("create_macroset") and other.startswith("create_macroset"):
            return True
        else:
            return str(self) < str(other)

    def __lt__(self, other):
        if self.startswith('resetjobqueue'):
            return True
        elif self.startswith("create_macroset") and not other.startswith("create_macroset"):
            return True
        elif not self.startswith("create_macroset") and other.startswith("create_macroset"):
            return False
        else:
            return str(self) > str(other)

class TestSuite_BigBang(unittest.TestSuite):
    def __init__(self):
        self._tests = []
        self._fileList = sorted([FileName(f) for f in os.listdir(FOLDER + "_suites")])
        for fileName in self._fileList:
            if not fileName.startswith('_') and os.path.splitext(fileName)[1] == '.json':
                testData = json.load(open(os.path.join(FOLDER + "_suites", fileName), "r"))

                test_case = TestCase_BigBang(testData, FOLDER, fileName)
                self.addTest(test_case)

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
            with open(APP_CONFIG, "r") as ac:
                appJSON = json.load(ac)
                TARGET_GDL_DIR_NAME = os.path.join("..", "..", appJSON["TARGET_GDL_DIR_NAME"])

            outFileName = os.path.join(inDir + "_errors", inFileName)
            s = ssl.SSLContext()
            conn = http.client.HTTPSConnection(SERVER_URL, context=s)
            headers = {"Content-Type": "application/json"}
            endp = inTestData["endpoint"]
            req = inTestData["request"]
            conn.request("POST", endp, json.dumps(req), headers)
            response = json.loads(conn.getresponse().read())

            if response == {'message': 'Internal Server Error'}:
                #FIXME response codes > 399
                print("*********Internal Server Error********")
                conn.request("POST", "/resetjobqueue", "", headers)
                response = json.loads(conn.getresponse().read())

            conn.close()

            # minor_version = datetime.date.today().strftime("%Y%m%d")
            # if "minor_version" in req:
            #     minor_version = req["minor_version"]

            if inTestData["endpoint"] == "/":
                tempDir = tempfile.mkdtemp()
                placeableTempGSMDir = tempfile.mkdtemp()
                placeableTempXMLDir = tempfile.mkdtemp()
                tasks = [("extractcontainer", os.path.join(tempDir, response['object_name']), placeableTempGSMDir, ),
                          ("l2x", placeableTempGSMDir, placeableTempXMLDir,), ]
                folders = {"placeables": placeableTempXMLDir}

                with open(os.path.join(tempDir, response['object_name']), 'wb') as objectFile:
                    decode = base64.urlsafe_b64decode(response['base64_encoded_object'])
                    objectFile.write(decode)
                del response['base64_encoded_object']

                if "base64_encoded_macroset" in response:
                    macrosetTempGSMDir = tempfile.mkdtemp()
                    macrosetTempXMLDir = tempfile.mkdtemp()
                    tasks += [("extractcontainer", os.path.join(tempDir, response['macroset_name']), macrosetTempGSMDir,),
                              ("l2x", macrosetTempGSMDir, macrosetTempXMLDir,), ]
                    folders.update({"macroset": macrosetTempXMLDir})

                    with open(os.path.join(tempDir, response['macroset_name']), 'wb') as objectFile:
                        decode = base64.urlsafe_b64decode(response['base64_encoded_macroset'])
                        objectFile.write(decode)
                    del response['base64_encoded_macroset']

                for _dir in tasks:
                    with Popen(f'"{os.path.join(ARCHICAD_LOCATION, "LP_XMLConverter.exe")}" {_dir[0]} "{_dir[1]}" "{_dir[2]}"',
                               stdout=PIPE, stderr=PIPE, stdin=DEVNULL) as proc:
                        _out, _err = proc.communicate()

                assErr = None

                for folder in folders.keys():
                    path_join = os.path.join(FOLDER + "_suites", inFileName[:-5], folder)
                    for root, subfolders, files, in os.walk(folders[folder]):
                        for receivedTestFile in files:
                            relPath = os.path.relpath(root, folders[folder])
                            if folder == "macroset":
                                originalRelPath = os.path.join(*relPath.split(os.sep)[1:])
                            else:
                                originalRelPath = relPath
                            originalTestFile = os.path.join(path_join, originalRelPath, receivedTestFile)
                            try:
                                originalTest = open(originalTestFile, "rb")
                                receivedTest = open(os.path.join(root, receivedTestFile), "rb")
                                inObj.assertEqual(originalTest.read(), receivedTest.read())
                                originalTest.close()
                                receivedTest.close()

                            except (AssertionError, FileNotFoundError) as a:
                                targetFolderPath = os.path.join(FOLDER + "_errors", inFileName[:-5], folder, originalRelPath)

                                if not os.path.exists(targetFolderPath):
                                    os.makedirs(targetFolderPath)
                                shutil.copyfile(os.path.join(folders[folder], relPath, receivedTestFile), os.path.join(FOLDER + "_errors", inFileName[:-5], folder, originalRelPath, receivedTestFile))
                                assErr = a
                if assErr:
                    raise assErr

            try:
                inObj.assertEqual(inTestData["result"], response)
            except AssertionError:
                print(inTestData["description"])
                with open(outFileName, "w") as outputFile:
                    json.dump(response, outputFile, indent=4)
                raise

            #FIXME cleanup

        func.__name__ = "test_" + inFileName[:-5]
        return func