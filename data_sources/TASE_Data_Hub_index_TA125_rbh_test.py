# -*- coding: utf-8 -*-
import http.client
import requests
import json

conn = http.client.HTTPSConnection("datawise.tase.co.il")

headers = {
    'accept': "application/json",
    'accept-language': "he-IL",
    'apikey': "0acd9c29-5514-42fe-978e-41ff565b09e1"
    }

conn.request("GET", "/v1/basic-indices/index-components-basic/137/2025/12/1", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))
data_dict = json.loads(data)
print(data_dict)