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

e = None

from flask import Flask, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

class TestEngine(Resource):
    def get(self):
        try:
            with Popen(" ".join([os.path.join("archicad", "LP_XMLConverter_18", "LP_XMLConverter.EXE"), "help"]), stdout=PIPE, encoding='utf-8') as _p:
                _res = _p.stdout.readlines()
                return {"test": "samu %s" % e.__class__.__name__} if e else _res
        except OSError as ee:
            return {"test": "samu %s" % " ".join([a for a in ee.args])}
        except BaseException as ee:
            return {"BaseException": ee.__class__.__name__}
        finally:
            return {"finally": "finally"}

try:
    from subprocess import check_output, Popen, PIPE
    # from PIL import Image
    # from lxml import etree
except BaseException as ex:
    e = ex
    print(e.__class__.__name__)
finally:
    api.add_resource(TestEngine, '/')


if __name__ == '__main__':
    app.run(debug=True)