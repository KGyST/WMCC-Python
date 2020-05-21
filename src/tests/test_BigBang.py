import unittest
import os
import json
import http.client
import ssl
import datetime
import shutil

FOLDER      = "test_BigBang"
SERVER_URL  = "localhost"
_SRC        = r".."
APP_CONFIG  = os.path.join(_SRC, r"appconfig.json")

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
                print("*********Internal Server Error********")
                conn.request("POST", "/resetjobqueue", "", headers)
                response = json.loads(conn.getresponse().read())

            conn.close()

            minor_version = datetime.date.today().strftime("%Y%m%d")
            if "minor_version" in req:
                minor_version = req["minor_version"]

            lcfFile = None
            jsonFile = None

            if inTestData["endpoint"] == "/createmacroset":
                lcfFile  = os.path.join(TARGET_GDL_DIR_NAME, "_".join(["macroset", req["category"], req["main_version"], minor_version]) + ".lcf")
                jsonFile = os.path.join(TARGET_GDL_DIR_NAME, "_".join(["macroset", req["category"], req["main_version"]]) + ".json")
            elif inTestData["endpoint"] == "/":
                lcfFile  = os.path.join(TARGET_GDL_DIR_NAME, "_".join([req["template"]["ARCHICAD_template"]["category"], req["productName"]]) + ".lcf")

            if 'base64_encoded_object' in response:
                del response['base64_encoded_object']
            if 'test_lcf' in response:
                del response['test_lcf']

            try:
                inObj.assertEqual(inTestData["result"], response)
            except AssertionError:
                print(inTestData["description"])
                with open(outFileName, "w") as outputFile:
                    json.dump(response, outputFile, indent=4)

                try:
                    if lcfFile:
                        shutil.move(lcfFile, os.path.join(inDir + "_errors", inFileName + ".lcf"))
                    if jsonFile:
                        shutil.copyfile(jsonFile, os.path.join(inDir + "_errors", inFileName + ".json"))
                except PermissionError:
                    print(f"**********PermissionError: {inFileName}**********")
                raise

        func.__name__ = "test_" + inFileName[:-5]
        return func