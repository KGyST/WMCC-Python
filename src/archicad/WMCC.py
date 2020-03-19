import os.path
from os import listdir
import uuid
import re
import tempfile
from subprocess import check_output, Popen, PIPE, DEVNULL
import shutil
# import sys
import datetime
import jsonpickle
# import os
import multiprocessing as mp
# from functools import partial

# import string

import copy
import argparse

import http.client, http.server, urllib.request, urllib.parse, urllib.error, json, webbrowser, urllib.parse, os, hashlib, base64
# import pip
import logging

#------------------ External modules------------------

from lxml import etree

#------------------/External modules------------------

#------------------ Temporary constants------------------

DEBUG                       = False
CLEANUP                     = False     # Do cleanup after finish
OUTPUT_XML                  = True      # To retain xmls
_SRC                        = r".\src"
ADDITIONAL_IMAGE_DIR_NAME   = os.path.join(_SRC, r"_IMAGES_GENERIC_")
TARGET_GDL_DIR_NAME         = os.path.join(_SRC, r"Target")
TRANSLATIONS_JSON           = os.path.join(_SRC, r"translations.json")
SOURCE_DIR_NAME             = os.path.join(_SRC, r"archicad")
ARCHICAD_LOCATION           = os.path.join(SOURCE_DIR_NAME, "LP_XMLConverter_18")
WMCC_BRAND_NAME             = "WMCC"
MATERIAL_BASE_OBJECT        = "_dev_material"

BO_AUTHOR                   = "BIMobject"
BO_LICENSE                  = "CC BY-ND"
BO_LICENSE_VERSION          = "3.0"

TARGET_IMAGE_DIR_NAME       = "" #REMOVE
TARGET_XML_DIR_NAME         = "" #REMOVE


#------------------/Temporary constants------------------

ADD_STRING = True   # If sourceFile has not WMCC_BRAND_NAME then add "_" + NEW_BRAND_NAME to at its end
OVERWRITE = False

PERSONAL_ID = "ac4e5af2-7544-475c-907d-c7d91c810039"    #FIXME to be deleted after BO API v1 is removed

AC_18           = 28
SCRIPT_NAMES_LIST = ["Script_1D",
                     "Script_2D",
                     "Script_3D",
                     "Script_PR",
                     "Script_UI",
                     "Script_VL",
                     "Script_FWM",
                     "Script_BWM",]

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

app = None
family_name = ""
projectPath = ""

dest_sourcenames    = {}   #source name             -> DestXMLs, idx by original filename
dest_guids          = {}   #dest guid               -> DestXMLs, idx by
source_guids        = {}   #Source GUID             -> Source XMLs, idx by
id_dict             = {}   #Source GUID             -> dest GUID
dest_dict           = {}   #dest name               -> DestXML
replacement_dict    = {}   #source filename, w/o ext-> SourceXMLs
pict_dict           = {}   #dest image filename     ->
source_pict_dict    = {}   #source image filename   ->

all_keywords = set()

# ------------------- parameter classes --------------------------------------------------------------------------------

class ArgParse(argparse.ArgumentParser):
    # Overriding exit method that stops whole program in case of bad parametrization
    def exit(self, *_):
        try:
            pass
        except TypeError:
            pass


