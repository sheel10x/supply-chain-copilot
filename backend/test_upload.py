import requests
import json
from pathlib import Path

pdf_path = Path(__file__).parent.parent / "samples" / "Vendor_A_GreatLakesMetalSupply_Proposal.pdf"
with open(pdf_path, "rb") as f:
    files = {'file': ('Vendor_A_GreatLakesMetalSupply_Proposal.pdf', f, 'application/pdf')}
    response = requests.post("http://127.0.0.1:8000/ingest", files=files)
    
print(response.status_code)
print(json.dumps(response.json(), indent=2))
