import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from agents.pipeline import AgentPipeline

BASELINE_CRITERIA = """
1. Vendor must supply Cold-Rolled Steel coil (ASTM A1008 CS Type B).
2. Steel must have min. yield of 280 MPa.
3. Aluminum 5052-H32 ASTM B209 required.
4. Aluminum defect rate must be under 0.5%.
5. On-time delivery rate must be >95%.
6. Must have ISO 14001 certification.
7. Must provide EN 10204 Type 3.1 MTC.
"""


async def test_agents():
    chunks_file = Path(__file__).parent / "ingestion_test_output.json"

    if not chunks_file.exists():
        print("Chunks file not found. Run test_ingestion.py first.")
        return

    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    pipeline = AgentPipeline()

    print("\n" + "=" * 50)
    print("AGENT 1 — RFQ EXTRACTION")
    print("=" * 50)
    extracted_data = await pipeline.run_extraction(chunks)
    print(extracted_data.model_dump_json(indent=2))

    print("\n" + "=" * 50)
    print("AGENT 2 — UNIT NORMALIZATION")
    print("=" * 50)
    normalization_report = await pipeline.run_normalization(extracted_data)
    print(normalization_report.model_dump_json(indent=2))

    print("\n" + "=" * 50)
    print("AGENT 3 — COMPARISON VS. BASELINE")
    print("=" * 50)
    comparison_report = await pipeline.run_comparison(
        extracted_data=extracted_data,
        normalization_report=normalization_report,
        run_name="Test Run Q3-2026",
        baseline_criteria=BASELINE_CRITERIA,
        key_features="Material Grade, Yield Strength, Defect Rate, Delivery Rate, Certifications",
        additional_considerations="Prefer vendors with ISO 14001 and EN 10204 Type 3.1 MTC"
    )
    print(comparison_report.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(test_agents())