class ParamSection:
    """
    iterable class of all params
    """
    def __init__(self, inETree):
        # self.eTree          = inETree
        self.__header       = etree.tostring(inETree.find("ParamSectHeader"))
        self.__paramList    = []
        self.__paramDict    = {}
        self.__index        = 0
        self.usedParamSet   = {}

        for attr in ["SectVersion", "SectionFlags", "SubIdent", ]:
            if attr in inETree.attrib:
                setattr(self, attr, inETree.attrib[attr])
            else:
                setattr(self, attr, None)

        for p in inETree.find("Parameters"):
            param = Param(p)
            self.append(param, param.name)

    def __iter__(self):
        return self

    def __next__(self):
        if self.__index >= len(self.__paramList) - 1:
            raise StopIteration
        else:
            self.__index += 1
            return self.__paramList[self.__index]

    def __contains__(self, item):
        return item in self.__paramDict

    def __setitem__(self, key, value):
        if key in self.__paramDict:
            self.__paramDict[key].setValue(value)
        else:
            # FIXME cannot set a Param without knowing its type etc
            self.append(value, key)

    def __delitem__(self, key):
        del self.__paramDict[key]
        self.__paramList = [i for i in self.__paramList if i.name != key]

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.__paramList[item]
        if isinstance(item, str):
            return self.__paramDict[item]

    def append(self, inEtree, inParName):
        #Adding param to the end
        self.__paramList.append(inEtree)
        if not isinstance(inEtree, etree._Comment):
            self.__paramDict[inParName] = inEtree

    def insertAfter(self, inParName, inEtree):
        self.__paramList.insert(self.__getIndex(inParName) + 1, inEtree)

    def insertBefore(self, inParName, inEtree):
        self.__paramList.insert(self.__getIndex(inParName), inEtree)

    def insertAsChild(self, inParentParName, inEtree):
        """
        inserting under a title
        :param inParentParName:
        :param inEtree:
        :param inPos:      position, 0 is first, -1 is last #FIXME
        :return:
        """
        base = self.__getIndex(inParentParName)
        i = 1
        if self.__paramList[base].iType == PAR_TITLE:
            nP = self.__paramList[base + i]
            try:
                while nP.iType != PAR_TITLE and \
                        PARFLG_CHILD in nP.flags:
                    i += 1
                    nP = self.__paramList[base + i]
            except IndexError:
                pass
            self.__paramList.insert(base + i, inEtree)
            self.__paramDict[inEtree.name] = inEtree

    def remove_param(self, inParName):
        if inParName in self.__paramDict:
            obj = self.__paramDict[inParName]
            while obj in self.__paramList:
                self.__paramList.remove(obj)
            del self.__paramDict[inParName]

    def upsert_param(self, inParName):
        #FIXME
        pass

    def __getIndex(self, inName):
        return [p.name for p in self.__paramList].index(inName)

    def get(self, inName):
        '''
        Get parameter by its name as lxml Element
        :param inName:
        :return:
        '''
        return self.__paramList[self.__getIndex(inName)]

    def getChildren(self, inETree):
        """
        Return children of a Parameter
        :param inETree:
        :return:        List of children, as lxml Elements
        """
        result = []
        idx = self.__getIndex(inETree.name)
        if inETree.iType != PAR_TITLE:    return None
        for p in self.__paramList[idx:]:
            if PARFLG_CHILD in p.flags:
                result.append(p)
            else:
                return result

    def toEtree(self):
        eTree = etree.Element("ParamSection", SectVersion=self.SectVersion, SectionFlags=self.SectionFlags, SubIdent=self.SubIdent, )
        eTree.text = '\n\t'
        eTree.append(etree.fromstring(self.__header))
        eTree.tail = '\n'

        parTree = etree.Element("Parameters")
        parTree.text = '\n\t\t'
        parTree.tail = '\n'
        eTree.append(parTree)
        for par in self.__paramList:
            elem = par.eTree
            ix = self.__paramList.index(par)
            if ix == len(self.__paramList) - 1:
                elem.tail = '\n\t'
            else:
                if self.__paramList[ix + 1].iType == PAR_COMMENT:
                    elem.tail = '\n\n\t\t'
            parTree.append(elem)
        return eTree

    def BO_update(self, prodatURL):
        #FIXME code for unsuccessful updates, BO_edinum to -1, removing BO_productguid
        #FIXME new authentication
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        _xml = urllib.parse.urlencode({"value": "<?xml version='1.0' encoding='UTF-8'?>"
                                            "<Bim API='%s'>"
                                                "<Objects>"
                                                    "<Object ProductId='%s'/>"
                                                "</Objects>"
                                            "</Bim>" % (PERSONAL_ID, prodatURL, )})

        conn = http.client.HTTPSConnection("api.bimobject.com")
        conn.request("POST", "/GetBimObjectInfoXml2", _xml, headers)
        response = conn.getresponse()
        resp = response.read()
        resTree = etree.fromstring(resp)

        BO_PARAM_TUPLE = ('BO_Title',
                          'BO_Separator',
                          'BO_prodinfo',
                          'BO_prodsku', 'BO_Manufac', 'BO_brandurl', 'BO_prodfam', 'BO_prodgroup',
                          'BO_mancont', 'BO_designcont', 'BO_publisdat', 'BO_edinum', 'BO_width',
                          'BO_height', 'BO_depth', 'BO_weight', 'BO_productguid',
                          'BO_links',
                          'BO_boqrurl', 'BO_producturl', 'BO_montins', 'BO_prodcert', 'BO_techcert',
                          'BO_youtube', 'BO_ean',
                          'BO_real',
                          'BO_mainmat', 'BO_secmat',
                          'BO_classific',
                          'BO_bocat', 'BO_ifcclas', 'BO_unspc', 'BO_uniclass_1_4_code', 'BO_uniclass_1_4_desc',
                          'BO_uniclass_2_0_code', 'BO_uniclass_2_0_desc', 'BO_uniclass2015_code', 'BO_uniclass2015_desc', 'BO_nbs_ref',
                          'BO_nbs_desc', 'BO_omniclass_code', 'BO_omniclass_name', 'BO_masterformat2014_code', 'BO_masterformat2014_name',
                          'BO_uniformat2_code', 'BO_uniformat2_name', 'BO_cobie_type_cat',
                          'BO_regions',
                          'BO_europe', 'BO_northamerica', 'BO_southamerica', 'BO_middleeast', 'BO_asia',
                          'BO_oceania', 'BO_africa', 'BO_antarctica', 'BO_Separator2',)
        for p in BO_PARAM_TUPLE:
            self.remove_param(p)

        for p in BO_PARAM_TUPLE:
            e = next((par for par in resTree.findall("Object/Parameters/Parameter") if par.get('VariableName') == p), '')
            if isinstance(e, etree._Element):
                varName = e.get('VariableName')
                if varName in ('BO_Title', 'BO_prodinfo', 'BO_links', 'BO_real', 'BO_classific', 'BO_regions',):
                    comment = Param(inName=varName,
                                    inDesc=e.get('VariableDescription'),
                                    inType=PAR_COMMENT,)
                    self.append(comment, 'BO_Title')
                param = Param(inName=varName,
                              inDesc=e.get('VariableDescription'),
                              inValue=e.text,
                              inTypeStr=e.get('VariableType'),
                              inAVals=None,
                              inChild=(e.get('VariableModifier')=='Child'),
                              inBold=(e.get('VariableStyle')=='Bold'), )
                self.append(param, varName)
            self.__paramList[-1].tail = '\n\t'

    def createParamfromCSV(self, inParName, inCol, inArrayValues = None):
        splitPars = inParName.split(" ")
        parName = splitPars[0]
        ap = ArgParse(add_help=False)
        ap.add_argument("-d", "--desc" , "--description", nargs="+")        # action=ConcatStringAction,
        ap.add_argument("-t", "--type")
        ap.add_argument("-f", "--frontof" )
        ap.add_argument("-a", "--after" )
        ap.add_argument("-c", "--child")
        ap.add_argument("-h", "--hidden", action='store_true')
        ap.add_argument("-b", "--bold", action='store_true')
        ap.add_argument("-u", "--unique", action='store_true')
        ap.add_argument("-o", "--overwrite", action='store_true')
        ap.add_argument("-i", "--inherit", action='store_true', help='Inherit properties form the other parameter')
        ap.add_argument("-y", "--array", action='store_true', help='Insert an array of [0-9]+ or  [0-9]+x[0-9]+ size')
        ap.add_argument("-r", "--remove", action='store_true')

        parsedArgs = ap.parse_known_args(splitPars)[0]

        if parsedArgs.desc is not None:
            desc = " ".join(parsedArgs.desc)
        else:
            desc = ''

        if parName not in self:
            parType = PAR_UNKNOWN
            if parsedArgs.type:
                if parsedArgs.type in ("Length", ):
                    parType = PAR_LENGTH
                elif parsedArgs.type in ("Angle", ):
                    parType = PAR_ANGLE
                elif parsedArgs.type in ("RealNum", ):
                    parType = PAR_REAL
                elif parsedArgs.type in ("Integer", ):
                    parType = PAR_INT
                elif parsedArgs.type in ("Boolean", ):
                    parType = PAR_BOOL
                elif parsedArgs.type in ("String", ):
                    parType = PAR_STRING
                elif parsedArgs.type in ("Material", ):
                    parType = PAR_MATERIAL
                elif parsedArgs.type in ("LineType", ):
                    parType = PAR_LINETYPE
                elif parsedArgs.type in ("FillPattern", ):
                    parType = PAR_FILL
                elif parsedArgs.type in ("PenColor", ):
                    parType = PAR_PEN
                elif parsedArgs.type in ("Separator", ):
                    parType = PAR_SEPARATOR
                elif parsedArgs.type in ("Title", ):
                    parType = PAR_TITLE
                elif parsedArgs.type in ("Comment", ):
                    parType = PAR_COMMENT
                    parName = " " + parName + ": PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK "
            else:
                if re.match(r'\bis[A-Z]', splitPars[0]) or re.match(r'\bb[A-Z]', splitPars[0]):
                    parType = PAR_BOOL
                elif re.match(r'\bi[A-Z]', splitPars[0]) or re.match(r'\bn[A-Z]', splitPars[0]):
                    parType = PAR_INT
                elif re.match(r'\bs[A-Z]', splitPars[0]) or re.match(r'\bst[A-Z]', splitPars[0]) or re.match(r'\bmp_', splitPars[0]):
                    parType = PAR_STRING
                elif re.match(r'\bx[A-Z]', splitPars[0]) or re.match(r'\by[A-Z]', splitPars[0]) or re.match(r'\bz[A-Z]', splitPars[0]):
                    parType = PAR_LENGTH
                elif re.match(r'\bx[A-Z]', splitPars[0]):
                    parType = PAR_ANGLE
                else:
                    parType = PAR_STRING

            if not inArrayValues:
                arrayValues = None
                if parType in (PAR_LENGTH, PAR_ANGLE, PAR_REAL, ):
                    inCol = float(inCol)
                elif parType in (PAR_INT, PAR_MATERIAL, PAR_LINETYPE, PAR_FILL, PAR_PEN, ):
                    inCol = int(inCol)
                elif parType in (PAR_BOOL, ):
                    inCol = bool(int(inCol))
                elif parType in (PAR_STRING, ):
                    inCol = inCol
                elif parType in (PAR_TITLE, ):
                    inCol = None
            else:
                inCol = None
                if parType in (PAR_LENGTH, PAR_ANGLE, PAR_REAL, ):
                    arrayValues = [float(x) if type(x) != list else [float(y) for y in x] for x in inArrayValues]
                elif parType in (PAR_INT, PAR_MATERIAL, PAR_LINETYPE, PAR_FILL, PAR_PEN, ):
                    arrayValues = [int(x) if type(x) != list else [int(y) for y in x] for x in inArrayValues]
                elif parType in (PAR_BOOL, ):
                    arrayValues = [bool(int(x)) if type(x) != list else [bool(int(y)) for y in x] for x in inArrayValues]
                elif parType in (PAR_STRING, ):
                    arrayValues = [x if type(x) != list else [y for y in x] for x in inArrayValues]
                elif parType in (PAR_TITLE, ):
                    inCol = None

            if parsedArgs.inherit:
                if parsedArgs.child:
                    paramToInherit = self.__paramDict[parsedArgs.child]
                elif parsedArgs.after:
                    paramToInherit = self.__paramDict[parsedArgs.after]
                elif parsedArgs.frontof:
                    paramToInherit = self.__paramDict[parsedArgs.frontof]

                isChild  =  PARFLG_CHILD in paramToInherit.flags
                isBold = PARFLG_BOLDNAME in paramToInherit.flags
                isUnique = PARFLG_UNIQUE in paramToInherit.flags
                isHidden = PARFLG_HIDDEN in paramToInherit.flags
            else:
                isChild = "child" in dir(parsedArgs)
                isBold = parsedArgs.bold
                isUnique = parsedArgs.unique
                isHidden = parsedArgs.hidden

            param = Param(inType=parType,
                          inName=parName,
                          inDesc=desc,
                          inValue=inCol,
                          inChild=isChild,
                          inBold=isBold,
                          inHidden=isHidden,
                          inUnique=isUnique,
                          inAVals=arrayValues)

            if parsedArgs.child:
                self.insertAsChild(parsedArgs.child, param)
            elif parsedArgs.after:
                self.insertAfter(parsedArgs.after, param)
            elif parsedArgs.frontof:
                self.insertBefore(parsedArgs.frontof, param)
            else:
                #FIXME writing tests for this
                self.append(param, parName)

            if parType == PAR_TITLE:
                paramComment = Param(inType=PAR_COMMENT,
                                     inName=" " + parName + ": PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK ", )
                self.insertBefore(param.name, paramComment)
        else:
            # FIXME writing tests for this
            if parsedArgs.remove:
                if inCol:
                    del self[parName]
            else:
                self[parName] = inCol
                if desc:
                    self.__paramDict[parName].desc = " ".join(parsedArgs.desc)

    def returnParamsAsDict(self):
        """
        Returns important parameters as a dict of primitive elements
        :return:
        """
        return [{"index": self.__paramList.index(p),
                 "name": p.name,
                   "type": Param.tagBackList[p.iType],
                   "desc": p.desc.strip('"'),
                   "value": p.value
                       if not p.aVals
                       else [r[0]
                             if len(r) == 1
                             else [c for c in r] for r in p._aVals],
                   "flags": [Param.flagBackList[f] for f in p.flags] if p.iType not in (PAR_COMMENT, ) else [],
                   } for p in self.__paramList]

