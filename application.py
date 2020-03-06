import os.path
from os import listdir
import uuid
import re
import tempfile
from subprocess import check_output
import shutil
import datetime
import jsonpickle
import multiprocessing as mp

import copy
import argparse

import urllib.request, urllib.parse, urllib.error, json, urllib.parse, os, base64
import http.client

from PIL import Image
import io

# from lxml import etree

from flask import Flask, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

class TestEngine(Resource):
    def get(self):
        return {"test": "samu"}

api.add_resource(TestEngine, '/')

if __name__ == '__main__':
    app.run(debug=True)