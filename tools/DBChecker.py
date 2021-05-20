import pymongo

import argparse

CONNECTION_STRING = "mongodb+srv://template_writer:t0LMjZrGIB71ao5o@archos-ezw4q.azure.mongodb.net/test?authSource=admin&replicaSet=Archos-shard-0&readPreference=primary&appname=MongoDB%20Compass&ssl=true"
DB_NAME = 'archos'
TEMPLATE_TABLE_NAME = 'templates'
BIMPRODUCT_TABLE_NAME = 'bimProducts'

client = pymongo.MongoClient(CONNECTION_STRING)

db = client[DB_NAME]
res = {str(t['_id']) for t in db[TEMPLATE_TABLE_NAME].find({})}

_i = 1
for p in db[BIMPRODUCT_TABLE_NAME].find({'brandId': "4615f3ed-6ea8-45bb-8a4e-b72b6545e613"}):
    if str(p['templateId']) not in res:
        print (_i)
        # pprint.pprint(p)
        print(str(p['templateId']))
        print(str(p['_id']))
        _i += 1