class Param(object):
    tagBackList = ["", "Length", "Angle", "RealNum", "Integer", "Boolean", "String", "Material",
                   "LineType", "FillPattern", "PenColor", "Separator", "Title", "Comment"]

    flagBackList =["", "Child", "Bold", "Unique", "Hidden", ]

    def __init__(self, inETree = None,
                 inType = PAR_UNKNOWN,
                 inName = '',
                 inDesc = '',
                 inValue = None,
                 inAVals = None,
                 inTypeStr='',
                 inChild=False,
                 inUnique=False,
                 inHidden=False,
                 inBold=False):
        self.__index = 0
        self.value      = None

        if inETree is not None:
            self.eTree = inETree
        else:            # Start from a scratch
            self.iType  = inType
            if inTypeStr:
                self.iType  = self.getTypeFromString(inTypeStr)

            self.name   = inName
            if len(self.name) > 32 and self.iType != PAR_COMMENT: self.name = self.name[:32]
            if inValue is not None:
                self.value = inValue

            if self.iType != PAR_COMMENT:
                self.flags = set()
                if inChild:
                    self.flags |= {PARFLG_CHILD}
                if inUnique:
                    self.flags |= {PARFLG_UNIQUE}
                if inHidden:
                    self.flags |= {PARFLG_HIDDEN}
                if inBold:
                    self.flags |= {PARFLG_BOLDNAME}

            if self.iType not in (PAR_COMMENT, PAR_SEPARATOR, ):
                self.desc   = inDesc
                self.aVals  = inAVals
            elif self.iType == PAR_SEPARATOR:
                self.desc   = inDesc
                self._aVals = None
                self.value  = None
            elif self.iType == PAR_COMMENT:
                pass
        self.isInherited    = False
        self.isUsed         = True

    def __iter__(self):
        if self._aVals:
            return self

    def __next__(self):
        if self.__index >= len(self._aVals) - 1:
            raise StopIteration
        else:
            self.__index += 1
            return self._aVals[self.__index]

    def __setitem__(self, key, value):
        if isinstance(value, list):
            self._aVals[key - 1] = self.__toFormat(value)
            self.__fd = max(self.__fd, key - 1)
            self.__sd = max(self.__sd, len(value))
        else:
            self._aVals[key - 1] = [self.__toFormat(value)]
            self.__fd = max(self.__fd, key - 1)

    def setValue(self, inVal):
        if type(inVal) == list:
            self.aVals = self.__toFormat(inVal)
            if self.value:
                print("WARNING: value -> array change: %s" % self.name)
            self.value = None
        else:
            self.value = self.__toFormat(inVal)
            if self.aVals:
                print("WARNING: array -> value change: %s" % self.name)
            self.aVals = None

    def __toFormat(self, inData):

        """
        Returns data converted from string according to self.iType
        :param inData:
        :return:
        """
        if type(inData) == list:
            return list(map (self.__toFormat, inData))
        if self.iType in (PAR_LENGTH, PAR_REAL, PAR_ANGLE):
            # self.digits = 2
            return float(inData)
        elif self.iType in (PAR_INT, PAR_MATERIAL, PAR_PEN, PAR_LINETYPE, PAR_MATERIAL):
            return int(inData)
        elif self.iType in (PAR_BOOL, ):
            return bool(int(inData))
        elif self.iType in (PAR_SEPARATOR, PAR_TITLE, ):
            return None
        else:
            return inData

    def _valueToString(self, inVal):
        if self.iType in (PAR_STRING, ):
            if inVal is not None:
                if not inVal.startswith('"'):
                    inVal = '"' + inVal
                if not inVal.endswith('"') or len(inVal) == 1:
                    inVal += '"'
                return etree.CDATA(inVal)
            else:
                return etree.CDATA('""')
        elif self.iType in (PAR_REAL, PAR_LENGTH, PAR_ANGLE):
            nDigits = 0
            eps = 1E-7
            maxN = 1E12
            # if maxN < abs(inVal) or eps > abs(inVal) > 0:
            #     return "%E" % inVal
            #FIXME 1E-012 and co
            # if -eps < inVal < eps:
            #     return 0
            s = '%.' + str(nDigits) + 'f'
            while nDigits < 8:
                if (inVal - eps < float(s % inVal) < inVal + eps):
                    break
                nDigits += 1
                s = '%.' + str(nDigits) + 'f'
            return s % inVal
        elif self.iType in (PAR_BOOL, ):
            return "0" if not inVal else "1"
        elif self.iType in (PAR_SEPARATOR, ):
            return None
        else:
            return str(inVal)

    @property
    def eTree(self):
        if self.iType < PAR_COMMENT:
            tagString = self.tagBackList[self.iType]
            elem = etree.Element(tagString, Name=self.name)
            nTabs = 3 if self.desc or self.flags is not None or self.value is not None or self.aVals is not None else 2
            elem.text = '\n' + nTabs * '\t'

            desc = etree.Element("Description")
            if not self.desc.startswith('"'):
                self.desc = '"' + self.desc
            if not self.desc.endswith('"') or self.desc == '"':
                self.desc += '"'
            desc.text = etree.CDATA(self.desc)
            nTabs = 3 if len(self.flags) or self.value is not None or self.aVals is not None else 2
            desc.tail = '\n' + nTabs * '\t'
            elem.append(desc)

            if self.flags:
                flags = etree.Element("Flags")
                nTabs = 3 if self.value is not None or self.aVals is not None else 2
                flags.tail = '\n' + nTabs * '\t'
                flags.text = '\n' + 4 * '\t'
                elem.append(flags)
                flagList = list(self.flags)
                for f in flagList:
                    if   f == PARFLG_CHILD:    element = etree.Element("ParFlg_Child")
                    elif f == PARFLG_UNIQUE:   element = etree.Element("ParFlg_Unique")
                    elif f == PARFLG_HIDDEN:   element = etree.Element("ParFlg_Hidden")
                    elif f == PARFLG_BOLDNAME: element = etree.Element("ParFlg_BoldName")
                    nTabs = 4 if flagList.index(f) < len(flagList) - 1 else 3
                    element.tail = '\n' + nTabs * '\t'
                    flags.append(element)

            if self.value is not None or (self.iType == PAR_STRING and self.aVals is None):
                #FIXME above line why string?
                value = etree.Element("Value")
                value.text = self._valueToString(self.value)
                value.tail = '\n' + 2 * '\t'
                elem.append(value)
            elif self.aVals is not None:
                elem.append(self.aVals)
            elem.tail = '\n' + 2 * '\t'
        else:
            elem = etree.Comment(self.name)
            elem.tail = 2 * '\n' + 2 * '\t'
        return elem

    @eTree.setter
    def eTree(self, inETree):
        self.text = inETree.text
        self.tail = inETree.tail
        if not isinstance(inETree, etree._Comment):
            # __eTree = inETree
            self.flags = set()
            self.iType = self.getTypeFromString(inETree.tag)

            self.name       = inETree.attrib["Name"]
            self.desc       = inETree.find("Description").text
            self.descTail   = inETree.find("Description").tail

            val = inETree.find("Value")
            if val is not None:
                self.value = self.__toFormat(val.text)
                self.valTail = val.tail
            else:
                self.value = None
                self.valTail = None

            self.aVals = inETree.find("ArrayValues")

            if inETree.find("Flags") is not None:
                self.flagsTail = inETree.find("Flags").tail
                for f in inETree.find("Flags"):
                    if f.tag == "ParFlg_Child":     self.flags |= {PARFLG_CHILD}
                    if f.tag == "ParFlg_Unique":    self.flags |= {PARFLG_UNIQUE}
                    if f.tag == "ParFlg_Hidden":    self.flags |= {PARFLG_HIDDEN}
                    if f.tag == "ParFlg_BoldName":  self.flags |= {PARFLG_BOLDNAME}

        else:  # _Comment
            self.iType = PAR_COMMENT
            self.name = inETree.text
            self.desc = ''
            self.value = None
            self.aVals = None

    @property
    def aVals(self):
        if self._aVals is not None:
            aValue = etree.Element("ArrayValues", FirstDimension=str(self.__fd), SecondDimension=str(self.__sd))
        else:
            return None
        aValue.text = '\n' + 4 * '\t'
        aValue.tail = '\n' + 2 * '\t'

        for rowIdx, row in enumerate(self._aVals):
            for colIdx, cell in enumerate(row):
                if self.__sd:
                    arrayValue = etree.Element("AVal", Column=str(colIdx + 1), Row=str(rowIdx + 1))
                    nTabs = 3 if colIdx == len(row) - 1 and rowIdx == len(self._aVals) - 1 else 4
                else:
                    arrayValue = etree.Element("AVal", Row=str(rowIdx + 1))
                    nTabs = 3 if rowIdx == len(self._aVals) - 1 else 4
                arrayValue.tail = '\n' + nTabs * '\t'
                aValue.append(arrayValue)
                arrayValue.text = self._valueToString(cell)
        return aValue

    @aVals.setter
    def aVals(self, inValues):
        if type(inValues) == etree._Element:
            self.__fd = int(inValues.attrib["FirstDimension"])
            self.__sd = int(inValues.attrib["SecondDimension"])
            if self.__sd > 0:
                self._aVals = [["" for _ in range(self.__sd)] for _ in range(self.__fd)]
                for v in inValues.iter("AVal"):
                    x = int(v.attrib["Column"]) - 1
                    y = int(v.attrib["Row"]) - 1
                    self._aVals[y][x] = self.__toFormat(v.text)
            else:
                self._aVals = [[""] for _ in range(self.__fd)]
                for v in inValues.iter("AVal"):
                    y = int(v.attrib["Row"]) - 1
                    self._aVals[y][0] = self.__toFormat(v.text)
            self.aValsTail = inValues.tail
        elif type(inValues) == list:
            self.__fd = len(inValues)
            self.__sd = len(inValues[0]) if isinstance(inValues[0], list) > 1 else 0

            self._aVals = list( map (self.__toFormat, inValues))
        else:
            self._aVals = None

    @staticmethod
    def getTypeFromString(inString):
        if inString in ("Length"):
            return PAR_LENGTH
        elif inString in ("Angle"):
            return PAR_ANGLE
        elif inString in ("RealNum", "Real"):
            return PAR_REAL
        elif inString in ("Integer"):
            return PAR_INT
        elif inString in ("Boolean"):
            return PAR_BOOL
        elif inString in ("String"):
            return PAR_STRING
        elif inString in ("Material"):
            return PAR_MATERIAL
        elif inString in ("LineType"):
            return PAR_LINETYPE
        elif inString in ("FillPattern"):
            return PAR_FILL
        elif inString in ("PenColor"):
            return PAR_PEN
        elif inString in ("Separator"):
            return PAR_SEPARATOR
        elif inString in ("Title"):
            return PAR_TITLE

