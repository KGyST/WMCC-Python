import WMCC
import os
import json
import datetime
import logging

TEST  = bool(os.environ['TEST']) if "TEST" in os.environ else False

if "CONTENT_DIR_NAME" in os.environ:
    CONTENT_DIR_NAME = os.environ["CONTENT_DIR_NAME"]
else:
    with open(WMCC.APP_CONFIG, "r") as ac:
        appJSON                     = json.load(ac)
        CONTENT_DIR_NAME            = appJSON["CONTENT_DIR_NAME"]

CATEGORY_DATA_JSON          = os.path.join(CONTENT_DIR_NAME, "categoryData.json")

data = {}

with open(CATEGORY_DATA_JSON, "r") as cD:
    categoryData = json.load(cD)

    for cat in categoryData:
        if TEST == (cat in ("tests", )):
            logging.info(f"Building category: {cat}")
            data["category"] = cat

            category = categoryData[cat]
            for mV in category:
                mainVersion = category[mV]
                data["main_version"] = mV
                data["minor_version"] = datetime.date.today().strftime("%Y%m%d")
                data['path'] = mainVersion["macro_folders"]

            result = WMCC.buildMacroSet(data)

