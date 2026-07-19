import os
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from ingestion.parser import RFPParser
from ingestion.chunker import RFPChunker
from retrieval.store import RetrievalStore
from agents.pipeline import AgentPipeline

load_dotenv()

app = FastAPI(
    title="RFQ Analyzer API",
    description="3-agent RAG backend: Extract → Normalize → Compare",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    # --- Comparison Details Form Fields ---
    run_name: str = Form(default="Default Run"),
    description: str = Form(default=""),
    purpose: str = Form(default=""),
    key_features: str = Form(default="Price, Delivery, Technical Specs, Certifications"),
    additional_considerations: str = Form(default=""),
    baseline_criteria: str = Form(default="")
):
    """
    Accepts an uploaded RFQ/RFP document and comparison details,
    runs it through the full 3-agent pipeline:
      Agent 1 — Generic RFQ Extraction
      Agent 2 — Unit Normalization
      Agent 3 — Comparison vs. Baseline
    """
    try:
        # 1. Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # 2. Ingestion Phase — Parse & Chunk
        parser = RFPParser()
        chunker = RFPChunker()
        raw_json = await parser.parse_document(tmp_path)
        chunks = chunker.chunk_document(raw_json)
        print(f"Ingested {len(chunks)} chunks from '{file.filename}'")

        # 3. Vector Store Upsert (for hybrid search / RAG)
        store = RetrievalStore()
        store.upsert_chunks(chunks)

        # 4. Agent Pipeline
        pipeline = AgentPipeline()

        # Agent 1: Extract all RFQ fields
        extracted_data = await pipeline.run_extraction(chunks)

        # Agent 2: Normalize units (metric/imperial, currency, etc.)
        normalization_report = await pipeline.run_normalization(extracted_data)

        # Build baseline string — combine user-supplied baseline with purpose/description
        full_baseline = baseline_criteria
        if purpose:
            full_baseline = f"Purpose: {purpose}\n\n{full_baseline}"
        if description:
            full_baseline = f"Description: {description}\n\n{full_baseline}"

        # Agent 3: Compare normalized data vs. buyer's baseline criteria
        comparison_report = await pipeline.run_comparison(
            extracted_data=extracted_data,
            normalization_report=normalization_report,
            run_name=run_name,
            baseline_criteria=full_baseline,
            key_features=key_features,
            additional_considerations=additional_considerations
        )

        # Clean up temp file
        os.unlink(tmp_path)

        return {
            "status": "success",
            "chunks": len(chunks),
            "data": {
                "extraction": extracted_data.model_dump(),
                "normalization": normalization_report.model_dump(),
                "comparison": comparison_report.model_dump()
            }
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