# -------------------/parameter classes --------------------------------------------------------------------------------

class BOAPIv2(object):
    """
    Class currently unused
    """
    BROWSER_CLOSE_WINDOW = '''<!DOCTYPE html> 
                            <html> 
                                    <script type="text/javascript"> 
                                        function close_window() { close(); }
                                    </script>
                                <body onload="close_window()"/>
                            </html>'''
    CLIENT_ID = "NL8IZo82T84ZCOruAZom4LlmrzkQFXPW"
    CLIENT_SECRET = "5RNNKjqAAA1szIImP0CO2IFNC6Z8OoBMQeiMKwwoxST7ntSFJhIQKVG1s1DEbLOV"
    REDIRECT_URI = "http://localhost"
    PORT_NUMBER = 80
    MAX_PAGE_NUMBER = 10
    PAGE_MAX_SIZE = 1000
    code = None
    server = None
    brands = {}  # brand permalink-guid

    class myHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            global data
            self.wfile.write(BOAPIv2.BROWSER_CLOSE_WINDOW)
            data = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            BOAPIv2.code = data['code']

            BOAPIv2.server.server_close()


    def __init__(self, inCurrentConfig):
        self.token_type = ""
        self.refresh_token = ""
        self.access_token = ""

        if  inCurrentConfig.has_option("BOAPIv2", "token_type") and \
            inCurrentConfig.has_option("BOAPIv2", "refresh_token"):
            self.token_type = inCurrentConfig.get("BOAPIv2", "token_type")
            self.refresh_token = inCurrentConfig.get("BOAPIv2", "refresh_token")
            self.get_access_token_from_refresh_token()

        if inCurrentConfig.has_option("BOAPIv2", "brands"):
            b = inCurrentConfig.get("BOAPIv2", "brands").split(', ')
            self.brands = {k: v for k, v in zip(b[::2], b[1::2])}


    def refreshBrandDict(self):
        page = 1
        while page < BOAPIv2.MAX_PAGE_NUMBER:
            res = self.get_data_with_access_token("/admin/v1/brands",
                                            {"fields": "permalink, id",
                                             "page": page,
                                             "pageSize": BOAPIv2.PAGE_MAX_SIZE})
            rjson = json.load(res)
            if res.status == http.client.OK:
                for brand in rjson['data'] :
                    self.brands[brand['permalink']] = brand['id']
                if rjson['meta']['hasNextPage']:
                    page += 1
                else:
                    break
            else:
                break

    def getProductData(self, inBrandGUID, inProductPermalink):
        products = self.get_data_with_access_token("/admin/v1/brands/%s/products" % (inBrandGUID, ), {"pageSize": BOAPIv2.PAGE_MAX_SIZE})
        jProd = json.load(products)
        foundData = next((prod for prod in jProd['data'] if prod['permalink'].lower() == inProductPermalink.lower()), None)
        iPage = 1

        while jProd['meta']['hasNextPage'] and not foundData:
            iPage += 1
            products = self.get_data_with_access_token("/admin/v1/brands/%s/products" % (inBrandGUID, ), {'page': iPage,
                                                                                                          "pageSize": BOAPIv2.PAGE_MAX_SIZE})
            jProd = json.load(products)
            foundData = next((prod for prod in jProd['data'] if prod['permalink'].lower() == inProductPermalink.lower()), None)

        productGUID = foundData['id'] if foundData else None

        res = json.load(self.get_data_with_access_token("/admin/v1/brands/%s/products/%s" % (inBrandGUID, productGUID, ), {}))
        return res

        # 1. Logging in with access token

    def get_data_with_access_token(self, inPath, inUrlDict):
        response = self._get_data_with_access_token(inPath, inUrlDict)

        if response.status != http.client.OK:
            self.log_in()
            response = self._get_data_with_access_token(inPath, inUrlDict)
        return response

    def _get_data_with_access_token(self, inPath, inUrlDict):
        conn = http.client.HTTPSConnection("api.bimobject.com")
        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Authorization": self.token_type + " " + self.access_token}
        urlDict = urllib.parse.urlencode(inUrlDict)
        conn.request("GET", inPath + "?" +  urlDict, '', headers)
        return conn.getresponse()

    # 2. If access token doesn't work, try refresh_token
    def get_access_token_from_refresh_token(self):
        conn = http.client.HTTPSConnection("api.bimobject.com")
        urlDict = urllib.parse.urlencode({"client_id": BOAPIv2.CLIENT_ID,
                                    "client_secret": BOAPIv2.CLIENT_SECRET,
                                    "grant_type": "refresh_token",
                                    "refresh_token": self.refresh_token, })
        headers = {"Content-type": "application/x-www-form-urlencoded", }
        conn.request("POST", "/oauth2/token", urlDict, headers)
        response = conn.getresponse()
        if response.status != http.client.OK:
            self.log_in()
        else:
            rjson = json.load(response)
            self.access_token = rjson['access_token']

    # 3. Logging in explicitely
    def log_in(self):
        code_verifier = base64.urlsafe_b64encode(os.urandom(64))
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier).digest()).rstrip(b'=')

        authorizePath = '/identity/connect/authorize'
        urlDict = urllib.parse.urlencode({"client_id": BOAPIv2.CLIENT_ID,
                                    "response_type": "code",
                                    "redirect_uri": BOAPIv2.REDIRECT_URI,
                                    "scope": "admin admin.brand admin.product offline_access",
                                    # "scope"                 : "search_api search_api_downloadbinary",
                                    "code_challenge": code_challenge,
                                    "code_challenge_method": "S256",
                                    "state": "1",
                                    })

        ue = urllib.parse.urlunparse(('https',
                                  'accounts.bimobject.com',
                                  authorizePath,
                                  '',
                                  urlDict,
                                  '',))
        webbrowser.open(ue)
        BOAPIv2.server = http.server.HTTPServer(('', BOAPIv2.PORT_NUMBER), BOAPIv2.myHandler)

        try:
            BOAPIv2.server.serve_forever()
        except IOError:
            pass

        urlDict2 = urllib.parse.urlencode({"client_id": BOAPIv2.CLIENT_ID,
                                     "client_secret": BOAPIv2.CLIENT_SECRET,
                                     "grant_type": "authorization_code",
                                     # "grant_type"       : "client_credentials_for_admin",
                                     "code": BOAPIv2.code,
                                     "code_verifier": code_verifier,
                                     "redirect_uri": BOAPIv2.REDIRECT_URI, })

        # print urlDict2

        headers = {"Content-type": "application/x-www-form-urlencoded", }
        conn = http.client.HTTPSConnection("accounts.bimobject.com")
        conn.request("POST", "/identity/connect/token", urlDict2, headers)
        # conn.request("GET", "/identity/connect/authorize", urlDict2, headers)
        response = conn.getresponse().read()
        print("response: " + response)

        try:
            self.access_token  = json.loads(response)['access_token']
            self.refresh_token = json.loads(response)['refresh_token']
            self.token_type    = json.loads(response)['token_type']
        except KeyError:
            pass

# ------------------- data classes -------------------------------------------------------------------------------------

