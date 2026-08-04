import urllib.request
from urllib.error import HTTPError
import json
import uuid
import time

# 1. Upload
boundary = uuid.uuid4().hex
body = f'--{boundary}\r\nContent-Disposition: form-data; name="title"\r\n\r\nTest Document\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.txt"\r\nContent-Type: text/plain\r\n\r\nHello World {uuid.uuid4().hex}\r\n--{boundary}--\r\n'.encode('utf-8')

req = urllib.request.Request('http://localhost:8000/api/v1/documents/', method='POST', data=body)
req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
doc_id = result.get('id') or result.get('existing_document_id')
print('Uploaded doc:', doc_id)

time.sleep(1)
method, url = 'GET', f'http://localhost:8000/api/v1/documents/{doc_id}/download'
try:
    req = urllib.request.Request(url, method=method)
    resp = urllib.request.urlopen(req)
    print(method, url, 'SUCCESS:', resp.getcode())
except HTTPError as e:
    print(method, url, 'FAILED:', e.code, e.read())

time.sleep(3) # Wait for processing to complete

method, url = 'POST', f'http://localhost:8000/api/v1/documents/{doc_id}/reindex'
try:
    req = urllib.request.Request(url, method=method, data=b'')
    resp = urllib.request.urlopen(req)
    print(method, url, 'SUCCESS:', resp.getcode())
except HTTPError as e:
    print(method, url, 'FAILED:', e.code, e.read())

method, url = 'DELETE', f'http://localhost:8000/api/v1/documents/{doc_id}'
try:
    req = urllib.request.Request(url, method=method)
    resp = urllib.request.urlopen(req)
    print(method, url, 'SUCCESS:', resp.getcode())
except HTTPError as e:
    print(method, url, 'FAILED:', e.code, e.read())
