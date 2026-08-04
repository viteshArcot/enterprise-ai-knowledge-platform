import urllib.request, urllib.error, json, os
with open('dummy.txt', 'wb') as f: f.write(b'duplicate test content')

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = (f'--{boundary}\r\n'
        'Content-Disposition: form-data; name=\"file\"; filename=\"dummy.txt\"\r\n'
        'Content-Type: text/plain\r\n\r\n'
        'duplicate test content\r\n'
        f'--{boundary}--\r\n').encode('utf-8')

req1 = urllib.request.Request('http://localhost:8000/api/v1/documents/', data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
try:
    resp1 = urllib.request.urlopen(req1)
    print('First upload:', resp1.status, json.loads(resp1.read().decode()))
except urllib.error.HTTPError as e:
    print('First upload error:', e.code, e.read().decode())

req2 = urllib.request.Request('http://localhost:8000/api/v1/documents/', data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
try:
    resp2 = urllib.request.urlopen(req2)
    print('Second upload:', resp2.status, json.loads(resp2.read().decode()))
except urllib.error.HTTPError as e:
    print('Second upload error:', e.code, e.read().decode())