class GeneralFile(object) :
    """
    basePath:   C:\...\
    fullPath:   C:\...\relPath\fileName.ext  -only for sources; dest stuff can always be modified
    relPath:           relPath\fileName.ext
    dirName            relPath
    fileNameWithExt:           fileName.ext
    name:                      fileName     - for XMLs
    name:                      fileName.ext - for images
    fileNameWithOutExt:        fileName     - for images
    ext:                               .ext

    Inheritances:

                    GeneralFile
                        |
        +---------------+--------------+
        |               |              |
    SourceFile      DestFile        XMLFile
        |               |              |
        |               |              +---------------+
        |               |              |               |
        +-------------- | -------------+               |
        |               |              |               |
        |               +------------- | --------------+
        |               |              |               |
    SourceImage     DestImage       SourceXML       DestXML
    """
    def __init__(self, relPath, **kwargs):
        self.relPath            = relPath
        self.fileNameWithExt    = os.path.basename(relPath)
        self.fileNameWithOutExt = os.path.splitext(self.fileNameWithExt)[0]
        self.ext                = os.path.splitext(self.fileNameWithExt)[1]
        self.dirName            = os.path.dirname(relPath)
        if 'root' in kwargs:
            self.fullPath = os.path.join(kwargs['root'], self.relPath)
            self.fullDirName         = os.path.dirname(self.fullPath)


    # def refreshFileNames(self):
    #     self.fileNameWithExt    = self.name + self.ext
    #     self.fileNameWithOutExt = self.name
    #     self.relPath            = os.path.join(self.dirName, self.fileNameWithExt)
    #
    # def __lt__(self, other):
    #     return self.fileNameWithOutExt < other.name


class SourceFile(GeneralFile):
    def __init__(self, relPath, **kwargs):
        global projectPath
        super(SourceFile, self).__init__(relPath, **kwargs)
        self.fullPath = os.path.join(SOURCE_DIR_NAME, projectPath, relPath)


class DestFile(GeneralFile):
    def __init__(self, fileName, **kwargs):
        super(DestFile, self).__init__(fileName)
        self.sourceFile         = kwargs['sourceFile']
        #FIXME sourcefile multiple times defined in Dest* classes
        self.ext                = self.sourceFile.ext


class SourceImage(SourceFile):
    def __init__(self, sourceFile, **kwargs):
        super(SourceImage, self).__init__(sourceFile, **kwargs)
        self.name = self.fileNameWithExt
        self.isEncodedImage = False


class DestImage(DestFile):
    def __init__(self, sourceFile, stringFrom, stringTo, **kwargs):
        if (not sourceFile.isEncodedImage or not (stringFrom == stringTo == "")) and not "targetFileName" in kwargs:
            self._name               = re.sub(stringFrom, stringTo, sourceFile.name, flags=re.IGNORECASE)
        elif "targetFileName" in kwargs:
            self._name = kwargs["targetFileName"]
        else:
            self._name               = sourceFile.name
        self.sourceFile         = sourceFile
        self.relPath            = os.path.join(sourceFile.dirName, self._name)
        super(DestImage, self).__init__(self.relPath, sourceFile=self.sourceFile)
        self.ext                = self.sourceFile.ext

        if stringTo not in self._name and ADD_STRING and not sourceFile.isEncodedImage:
            self.fileNameWithOutExt = os.path.splitext(self._name)[0] + stringTo
            self._name           = self.fileNameWithOutExt + self.ext
        self.fileNameWithExt = self._name

        self.relPath            = os.path.join(sourceFile.dirName, self._name)
        # super(DestImage, self).__init__(self.relPath, sourceFile=self.sourceFile)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, inName):
        self._name      = inName
        # self.relPath    = self.dirName + "/" + self._name
        self.relPath    = os.path.join(self.dirName, self._name)

    def refreshFileNames(self):
        pass

    #FIXME self.name as @property


class XMLFile(GeneralFile):
    def __init__(self, relPath, **kwargs):
        super(XMLFile, self).__init__(relPath, **kwargs)
        self._name       = self.fileNameWithOutExt
        self.bPlaceable  = False
        self.prevPict    = ''
        self.gdlPicts    = []

    # def __lt__(self, other):
    #     if self.bPlaceable and not other.bPlaceable:
    #         return True
    #     if not self.bPlaceable and other.bPlaceable:
    #         return False
    #     return self._name < other.name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, inName):
        self._name   = inName


class SourceXML (XMLFile, SourceFile):
    def __init__(self, relPath):
        global all_keywords
        super(SourceXML, self).__init__(relPath)
        self.calledMacros   = {}
        self.parentSubTypes = []
        self.scripts        = {}

        mroot = etree.parse(self.fullPath, etree.XMLParser(strip_cdata=False))
        self.iVersion = int(mroot.getroot().attrib['Version'])

        global ID
        if int(self.iVersion) <= AC_18:
            ID = 'UNID'
            self.ID = 'UNID'
        else:
            ID = 'MainGUID'
            self.ID = 'MainGUID'
        self.guid = mroot.getroot().attrib[ID]

        if mroot.getroot().attrib['IsPlaceable'] == 'no':
            self.bPlaceable = False
        else:
            self.bPlaceable = True

        #Filtering params in source in place of dest cos it's feasible and in dest later added params are unused
        # FIXME getting calledmacros' guids.
        # if self.iVersion >= AC_18:
        #     ID = "MainGUID"
        # else:
        #     ID = "UNID"

        for a in mroot.findall("./Ancestry"):
            for ancestryID in a.findall(ID):
                self.parentSubTypes += [ancestryID.text]

        for m in mroot.findall("./CalledMacros/Macro"):
            calledMacroID = m.find(ID).text
            self.calledMacros[calledMacroID] = str.strip(m.find("MName").text, "'" + '"')

        for gdlPict in mroot.findall("./GDLPict"):
            if 'path' in gdlPict.attrib:
                _path = os.path.basename(gdlPict.attrib['path'])
                self.gdlPicts += [_path.upper()]

        #Parameter manipulation: checking usage and later add custom pars
        self.parameters = ParamSection(mroot.find("./ParamSection"))

        for scriptName in SCRIPT_NAMES_LIST:
            script = mroot.find("./%s" % scriptName)
            if script is not None:
                self.scripts[scriptName] = script.text

        # for par in self.parameters:
        #     par.isUsed = self.checkParameterUsage(par, set())
        k = mroot.find("./Keywords")
        if k is not None:
            t = re.sub("\n", ", ", k.text)
            self.keywords = [kw.strip() for kw in t.split(",") if kw != ''][1:-1]
            all_keywords |= set(self.keywords)
        else:
            self.keywords = None

        if self.guid.upper() not in source_guids:
            source_guids[self.guid.upper()] = self.name

        pic = mroot.find("./Picture")
        if pic is not None:
            if "path" in pic.attrib:
                self.prevPict = pic.attrib["path"]

    def checkParameterUsage(self, inPar, inMacroSet):
        """
        Checking whether a certain Parameter is used in the macro or any of its called macros
        :param inPar:       Parameter
        :param inMacroSet:  set of macros that the parameter was searched in before
        :return:        boolean
        """
        #FIXME check parameter passings: a called macro without PARAMETERS ALL
        for script in self.scripts:
            if inPar.name in script:
                return True

        for _, macroName in self.calledMacros.items():
            if macroName in replacement_dict:
                if macroName not in inMacroSet:
                    if replacement_dict[macroName].checkParameterUsage(inPar, inMacroSet):
                        return True
        return False


class DestXML (XMLFile, DestFile):
    # tags            = []      #FIXME later; from BO site

    def __init__(self, sourceFile, stringFrom = "", stringTo = "", **kwargs):
        # Renaming
        if 'targetFileName' in kwargs:
            self.name     = kwargs['targetFileName']
        else:
            self.name     = re.sub(stringFrom, stringTo, sourceFile.name, flags=re.IGNORECASE)
            if stringTo not in self.name and ADD_STRING:
                self.name += stringTo
        if self.name.upper() in dest_dict:
            i = 1
            while self.name.upper() + "_" + str(i) in list(dest_dict.keys()):
                i += 1
            self.name += "_" + str(i)

        self.relPath                = os.path.join(sourceFile.dirName, self.name + sourceFile.ext)

        super(DestXML, self).__init__(self.relPath, sourceFile=sourceFile)
        self.warnings               = []

        self.sourceFile             = sourceFile
        self.guid                   = str(uuid.uuid4()).upper()
        self.bPlaceable             = sourceFile.bPlaceable
        self.iVersion               = sourceFile.iVersion
        self.proDatURL              = ''
        self.bOverWrite             = False
        self.bRetainCalledMacros    = False

        self.parameters             = copy.deepcopy(sourceFile.parameters)

        # fullPath                    = os.path.join(TARGET_XML_DIR_NAME, self.relPath)
        # if os.path.isfile(fullPath):
        #     #for overwriting existing xmls while retaining GUIDs etx
        #     if OVERWRITE:
        #         #FIXME to finish it
        #         self.bOverWrite             = True
        #         self.bRetainCalledMacros    = True
        #         mdp = etree.parse(fullPath, etree.XMLParser(strip_cdata=False))
        #         self.guid = mdp.getroot().attrib[ID]
        #         print(mdp.getroot().attrib[ID])
        #     else:
        #         self.warnings += ["XML Target file exists!"]

        fullGDLPath                 = os.path.join(TARGET_GDL_DIR_NAME, self.fileNameWithOutExt + ".gsm")
        if os.path.isfile(fullGDLPath):
            self.warnings += ["GDL Target file exists!"]

        if self.iVersion >= AC_18:
            # AC18 and over: adding licensing statically
            self.author         = BO_AUTHOR
            self.license        = BO_LICENSE
            self.licneseVersion = BO_LICENSE_VERSION

        if self.sourceFile.guid.upper() not in id_dict:
            # if id_dict[self.sourceFile.guid.upper()] == "":
            id_dict[self.sourceFile.guid.upper()] = self.guid.upper()


