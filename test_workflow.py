import urllib.request
import json
import ssl

def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print("--- Creating Conversation ---")
    req = urllib.request.Request(
        'http://localhost:8000/api/v1/conversations/',
        data=json.dumps({"title": "Test Chat"}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req, context=ctx)
    conv = json.loads(resp.read().decode())
    print("Response:", json.dumps(conv, indent=2))
    
    conv_id = conv['id']

    print(f"\n--- Sending Message to {conv_id} ---")
    req2 = urllib.request.Request(
        f'http://localhost:8000/api/v1/conversations/{conv_id}/messages',
        data=json.dumps({"message": "Hello!"}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    try:
        resp2 = urllib.request.urlopen(req2, context=ctx)
        print("Response stream:")
        while True:
            chunk = resp2.readline()
            if not chunk:
                break
            print(chunk.decode().strip())
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code} - {e.read().decode()}")

if __name__ == "__main__":
    main()
