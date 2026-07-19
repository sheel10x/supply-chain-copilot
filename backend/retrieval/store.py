import os
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from rank_bm25 import BM25Okapi

class RetrievalStore:
    def __init__(self, index_name: str = "rfp-analyzer-gemini"):
        self.pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
        self.index_name = index_name
        
        # Initialize Embeddings (Google Gemini API - instant, no RAM usage)
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY is missing! You must add it to your Render dashboard to use fast embeddings.")
            
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", 
            google_api_key=gemini_api_key
        )
        self.dimension = 768 # dimension of text-embedding-004
        
        # Ensure Pinecone index exists
        self._ensure_index()
        self.index = self.pc.Index(self.index_name)
        
        # In-memory BM25 store (for a production app, this would be persisted or in Postgres)
        self.bm25: Optional[BM25Okapi] = None
        self.document_chunks: List[Dict[str, Any]] = []

    def _ensure_index(self):
        if self.index_name not in self.pc.list_indexes().names():
            print(f"Creating Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1" # Using default free tier region
                )
            )

    def upsert_chunks(self, chunks: List[Dict[str, Any]], namespace: str = "default"):
        """
        Upserts chunks into Pinecone (Vector) and BM25 (Keyword).
        """
        if not chunks:
            return
            
        vectors = []
        texts_for_bm25 = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"chunk_{i}"
            text = chunk.get("text", "")
            metadata = chunk.get("metadata", {})
            
            # Text is stored in metadata for retrieval
            metadata["text"] = text 
            
            # Pinecone does not accept None/null values in metadata
            clean_metadata = {k: v for k, v in metadata.items() if v is not None}
            
            # 1. Prepare for Pinecone
            embedding = self.embeddings.embed_query(text)
            vectors.append((chunk_id, embedding, clean_metadata))
            
            # 2. Prepare for BM25
            self.document_chunks.append(chunk)
            # Simple tokenization for BM25
            texts_for_bm25.append(text.lower().split())

        print(f"Upserting {len(vectors)} vectors into Pinecone...")
        self.index.upsert(vectors=vectors, namespace=namespace)
        
        print(f"Building BM25 index for {len(texts_for_bm25)} chunks...")
        self.bm25 = BM25Okapi(texts_for_bm25)

    def hybrid_search(self, query: str, top_k: int = 5, namespace: str = "default") -> List[Dict[str, Any]]:
        """
        Performs vector search + keyword search and merges results using Reciprocal Rank Fusion (RRF).
        """
        if not self.bm25 or not self.document_chunks:
            print("Warning: Store is empty. Call upsert_chunks first.")
            return []
            
        # 1. Vector Search
        query_embedding = self.embeddings.embed_query(query)
        vector_results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            namespace=namespace
        )
        
        # 2. BM25 Search
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k indices from BM25
        top_bm25_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]
        
        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[str, float] = {}
        k_rrf = 60 # standard RRF constant
        
        # Add vector ranks
        for rank, match in enumerate(vector_results.matches):
            chunk_id = match.id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k_rrf + rank + 1)
            
        # Add BM25 ranks
        for rank, idx in enumerate(top_bm25_indices):
            chunk_id = f"chunk_{idx}"
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k_rrf + rank + 1)
            
        # Sort by combined RRF score
        sorted_chunks = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        
        # 4. Format Output
        final_results = []
        for chunk_id, score in sorted_chunks:
            # We can pull the full text/metadata from our local document_chunks 
            # (or from Pinecone metadata if preferred)
            idx = int(chunk_id.split("_")[1])
            final_results.append({
                "chunk": self.document_chunks[idx],
                "score": score
            })
            
        return final_results
