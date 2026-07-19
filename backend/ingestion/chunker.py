from typing import List, Dict, Any
import re

class RFPChunker:
    def __init__(self):
        # We will split on common Markdown headers (##, ###, etc.)
        self.header_pattern = re.compile(r'^(#{1,6})\s+(.*)$', re.MULTILINE)

    def chunk_document(self, json_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes LlamaParse JSON output and chunks it by headers/sections.
        Preserves page number and bounding box metadata for the chunk.
        
        Note: The exact structure of LlamaParse JSON varies by version. 
        Usually, it is a list of pages. Each page has 'text' (the markdown) 
        and optionally 'items' with bounding boxes.
        """
        chunks = []
        current_chunk = {
            "text": "",
            "metadata": {
                "headers": [],
                "page": None,
                "bbox": None
            }
        }
        
        # Handle LlamaParse's nested structure
        pages = []
        if isinstance(json_data, list) and len(json_data) > 0 and "pages" in json_data[0]:
            pages = json_data[0]["pages"]
        else:
            # Fallback if structure changes
            pages = json_data if isinstance(json_data, list) else []
            
        for page_obj in pages:
            page_num = page_obj.get("page", 0)
            page_text = page_obj.get("md", page_obj.get("text", ""))
            
            # Simple header-based splitting logic
            # This is a basic implementation. For production, we'd map bounding boxes
            # from `page_obj.get('items', [])` to these text segments.
            
            lines = page_text.split('\n')
            for line in lines:
                match = self.header_pattern.match(line)
                if match:
                    # If we hit a new header and current chunk has text, save it
                    if current_chunk["text"].strip():
                        chunks.append(current_chunk)
                    
                    header_level = len(match.group(1))
                    header_text = match.group(2).strip()
                    
                    # Start new chunk
                    current_chunk = {
                        "text": line + "\n",
                        "metadata": {
                            "headers": [header_text],
                            "page": page_num,
                            # Placeholder for actual bbox logic which requires mapping 
                            # text offset to LlamaParse item coordinates
                            "bbox": page_obj.get("bbox", None) 
                        }
                    }
                else:
                    # Append to current chunk
                    current_chunk["text"] += line + "\n"
                    # If page isn't set for this chunk yet, set it to current page
                    if current_chunk["metadata"]["page"] is None:
                        current_chunk["metadata"]["page"] = page_num
                        
        # Append the last chunk
        if current_chunk["text"].strip():
            chunks.append(current_chunk)
            
        return chunks
