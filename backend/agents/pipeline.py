import os
import json
from typing import List, Dict, Any
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from pydantic import ValidationError

from agents.schemas import ExtractedRFQData, NormalizationReport, ComparisonReport


class AgentPipeline:
    def __init__(self):
        groq_api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not groq_api_key:
            print("Warning: GROQ_API_KEY is missing.")

        self.llm = ChatGroq(
            temperature=0,
            model_name="llama-3.3-70b-versatile",
            api_key=groq_api_key,
            model_kwargs={"response_format": {"type": "json_object"}},
            max_retries=1
        )

    # ------------------------------------------------------------------
    # Agent 1 — Generic RFQ Extraction
    # ------------------------------------------------------------------
    async def run_extraction(self, chunks: List[Dict[str, Any]]) -> ExtractedRFQData:
        """
        Step 1: Systematic Extraction
        Reads all document chunks and extracts every mandatory RFQ data point.
        Missing fields are explicitly marked "Not Provided".
        """
        context = "\n\n".join([chunk.get("text", "") for chunk in chunks])

        prompt = PromptTemplate.from_template(
            "You are an expert Procurement Analyst and Data Extraction system.\n\n"
            "## TASK — Step 1: Systematic Extraction\n"
            "Analyze the provided RFQ document and extract the following mandatory data points.\n"
            "If any information is missing, explicitly set the value to the string 'Not Provided'.\n\n"
            "### Categories to extract:\n"
            "1. **Header & Tracking**: RFQ Reference Number, Issue Date, Question Deadline, "
            "Submission Deadline, Buyer Company, Buyer Contact.\n"
            "2. **Specifications & Requirements**: Item descriptions, part numbers, quantities, "
            "technical standards (material grades, dimensions, tolerances, ISO certifications).\n"
            "3. **Delivery & Logistics**: Exact delivery location/address, required delivery date, lead time.\n"
            "4. **Pricing / Bill of Quantities**: Unit price, total price, additional costs "
            "(shipping, installation, taxes), price validity period.\n"
            "5. **Terms, Conditions & Evaluation Criteria**: Payment terms, Incoterms, "
            "evaluation criteria (price, delivery time, quality, etc.), required certifications.\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n{schema}\n\n"
            "RFQ Document Text:\n{context}\n\nJSON Output:"
        )

        chain = prompt | self.llm
        print("Running Agent 1 — RFQ Extraction...")

        res = await chain.ainvoke({
            "schema": json.dumps(ExtractedRFQData.model_json_schema(), indent=2),
            "context": context
        })

        try:
            parsed_json = json.loads(res.content)
            return ExtractedRFQData(**parsed_json)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Agent 1 (Extraction) failed validation: {e}")
            raise e

    # ------------------------------------------------------------------
    # Agent 2 — Unit Normalization
    # ------------------------------------------------------------------
    async def run_normalization(self, extracted_data: ExtractedRFQData) -> NormalizationReport:
        """
        Step 2: Unit Normalization
        Checks for unit differences (Metric vs. Imperial, currencies, quantities)
        and converts all values to the baseline standard units.
        """
        prompt = PromptTemplate.from_template(
            "You are an expert Procurement Analyst and unit normalization system.\n\n"
            "## TASK — Step 2: Unit Normalization\n"
            "Review all extracted technical specs, quantities, and pricing from the RFQ data below.\n"
            "Identify any values that use non-standard or mixed units and convert them.\n\n"
            "### Normalization Rules:\n"
            "- Dimensions: normalize to **millimeters (mm)**\n"
            "- Weight/Mass: normalize to **kilograms (kg)** or **metric tons (MT)**\n"
            "- Pressure: normalize to **MPa**\n"
            "- Temperature: normalize to **Celsius (°C)**\n"
            "- Currency: normalize to **USD**\n"
            "- Quantities: normalize to individual units (not cases/pallets) where applicable\n\n"
            "For each conversion, record:\n"
            "  - `field`: which field was normalized\n"
            "  - `original`: the original value with its unit\n"
            "  - `normalized`: the converted value with the new unit\n"
            "  - `conversion_note`: brief explanation e.g. '2 inches -> 50.8 mm'\n\n"
            "Also produce `normalized_specs`: the full technical_specs list after normalization.\n"
            "If no conversion was needed for a spec, include it unchanged.\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n{schema}\n\n"
            "Extracted RFQ Data:\n{extracted_data}\n\nJSON Output:"
        )

        chain = prompt | self.llm
        print("Running Agent 2 — Unit Normalization...")

        res = await chain.ainvoke({
            "schema": json.dumps(NormalizationReport.model_json_schema(), indent=2),
            "extracted_data": extracted_data.model_dump_json(indent=2)
        })

        try:
            parsed_json = json.loads(res.content)
            # Ensure vendor_name is carried forward
            parsed_json.setdefault("vendor_name", extracted_data.vendor_name)
            return NormalizationReport(**parsed_json)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Agent 2 (Normalization) failed validation: {e}")
            raise e

    # ------------------------------------------------------------------
    # Agent 3 — Comparison vs. Baseline
    # ------------------------------------------------------------------
    async def run_comparison(
        self,
        extracted_data: ExtractedRFQData,
        normalization_report: NormalizationReport,
        run_name: str,
        baseline_criteria: str,
        key_features: str = "",
        additional_considerations: str = ""
    ) -> ComparisonReport:
        """
        Step 3: Comparison & Analysis
        Compares normalized RFQ data against the buyer's baseline criteria.
        Highlights matches, flags deviations and missing requirements.
        """
        prompt = PromptTemplate.from_template(
            "You are an expert Procurement Auditor performing a structured comparison.\n\n"
            "## TASK — Step 3: Comparison & Analysis\n"
            "Using the normalized RFQ data, compare every field against the Baseline Criteria.\n\n"
            "### Comparison Run: {run_name}\n"
            "### Key Features to Compare:\n{key_features}\n"
            "### Additional Considerations:\n{additional_considerations}\n\n"
            "### Status Rules (use EXACTLY one of these values):\n"
            "  - `match`    — vendor value meets or exceeds the baseline requirement\n"
            "  - `deviation` — vendor value differs from the baseline (flag the difference)\n"
            "  - `missing`  — requirement not addressed by the vendor at all\n\n"
            "For each comparison item, clearly state:\n"
            "  - `feature`: the requirement being evaluated\n"
            "  - `baseline_value`: what the buyer requires\n"
            "  - `vendor_value`: what the vendor offers (normalized)\n"
            "  - `status`: match / deviation / missing\n"
            "  - `notes`: brief explanation of the finding\n\n"
            "End with an `overall_summary` (2-3 sentences) as an executive summary.\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n{schema}\n\n"
            "### Baseline Criteria:\n{baseline_criteria}\n\n"
            "### Normalized Vendor Data:\n{vendor_data}\n\n"
            "### Unit Normalization Notes:\n{normalization_notes}\n\nJSON Output:"
        )

        chain = prompt | self.llm
        print("Running Agent 3 — Baseline Comparison...")

        normalization_notes = "\n".join([
            f"- {n.field}: {n.conversion_note}"
            for n in normalization_report.notes
        ]) or "No unit conversions were required."

        res = await chain.ainvoke({
            "schema": json.dumps(ComparisonReport.model_json_schema(), indent=2),
            "run_name": run_name,
            "key_features": key_features or "Price, Delivery, Technical Specs, Certifications",
            "additional_considerations": additional_considerations or "None",
            "baseline_criteria": baseline_criteria,
            "vendor_data": extracted_data.model_dump_json(indent=2),
            "normalization_notes": normalization_notes
        })

        try:
            parsed_json = json.loads(res.content)
            parsed_json.setdefault("vendor_name", extracted_data.vendor_name)
            parsed_json.setdefault("run_name", run_name)
            return ComparisonReport(**parsed_json)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Agent 3 (Comparison) failed validation: {e}")
            raise e