class StrippedSourceXML:
    """
    Dummy placeholder class for writing out calledmacros' data for calling (name, guid).
    """
    def __init__(self, inName, inFullPath):
        self.name = inName
        self.fullPath = inFullPath


class StrippedDestXML:
    """
    Dummy placeholder class for writing out calledmacros' data for calling (name, guid).
    """
    def __init__(self, inName, inGUID, inRelPath, inSourceFile):
        self.name = inName
        self.guid = inGUID
        self.relPath = inRelPath
        self.sourceFile = inSourceFile

# -------------------/data classes -------------------------------------------------------------------------------------

def resetAll():
    dest_sourcenames.clear()
    dest_guids.clear()
    source_guids.clear()
    id_dict.clear()
    dest_dict.clear()
    replacement_dict.clear()
    pict_dict.clear()
    source_pict_dict.clear()

    all_keywords.clear()


def scanFolders (inFile, inRootFolder, library_images=False):
    """
    scanning input dir recursively to set up xml and image files' list
    :param inFile:  folder actually to be scanned
    :param outFile: folder at top of hierarchy
    :param library_images: whether we are scanning library_images (for encoded images) or library folder
    :return:
    """
    global projectPath, imagePath

    #FIXME to be rewritten using os.path.walk()
    try:
        for f in listdir(inFile):
            try:
                src = os.path.join(inFile, f)
                # if it's NOT a directory
                if not os.path.isdir(src):
                    if os.path.splitext(os.path.basename(f))[1].upper() in (".XML", ):
                        sf = SourceXML(os.path.relpath(src, inRootFolder))
                        # replacement_dict[sf._name.upper()] = sf
                        replacement_dict[sf.name.upper()] = sf
                    else:
                        # set up replacement dict for other files (not only images, indeed)
                        if os.path.splitext(os.path.basename(f))[0].upper() not in source_pict_dict:
                            sI = SourceImage(os.path.relpath(src, inRootFolder), root=inRootFolder)
                            # SIDN = os.path.join(SOURCE_DIR_NAME, imagePath)
                            # if SIDN in sI.fullDirName:
                            #     sI.isEncodedImage = True
                            source_pict_dict[sI.fileNameWithExt.upper()] = sI
                            sI.isEncodedImage = library_images
                else:
                    scanFolders(src, inRootFolder, library_images=library_images)
            except KeyError:
                print("KeyError %s" % f)
                continue
    except WindowsError:
        pass


def addImageFile(fileName, **kwargs):
    global family_name
    if not fileName.upper() in pict_dict:
        target_name = family_name
        if "main_version" in kwargs:
            target_name = kwargs["main_version"]
        destItem = DestImage(source_pict_dict[fileName.upper()], WMCC_BRAND_NAME, target_name, **kwargs)
        pict_dict[destItem.fileNameWithExt.upper()] = destItem


def addFile(sourceFileName, **kwargs):
    global family_name
    if sourceFileName.upper() in replacement_dict:
        target_name = family_name
        if "main_version" in kwargs:
            target_name = kwargs["main_version"]
        destItem = DestXML(replacement_dict[sourceFileName.upper()], WMCC_BRAND_NAME, target_name, **kwargs)
        dest_dict[destItem.name.upper()] = destItem
        dest_guids[destItem.guid] = destItem
        dest_sourcenames[destItem.sourceFile.name.upper()] = destItem
    else:
        #FIXME File should be in library_additional, possibly worth of checking it or add a warning
        print("Warning: %s not in replacement_dict" % sourceFileName)
        return
    return destItem


def addAllFiles():
    for filename in replacement_dict:
        addFile(filename)

    for imageFileName in source_pict_dict:
        addImageFile(imageFileName)


def addFileRecursively(sourceFileName='', **kwargs):
        destItem = addFile(sourceFileName, **kwargs)

        if sourceFileName.upper() not in replacement_dict:
            #should be in library_additional
            return

        x = replacement_dict[sourceFileName.upper()]

        for k, v in x.calledMacros.items():
            if v.upper() not in dest_sourcenames:
                addFileRecursively(v)

        for parentGUID in x.parentSubTypes:
            if parentGUID not in id_dict:
                if parentGUID in source_guids:
                    addFileRecursively(source_guids[parentGUID])

        for pict in source_pict_dict.values():
            for script in x.scripts.values():
                if pict.fileNameWithExt.upper() in script or pict.fileNameWithOutExt.upper() in script.upper():
                    addImageFile(pict.fileNameWithExt)
            if pict.fileNameWithExt.upper() in x.gdlPicts:
                addImageFile(pict.fileNameWithExt)

        if x.prevPict:
            bN = os.path.basename(x.prevPict)
            addImageFile(bN)

        if 'targetFileName' in kwargs:
            destItem.name = kwargs['targetFileName']

        return destItem


def addFileUsingMacroset(inFile, in_dest_dict, **kwargs):
    global dest_dict

    dest_dict.update(in_dest_dict)

    destItem = addFile(inFile, **kwargs)

    return destItem


def createLCF(tempGDLDirName, fileNameWithoutExtension):
    '''
    Builds up an LCF from a set of Folders
    :return:
    '''
    global projectPath

    source_image_dir_name = os.path.join(SOURCE_DIR_NAME, projectPath, "library_images")
    if not os.path.exists(source_image_dir_name):
        source_image_dir_name = ""
    else:
        source_image_dir_name = '"' + source_image_dir_name + '"'

    output = r'"%s" createcontainer "%s" "%s" %s "%s"' % (os.path.join(ARCHICAD_LOCATION, 'LP_XMLConverter.exe'), os.path.join(TARGET_GDL_DIR_NAME, fileNameWithoutExtension + '.lcf'), tempGDLDirName, source_image_dir_name, ADDITIONAL_IMAGE_DIR_NAME)
    print("output: %s" % output)

    logging.info("createcontainer")
    with Popen(output, stdout=PIPE, stderr=PIPE, stdin=DEVNULL) as proc:
        _out, _err = proc.communicate()
        logging.info(f"Success: {_out} (error: {_err}) ")

    # check_output(output, shell=True)

    print("*****LCF CREATION FINISHED SUCCESFULLY******")


def unitConvert(inParameterName,
                inParameterValue,
                inTranslationLib, ):
    """
    Converts source units into destination units
    #FIXME
    :param inParameter:
    :param inTranslation:
    :inFirstPosition:   position if in array
    :inSecondPosition:  position if in array
    :return:            float; NOT string
    """
    _UnitLib = {"m": 1,
                "cm": 0.01,
                "mm" : 0.001}

    if type(inParameterValue) == list:
        return [unitConvert(inParameterName, par, inTranslationLib) for par in inParameterValue]

    if "Measurement" in inTranslationLib['parameters'][inParameterName]:
        if "Measurement" in inTranslationLib['parameters'][inParameterName]["ARCHICAD"]:
            return float(inParameterValue) * _UnitLib[inTranslationLib['parameters'][inParameterName]["Measurement"]] / \
                   _UnitLib[inTranslationLib['parameters'][inParameterName]["ARCHICAD"]["Measurement"]]
    elif inParameterName in {"Inner frame material",
                             "Outer frame material",
                             "Glazing",
                             "Available inner frame materials",
                             "Available outer frame materials",
                             }:
        return inParameterValue + "_" + family_name
    else:
        return inParameterValue


def extractParams(inData):
    global projectPath
    projectPath = inData["path"] if "path" in inData else ""
    sf = SourceXML(inData["fileName"])
    return sf.parameters.returnParamsAsDict()


def createMasterGDL(**kwargs):
    """
    Creates master.gdl script with the only content currently:
    -file_dependence for material macros
    -call for materials for being able to be seen in attributes
    :return:
    """
    content = ""
    colorList = [c for c in kwargs["surfaces"]] if "surfaces" in kwargs else []

    if colorList:
        content += '\n\tcall "' + '"\n\tcall "'.join([c + '" parameters  sSurfaceName = "' + c for c in colorList]) + '"'

    if colorList or False:
        #FIXME later to add other dependencies, like profile and composite definitions
        content += '\n\nfile_dependence \\\n\t"'
        content += '",\n\t"'.join(colorList) + '"'

    return content


