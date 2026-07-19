import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load env vars from the root .env file
load_dotenv(Path(__file__).parent.parent / ".env")

from ingestion.parser import RFPParser
from ingestion.chunker import RFPChunker

async def test_ingest():
    pdf_path = Path(__file__).parent.parent / "samples" / "Vendor_A_GreatLakesMetalSupply_Proposal.pdf"
    
    parser = RFPParser()
    chunker = RFPChunker()
    
    print(f"Parsing: {pdf_path}")
    
    # 1. Parse Document
    try:
        raw_json = await parser.parse_document(str(pdf_path))
        print(f"Successfully parsed document. Got {len(raw_json)} pages/items from LlamaParse.")
    except Exception as e:
        print(f"Failed to parse document: {e}")
        return
        
    # 2. Chunk Document
    try:
        chunks = chunker.chunk_document(raw_json)
        print(f"Successfully chunked into {len(chunks)} chunks.")
        
        # Save output for manual inspection
        output_path = Path(__file__).parent / "ingestion_test_output.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2)
            
        print(f"Saved chunk preview to {output_path}")
    except Exception as e:
        print(f"Failed to chunk document: {e}")

if __name__ == "__main__":
    asyncio.run(test_ingest())
