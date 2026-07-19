import os
import json
import hashlib
from typing import List, Dict, Any
from pathlib import Path
from llama_parse import LlamaParse

# We'll store parsed cache in a local directory to avoid hitting LlamaParse API repeatedly
CACHE_DIR = Path(os.path.dirname(__file__)).parent / "data" / "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

class RFPParser:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("LLAMA_CLOUD_API_KEY")
        if not self.api_key:
            raise ValueError("LLAMA_CLOUD_API_KEY is missing! You must add it to your Render dashboard Environment Variables for the backend.")
            
        # Initialize LlamaParse
        # Note: LlamaParse premium tier might require `premium_mode=True` or similar.
        self.parser = LlamaParse(
            api_key=self.api_key,
            result_type="markdown",
            # We want layout mode to preserve tables/headers
            # Depending on the exact version, this might be the default for markdown, 
            # but we explicitly set verbose to track progress.
            verbose=True
        )

    def _get_cache_path(self, file_path: str) -> Path:
        """Generate a unique cache filename based on the file content hash."""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return CACHE_DIR / f"{hasher.hexdigest()}.json"

    async def parse_document(self, file_path: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Parses a document (PDF) and returns structured markdown chunks.
        Saves to disk to prevent re-parsing.
        """
        cache_path = self._get_cache_path(file_path)
        
        if use_cache and cache_path.exists():
            print(f"Loading cached parse result from {cache_path}")
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        print(f"Parsing document {file_path} via LlamaParse...")
        # LlamaParse get_json() returns rich metadata including bounding boxes
        # We use a synchronous call or async call depending on version. 
        # get_json is highly recommended for bounding boxes.
        try:
            # We'll fetch the JSON representation to get page/bbox metadata.
            json_result = await self.parser.aget_json(file_path)
            
            # Save raw result to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(json_result, f, indent=2)
                
            return json_result
            
        except Exception as e:
            print(f"Error during LlamaParse execution: {e}")
            raise e