def buildMacroSet(inData, main_version="19"):
    '''
    :inFolderS: a list of foleder names to go through to build up macros
    :return:
    '''
    global projectPath, imagePath

    if "main_version" in inData:
        main_version = inData["main_version"]

    minor_version = datetime.date.today().strftime("%Y%m%d")
    if "minor_version" in inData:
        minor_version = inData["minor_version"]

    projectPath = inData["path"] if "path" in inData else ""
    imagePath = inData["imagePath"] if "imagePath" in inData else ""

    resetAll()

    source_xml_dir_name = os.path.join(SOURCE_DIR_NAME, projectPath)
    source_image_dir_name = os.path.join(SOURCE_DIR_NAME, imagePath) if imagePath else ""
    if source_image_dir_name:
        scanFolders(source_image_dir_name, source_image_dir_name, library_images=True)

    # --------------------------------------------------------

    for rootFolder in inData['folder_names']:
        scanFolders(os.path.join(source_xml_dir_name, rootFolder), source_xml_dir_name, library_images=False)

        for folder, subFolderS, fileS in os.walk(os.path.join(source_xml_dir_name, rootFolder)):
            for file in fileS:
                if os.path.splitext(file)[1].upper() == ".XML":
                    if os.path.splitext(file)[0].upper() not in dest_dict:
                        addFile(os.path.splitext(file)[0], main_version=main_version)
                else:
                    addImageFile(file, main_version=main_version)

        if source_image_dir_name:
            for folder, subFolderS, fileS in os.walk(source_image_dir_name):
                for file in fileS:
                    addImageFile(file, main_version=main_version)

    if "LIBRARY_VERSION_WMCC" in dest_sourcenames:
        dest_sourcenames["LIBRARY_VERSION_WMCC"].parameters["iVersionLibrary"] = minor_version

    tempGDLDirName = tempfile.mkdtemp()

    print("tempGDLDirName: %s" % tempGDLDirName)

    startConversion(targetGDLDirName = tempGDLDirName, sourceImageDirName=source_image_dir_name)

    _fileNameWithoutExtension = "macroset_" + inData["category"] + "_" + main_version

    createLCF(tempGDLDirName, _fileNameWithoutExtension + "_" + str(minor_version))

    _stripped_dest_dict = {}

    for k, v in dest_dict.items():
        # dest_dict[k].sourceFile.scripts = None
        _sourceFile = StrippedSourceXML(v.sourceFile.name, v.sourceFile.fullPath, )
        _stripped_dest_dict[k] = StrippedDestXML(v.name, v.guid, v.relPath, _sourceFile, )

    jsonPathName = os.path.join(TARGET_GDL_DIR_NAME, _fileNameWithoutExtension + ".json")
    jsonData = jsonpickle.encode({  "minor_version": str(minor_version),
                                    "objects": _stripped_dest_dict}, )

    with open(jsonPathName, "w") as file:
        file.write(jsonData)

    if CLEANUP:
        os.rmdir(tempGDLDirName)

    return {'LCFName': _fileNameWithoutExtension + ".json"}


def createBrandedProduct(inData):
    """
    creates branded product's lcf based on macroset's into a json file(like macroset_200130.json) extracted names/guids
    :param inData:    JSON
    :return:
    """
    global dest_sourcenames, family_name, projectPath, imagePath, dest_dict

    resetAll()
    family_name = inData["family_name"]
    tempGDLDirName = os.path.join(tempfile.mkdtemp(), family_name)
    logging.info("tempGDLDirName: %s" % tempGDLDirName)

    projectPath = inData["path"]
    imagePath = inData["imagePath"] if "imagePath" in inData else projectPath
    source_image_dir_name = os.path.join(SOURCE_DIR_NAME, projectPath, "library_images")
    source_xml_dir_name = os.path.join(SOURCE_DIR_NAME, projectPath)

    scanFolders(source_xml_dir_name, source_xml_dir_name, library_images=False)
    scanFolders(source_image_dir_name, source_image_dir_name, library_images=True)
    # --------------------------------------------------------
    if 'materials' in inData:
        addFileRecursively("Glass", targetFileName="Glass" + "_" + family_name)

    JSONFileName = "macroset_" + inData["category"] + "_" + inData["main_macroset_version"] + ".json"
    with open(TRANSLATIONS_JSON, "r") as translatorJSON:
        translation = json.loads(translatorJSON.read())

        # ------ surfaces ------
        #FIXME organize it into a factory class
        availableMaterials = []
        for material in inData['materials']:
            availableMaterials += [material["material_name"] + "_" + family_name]
            materialMacro = addFile(MATERIAL_BASE_OBJECT,
                                    targetFileName=material["material_name"] + "_" + family_name)

            for parameter in material['parameters']:
                translatedParameter = translation["parameters"][parameter]['ARCHICAD']["Name"]
                materialMacro.parameters[translatedParameter] = unitConvert(
                    parameter,
                    material['parameters'][parameter],
                    translation
                )
            materialMacro.parameters["sSurfaceName"] = material["material_name"] + "_" + family_name

            # --------- textures -----------
            if ('texture_name' in material) and ('base64_encoded_texture' in material):
                if not os.path.exists(os.path.join(tempGDLDirName, 'surfaces')):
                    os.makedirs(os.path.join(tempGDLDirName, 'surfaces'))
                with open(os.path.join(tempGDLDirName, 'surfaces', material['texture_name']), 'wb') as textureFile:
                    textureFile.write(base64.urlsafe_b64decode(material['base64_encoded_texture']))
                materialMacro.parameters['sTextureName'] = os.path.splitext(material['texture_name'])[0]

        # ------ placeables ------

        placeableS = []

        inputJson = jsonpickle.decode(open(os.path.join(TARGET_GDL_DIR_NAME, JSONFileName)).read())
        _dest_dict = inputJson["objects"]
        dest_dict.update(_dest_dict)
        dest_sourcenames = {d.sourceFile.name.upper(): d for d in dest_dict.values()}

        for family in inData['family_types']:
            sourceFile = family["source_file"]
            destItem = addFileUsingMacroset(sourceFile, dest_dict,
                                            targetFileName=family["type_name"])

            placeableS.append(destItem.name)

            if 'parameters' in family:
                for _i in range(14):
                    destItem.parameters["sMaterialValS"][_i] = availableMaterials + ["Glass_" + family_name]

                destItem.parameters["sMaterialS"] = [[availableMaterials[0]] for _ in destItem.parameters["sMaterialS"]]
                destItem.parameters["iVersionNumber"][1] = [int(inData["minimum_required_macroset_version"]), 0]

                for parameter in family['parameters']:
                    translatedParameter = translation["parameters"][parameter]['ARCHICAD']["Name"]
                    if "FirstPosition" in translation["parameters"][parameter]['ARCHICAD']:
                        firstPosition = translation["parameters"][parameter]['ARCHICAD']["FirstPosition"]

                        if "SecondPosition" in translation["parameters"][parameter]['ARCHICAD']:
                            secondPosition = translation["parameters"][parameter]['ARCHICAD']["SecondPosition"]

                            destItem.parameters[translatedParameter][firstPosition][secondPosition] = unitConvert(
                                parameter,
                                family['parameters'][parameter],
                                translation)
                        else:
                            destItem.parameters[translatedParameter][firstPosition] = unitConvert(
                                parameter,
                                family['parameters'][parameter],
                                translation)
                    else:
                        destItem.parameters[translatedParameter] = unitConvert(
                            parameter,
                            family['parameters'][parameter],
                            translation)

    # For now:
    # --------------------------------------------------------

    startConversion(targetGDLDirName=tempGDLDirName)

    if availableMaterials:
        masterGDL = createMasterGDL(surfaces=availableMaterials)
        with open(os.path.join(tempGDLDirName, "surfaces", "master_gdl_%s.gdl" % family_name), "w") as f:
            f.write(masterGDL)

    fileName = inData["category"] + "_" + family_name

    createLCF(tempGDLDirName, fileName)

    _paceableName = fileName + ".lcf"
    _macrosetName = 'macroset' + "_" + inData["category"] + "_" + inData["main_macroset_version"] + "_" + inputJson["minor_version"] + ".lcf"
    uploadFinishedObject(_paceableName, _macrosetName,
                         inData["webhook_url"] if "webhook_url" in inData else "127.0.0.1",
                         inData["webhook_path"] if "webhook_path" in inData else "/setfile" )

    if CLEANUP:
        os.rmdir(tempGDLDirName)
    os.remove(os.path.join(TARGET_GDL_DIR_NAME, _paceableName))

    return {"placeables": placeableS,
            "materials": availableMaterials,
            "macroSet": _macrosetName}


def uploadFinishedObject(inFileName,
                         inMacrosetName,
                         inWebhook_url="127.0.0.1" ,
                         inWebhook_path = "/setfile",
                         inPORT=5000):
    """
    Uploads finished objects by calling a webhook with a POST message
    FIXME doing it by using a blob storage
    """
    with open(os.path.join(TARGET_GDL_DIR_NAME, inFileName), "rb") as file:
        _fileData = base64.urlsafe_b64encode(file.read()).decode("utf-8")
        _macrosetData = base64.urlsafe_b64encode(file.read()).decode("utf-8")

        urlDict = json.dumps({"object_name": inFileName,
                              "base64_encoded_object": _fileData,
                              "macroset_name": inMacrosetName,
                              "base64_encoded_macroset": _macrosetData,
                              })

        headers = {"Content-type": "application/json", }
        conn = http.client.HTTPConnection(inWebhook_url, port=inPORT)
        conn.request("POST", inWebhook_path, urlDict, headers)
        response = conn.getresponse().read()
        logging.info(f"response: {response}")


