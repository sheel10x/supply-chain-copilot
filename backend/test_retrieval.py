import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from ingestion.chunker import RFPChunker
from retrieval.store import RetrievalStore

def test_retrieval():
    # Load previously cached JSON from LlamaParse
    cache_file = Path(__file__).parent / "data" / "cache" / "175b894fc471b4ac19f0a55e85929ee0.json"
    
    if not cache_file.exists():
        print("Cache file not found. Run test_ingestion.py first.")
        return
        
    with open(cache_file, "r", encoding="utf-8") as f:
        raw_json = json.load(f)
        
    # Chunk
    chunker = RFPChunker()
    chunks = chunker.chunk_document(raw_json)
    
    print(f"Loaded and chunked into {len(chunks)} chunks.")
    
    # Init store
    store = RetrievalStore()
    
    # Upsert
    store.upsert_chunks(chunks)
    
    # Search
    query = "What is the price for 5052 Aluminum sheet?"
    print(f"\nQuerying: '{query}'")
    results = store.hybrid_search(query, top_k=2)
    
    for i, res in enumerate(results):
        print(f"\n--- Result {i+1} (Score: {res['score']:.4f}) ---")
        print(res["chunk"]["text"][:300] + "...")

if __name__ == "__main__":
    test_retrieval()
