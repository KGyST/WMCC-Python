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

from flask import Flask, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

class TestEngine(Resource):
    def get(self):
        try:
            with Popen([os.path.join("src", "archicad", "LP_XMLConverter_18", "LP_XMLConverter.EXE"), "help"], stdout=PIPE, stderr=PIPE, stdin=DEVNULL) as proc:
                _ret = proc.communicate()
                # _out = proc.stdout
                # _err = proc.stdout
                # _ret = proc.returncode
                return f"v4 Success: {_ret[0]} (error: {_ret[1]}) "
        except OSError as ex:
            return f"OSError: {ex.__class__.__name__} {ex.__str__()} {ex.errno} {ex.strerror} {ex.filename} {ex.filename2}"
        except BaseException as ex:
            return f"v4 BaseException: {ex.__class__.__name__} {ex.__str__()}"

try:
    from subprocess import check_output, Popen, PIPE, run, DEVNULL
    # from PIL import Image
    # from lxml import etree
finally:
    api.add_resource(TestEngine, '/')


if __name__ == '__main__':
    app.run(debug=True)