def startConversion(targetGDLDirName = TARGET_GDL_DIR_NAME, sourceImageDirName=''):
    """
    :return:
    """
    # tempdir = os.path.join(tempfile.mkdtemp(), "library")
    tempdir = tempfile.mkdtemp()
    tempPicDir = tempfile.mkdtemp()

    logging.debug("tempdir: %s" % tempdir)
    logging.debug("tempPicDir: %s" % tempPicDir)

    pool_map = [{"dest": dest_dict[k],
                 "tempdir": tempdir,
                 "projectPath": projectPath,
                 "dest_sourcenames": dest_sourcenames,
                 "pict_dict": pict_dict,
                 "dest_dict": dest_dict,
                 "family_name": family_name,
                 } for k in dest_dict.keys() if isinstance(dest_dict[k], DestXML)]
    _pool = mp.Pool()
    _pool.map(processOneXML, pool_map)

    _picdir =  ADDITIONAL_IMAGE_DIR_NAME

    dirs_to_delete = set()
    if _picdir:
        for f in listdir(_picdir):
            dirs_to_delete |= {f}
            shutil.copytree(os.path.join(_picdir, f), os.path.join(tempPicDir, f))

    for f in list(pict_dict.keys()):
        if pict_dict[f].sourceFile.isEncodedImage:
            try:
                shutil.copyfile(os.path.join(sourceImageDirName, pict_dict[f].sourceFile.relPath), os.path.join(tempPicDir, pict_dict[f].relPath))
            except IOError:
                os.makedirs(os.path.join(tempPicDir, pict_dict[f].dirName))
                shutil.copyfile(os.path.join(sourceImageDirName, pict_dict[f].sourceFile.relPath), os.path.join(tempPicDir, pict_dict[f].relPath))
        else:
            try:
                shutil.copyfile(pict_dict[f].sourceFile.fullPath, os.path.join(targetGDLDirName, pict_dict[f].relPath))
            except IOError:
                os.makedirs(os.path.join(targetGDLDirName, pict_dict[f].dirName))
                shutil.copyfile(pict_dict[f].sourceFile.fullPath, os.path.join(targetGDLDirName, pict_dict[f].relPath))

    x2lCommand = '"%s" x2l -img "%s" "%s" "%s"' % (os.path.join(ARCHICAD_LOCATION, 'LP_XMLConverter.exe'), tempPicDir, tempdir, targetGDLDirName)
    logging.info(r"x2l Command being executed...\n%s" % x2lCommand)

    if DEBUG:
        logging.debug("ac command:")
        logging.debug(x2lCommand)
        with open(tempdir + "\dict.txt", "w") as d:
            for k in list(dest_dict.keys()):
                d.write(k + " " + dest_dict[k].sourceFile.name + "->" + dest_dict[k].name + " " + dest_dict[k].sourceFile.guid + " -> " + dest_dict[k].guid + "\n")

        with open(tempdir + "\pict_dict.txt", "w") as d:
            for k in list(pict_dict.keys()):
                d.write(pict_dict[k].sourceFile.fullPath + "->" + pict_dict[k].relPath+ "\n")

        with open(tempdir + "\id_dict.txt", "w") as d:
            for k in list(id_dict.keys()):
                d.write(id_dict[k] + "\n")

    logging.info("x2l")
    with Popen(x2lCommand, stdout=PIPE, stderr=PIPE, stdin=DEVNULL) as proc:
        _out, _err = proc.communicate()
        logging.info(f"Success: {_out} (error: {_err}) ")

    # cleanup ops
    if CLEANUP:
        if _picdir:
            for d in dirs_to_delete:
                shutil.rmtree(os.path.join(tempPicDir, d))
        if not OUTPUT_XML:
            shutil.rmtree(tempdir)
    else:
        logging.debug("tempdir: %s" % tempdir)
        logging.debug("tempPicDir: %s" % tempPicDir)

    logging.info("*****GSM CREATION FINISHED SUCCESFULLY******")


def processOneXML(inData):
    dest = inData['dest']
    tempdir = inData["tempdir"]
    projectPath = inData["projectPath"]
    dest_sourcenames = inData["dest_sourcenames"]
    dest_dict = inData["dest_dict"]
    pict_dict = inData["pict_dict"]
    family_name = inData["family_name"]

    src = dest.sourceFile
    srcPath = src.fullPath
    destPath = os.path.join(tempdir, dest.relPath)
    destDir = os.path.dirname(destPath)

    print("%s -> %s" % (srcPath, destPath,))

    mdp = etree.parse(srcPath, etree.XMLParser(strip_cdata=False))
    mdp.getroot().attrib[dest.sourceFile.ID] = dest.guid
    _calledMacroSet = set()

    for m in mdp.findall("./CalledMacros/Macro"):
        key = str.strip(m.find("MName").text, "'" + '"')
        try:
            d = dest_sourcenames[key.upper()]
            # for dI in list(dest_dict.keys()):
            #     d = dest_dict[dI]
            #     if  str.strip(m.find("MName").text, "'" + '"')  == d.sourceFile.name:
            m.find("MName").text = etree.CDATA('"' + d.name + '"')
            m.find(dest.sourceFile.ID).text = d.guid
            _calledMacroSet.add(d.name.upper())
        except KeyError:
            if not os.path.exists(os.path.join(SOURCE_DIR_NAME, projectPath, "library_additional", key + ".gsm")):
                print("Missing called macro: %s (Might be in library_additional, called by: %s)" % (key, src.name,))

    for sect in ["./Script_2D", "./Script_3D", "./Script_1D", "./Script_PR", "./Script_UI", "./Script_VL",
                 "./Script_FWM", "./Script_BWM", ]:
        section = mdp.find(sect)
        if section is not None:
            t = section.text
            for dI in _calledMacroSet:
                t = re.sub(dest_dict[dI].sourceFile.name, dest_dict[dI].name, t, flags=re.IGNORECASE)
                # t = ireplace(dest_dict[dI].sourceFile.name, dest_dict[dI].name, t)

            for pr in sorted(pict_dict.keys(), key=lambda x: -len(x)):
                # Replacing images
                fromRE = pict_dict[pr].sourceFile.fileNameWithOutExt
                if family_name:
                    fromRE += '(?!' + family_name + ')'
                t = re.sub(fromRE, pict_dict[pr].fileNameWithOutExt, t, flags=re.IGNORECASE)

                # t = ireplace(pict_dict[pr].sourceFile.fileNameWithOutExt, pict_dict[pr].fileNameWithOutExt, t)

            section.text = etree.CDATA(t)

    if dest.bPlaceable:
        section = mdp.find('Picture')
        if isinstance(section, etree._Element) and 'path' in section.attrib:
            path = os.path.basename(section.attrib['path']).upper()
            if path:
                n = next((pict_dict[p].relPath for p in list(pict_dict.keys()) if
                          os.path.basename(pict_dict[p].sourceFile.relPath).upper() == path), None)
                if n:
                    section.attrib['path'] = os.path.join(os.path.dirname(n), os.path.basename(n))

    if dest.iVersion >= AC_18:
        for cr in mdp.getroot().findall("Copyright"):
            mdp.getroot().remove(cr)

        eCopyright = etree.Element("Copyright", SectVersion="1", SectionFlags="0", SubIdent="0")
        eAuthor = etree.Element("Author")
        eCopyright.append(eAuthor)
        eAuthor.text = dest.author

        eLicense = etree.Element("License")
        eCopyright.append(eLicense)

        eLType = etree.Element("Type")
        eLicense.append(eLType)
        eLType.text = dest.license

        eLVersion = etree.Element("Version")
        eLicense.append(eLVersion)

        eLVersion.text = dest.licneseVersion

        mdp.getroot().append(eCopyright)

    # ---------------------BO_update---------------------
    parRoot = mdp.find("./ParamSection")
    parPar = parRoot.getparent()
    parPar.remove(parRoot)

    destPar = dest.parameters.toEtree()
    parPar.append(destPar)

    # ---------------------Ancestries--------------------

    # FIXME not clear, check, writes an extra empty mainunid field
    # FIXME ancestries to be used in param checking
    # FIXME this is unclear what id does
    for m in mdp.findall("./Ancestry/" + dest.sourceFile.ID):
        guid = m.text
        if guid.upper() in id_dict:
            print("ANCESTRY: %s" % guid)
            par = m.getparent()
            par.remove(m)

            element = etree.Element(dest.sourceFile.ID)
            element.text = id_dict[guid]
            element.tail = '\n'
            par.append(element)
    try:
        os.makedirs(destDir)
    except WindowsError:
        pass
    with open(destPath, "wb") as file_handle:
        file_handle.write(etree.tostring(mdp, pretty_print=True, encoding="UTF-8", ))
