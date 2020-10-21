import unittest
from WMCC import Param
from lxml import etree
import os
import os.path

PAR_UNKNOWN     = 0
PAR_LENGTH      = 1
PAR_ANGLE       = 2
PAR_REAL        = 3
PAR_INT         = 4
PAR_BOOL        = 5
PAR_STRING      = 6
PAR_MATERIAL    = 7
PAR_LINETYPE    = 8
PAR_FILL        = 9
PAR_PEN         = 10
PAR_SEPARATOR   = 11
PAR_TITLE       = 12
PAR_COMMENT     = 13

PARFLG_CHILD    = 1
PARFLG_BOLDNAME = 2
PARFLG_UNIQUE   = 3
PARFLG_HIDDEN   = 4

class TestSuiteParam(unittest.TestSuite):
    def __init__(self):
        self._tests = []
        dir_prefix = os.path.join("src", "tests", 'test_param')
        dirName = dir_prefix + "_items"
        for testFileName in os.listdir(dirName):
            if os.path.isfile(os.path.join(dirName, testFileName)) and testFileName[0] != '_':
                print(testFileName)
                tp = TestParam(testFileName, dir_prefix)
                self.addTest(tp)
            elif os.path.isfile(os.path.join(dirName, testFileName)) and testFileName[0] == '_':
                #FIXME expected failures to be here
                pass
        super(TestSuiteParam, self).__init__(self._tests)


class TestParam(unittest.TestCase):
    def __init__(self, inFile, inDirPreFix):
        func = self.ParamTestCaseFactory(inFile, inDirPreFix)
        setattr(TestParam, func.__name__, func)
        super(TestParam, self).__init__(func.__name__)

    @staticmethod
    def ParamTestCaseFactory(inFileName, inDirPrefix):
        def func(inObj):
            with open(os.path.join(inDirPrefix + "_items", inFileName), "r") as testFile:
                testNode = testFile.read()
                par = Param(inETree=etree.XML(testNode))
                out_file_name = os.path.join(inDirPrefix + "_errors", inFileName)
                if os.path.isfile(out_file_name):
                    os.remove(out_file_name)
                try:
                    inObj.assertEqual(testNode, etree.tostring(par.eTree, encoding = "unicode"))

                    fChild = False
                    fUnique = False
                    fHidden = False
                    fBold = False

                    if par.iType not in (PAR_COMMENT,):
                        if PARFLG_CHILD     in par.flags: fChild  = True
                        if PARFLG_UNIQUE    in par.flags: fUnique = True
                        if PARFLG_HIDDEN    in par.flags: fHidden = True
                        if PARFLG_BOLDNAME  in par.flags: fBold   = True

                    par2 = Param(
                         inType = par.iType,
                         inName = par.name,
                         inDesc = par.desc,
                         inValue = par.value,
                         inAVals = par.aVals,
                         inChild=fChild,
                         inUnique=fUnique,
                         inHidden=fHidden,
                         inBold=fBold)

                    inObj.assertEqual(testNode, etree.tostring(par2.eTree, encoding = "unicode"))
                except AssertionError:
                    with open(out_file_name, "w") as of:
                        of.write( etree.tostring(par.eTree, encoding = "unicode"))
                    raise

        func.__name__ = "test_" + inFileName[:-4]
        return func
