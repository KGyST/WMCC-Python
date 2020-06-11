import sys
import json
import base64
import tempfile
import os
from subprocess import Popen, PIPE, DEVNULL
import shutil

_SRC = "..\src"
ARCHICAD_LOCATION = os.path.join(_SRC, "archicad", "LP_XMLConverter_18")

def extractLCF(inTempLcfPath, inOutputDirPath):
    '''
    Builds up an LCF from a set of Folders
    :return:
    '''
    output = '"%s" extractcontainer "%s" "%s"' % (os.path.join(ARCHICAD_LOCATION, 'LP_XMLConverter.exe'), inTempLcfPath, inOutputDirPath)
    print(output)
    with Popen(output, stdout=PIPE, stderr=PIPE, stdin=DEVNULL) as proc:
        _out, _err = proc.communicate()

    print(_out)



def lcfWriter():
    with open(sys.argv[1], "r") as jF:
        jsonDict = json.load(jF)

        for objName, objContent in zip (("macroset_name", "object_name", ),("base64_encoded_macroset", "base64_encoded_object" )):
            tempDirPath = tempfile.mkdtemp()

            with open(os.path.join(tempDirPath, jsonDict[objName]), "wb") as objFile:
                print(jsonDict[objName])
                objFile.write(base64.urlsafe_b64decode(jsonDict[objContent]))

            inTargetDir = "." if len(sys.argv) < 3 else sys.argv[2]

            targetDirPath = os.path.join(inTargetDir, jsonDict[objName])

            if os.path.exists(targetDirPath):
                shutil.rmtree(targetDirPath)
            os.mkdir(targetDirPath)
            extractLCF(os.path.join(tempDirPath, jsonDict[objName]), targetDirPath)

if __name__ == '__main__':
    lcfWriter()