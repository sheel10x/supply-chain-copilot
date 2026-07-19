import requests
import json

files = {'file': ('test.pdf', b'%PDF-1.4\n...', 'application/pdf')}
response = requests.post("http://127.0.0.1:8000/ingest", files=files)
print(response.status_code)
print(response.json())
