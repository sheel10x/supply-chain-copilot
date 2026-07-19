from pydantic import BaseModel, Field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Agent 1 — Generic RFQ Extraction
# ---------------------------------------------------------------------------

class RFQHeader(BaseModel):
    rfq_reference_number: Optional[str] = Field(default="Not Provided")
    issue_date: Optional[str] = Field(default="Not Provided")
    submission_deadline: Optional[str] = Field(default="Not Provided")
    question_deadline: Optional[str] = Field(default="Not Provided")
    buyer_company: Optional[str] = Field(default="Not Provided")
    buyer_contact: Optional[str] = Field(default="Not Provided")

class LineItem(BaseModel):
    description: str
    part_number: Optional[str] = Field(default="Not Provided")
    quantity: Optional[str] = Field(default="Not Provided")
    unit: Optional[str] = Field(default="Not Provided")
    unit_price: Optional[str] = Field(default="Not Provided")
    total_price: Optional[str] = Field(default="Not Provided")
    pricing_basis: Optional[str] = Field(default="Not Provided")

class TechnicalSpec(BaseModel):
    parameter: str = Field(description="e.g. Material Grade, Voltage, Pressure, Thickness")
    value: str     = Field(description="The extracted value as stated in the document")

class ExtractedRFQData(BaseModel):
    vendor_name: str
    header: RFQHeader
    line_items: List[LineItem]
    technical_specs: List[TechnicalSpec]
    delivery_location: Optional[str] = Field(default="Not Provided")
    required_delivery_date: Optional[str] = Field(default="Not Provided")
    lead_time: Optional[str] = Field(default="Not Provided")
    payment_terms: Optional[str] = Field(default="Not Provided")
    incoterms: Optional[str] = Field(default="Not Provided")
    price_validity: Optional[str] = Field(default="Not Provided")
    evaluation_criteria: Optional[str] = Field(default="Not Provided")
    certifications: List[str] = Field(default_factory=list)

# ---------------------------------------------------------------------------
# Agent 2 — Unit Normalization
# ---------------------------------------------------------------------------

class NormalizationNote(BaseModel):
    field: str            = Field(description="Which field/parameter was normalized")
    original: str         = Field(description="The original extracted value with unit")
    normalized: str       = Field(description="The normalized value with unit")
    conversion_note: str  = Field(description="Explanation e.g. '2 inches -> 50.8 mm'")

class NormalizationReport(BaseModel):
    vendor_name: str
    notes: List[NormalizationNote]
    normalized_specs: List[TechnicalSpec] = Field(
        description="The technical_specs list after normalization has been applied"
    )

# ---------------------------------------------------------------------------
# Agent 3 — Comparison vs. User Baseline
# ---------------------------------------------------------------------------

class ComparisonItem(BaseModel):
    feature: str         = Field(description="The feature/requirement being compared")
    baseline_value: str  = Field(description="What the buyer required")
    vendor_value: str    = Field(description="What the vendor offered (normalized if applicable)")
    status: str          = Field(description="Must be one of: match, deviation, missing")
    notes: str           = Field(description="Brief explanation of the match or gap")

class ComparisonReport(BaseModel):
    vendor_name: str
    run_name: str
    comparison_items: List[ComparisonItem]
    overall_summary: str = Field(description="A 2-3 sentence executive summary of the comparison")
