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
                _out = proc.stdout.read()
                return f"{_out}"
        except OSError as ex:
            return f"BaseException: {ex.__class__.__name__} {ex.__str__()} {ex.errno} {ex.strerror} {ex.filename} {ex.filename2}"

try:
    from subprocess import check_output, Popen, PIPE, run, DEVNULL
    # from PIL import Image
    # from lxml import etree
finally:
    api.add_resource(TestEngine, '/')


if __name__ == '__main__':
    app.run(debug=True)