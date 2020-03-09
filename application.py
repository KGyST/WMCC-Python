import os.path
# from os import listdir
# import uuid
# import re
# import tempfile
# import shutil
# import datetime
# import jsonpickle
# import multiprocessing as mp
#
# import copy
# import argparse
#
# import urllib.request, urllib.parse, urllib.error, json, urllib.parse, os, base64
# import http.client
# import io

import time

e = None

from flask import Flask, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

class TestEngine(Resource):
    def get(self):
        try:
            # return " ".join([a[0] for a in os.walk(".")])

            _p = run(" ".join([os.path.join("src", "archicad", "LP_XMLConverter_18", "LP_XMLConverter.EXE"), "help"]))
            # _res = _p.stderr
            return {"test": "samu %d" % _p.returncode}
        except OSError as ee:
            print("OSError")
            return {"OSError": "OSError %s" % " ".join([str(a) for a in ee.args])}
        except BaseException as ee:
            return {"test": "BaseException"}

try:
    from subprocess import check_output, Popen, PIPE, run
    print("test")
    # from PIL import Image
    # from lxml import etree
except BaseException as ex:
    e = ex
    print(e.__class__.__name__)
finally:
    api.add_resource(TestEngine, '/')


if __name__ == '__main__':
    app.run(debug=True)