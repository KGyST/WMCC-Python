from src.WMCC import APP_CONFIG, buildMacroSet
import os
import json
import datetime
import logging
import shutil

# Test builds test_cats and moves them to
TEST  = bool(int(os.environ['TEST'])) if "TEST" in os.environ else False
TEST_CATS = ["tests", ]
CLEANUP = False
ONLY_CAT    = os.environ["ONLY_CAT"] if "ONLY_CAT" in os.environ else None

if "CONTENT_DIR_NAME" in os.environ:
    CONTENT_DIR_NAME = os.environ["CONTENT_DIR_NAME"]
else:
    with open(APP_CONFIG, "r") as ac:
        appJSON = json.load(ac)

        CONTENT_DIR_NAME = appJSON["CONTENT_DIR_NAME"]

CATEGORY_DATA_JSON          = os.path.join(CONTENT_DIR_NAME, "categoryData.json")

data = {}

with open(CATEGORY_DATA_JSON, "r") as cD:
    categoryData = json.load(cD)
    del categoryData["commons"]

    for cat in categoryData:
        #TEST == (cat in TEST_CATS) and ()
        if cat == ONLY_CAT or not ONLY_CAT:
            logging.info(f"Building category: {cat}")
            print(f"Building category: {cat}")
            data["category"] = cat

            category = categoryData[cat]
            for mV in category:
                mainVersion = category[mV]
                data["main_version"] = mV
                data["minor_version"] = datetime.date.today().strftime("%Y%m%d")
                data['path'] = mainVersion["macro_folders"]

                result = buildMacroSet(data)

                for macroFolder in mainVersion["macro_folders"]:
                    _macroFolderPath = os.path.join(CONTENT_DIR_NAME, macroFolder)
                    if TEST:
                        shutil.copytree(_macroFolderPath, os.path.join(CONTENT_DIR_NAME, os.path.dirname(macroFolder), "_" + os.path.basename(macroFolder)))

                    if CLEANUP:
                        shutil.rmtree(_macroFolderPath)
                        print(f"Removed macro folder: {_macroFolderPath}")

                    if TEST:
                        shutil.move(os.path.join(CONTENT_DIR_NAME, os.path.dirname(macroFolder), "_" + os.path.basename(macroFolder)),
                                    _macroFolderPath)
        else:
            print(f"Not built category: {cat}")

