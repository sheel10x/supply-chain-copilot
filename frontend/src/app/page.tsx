"use client";

import { useState, useRef } from "react";
import {
  FileText, Package, GitCompareArrows, DollarSign,
  ShieldCheck, Upload, CheckCircle2, XCircle, AlertCircle,
  Loader2, X, Award, Truck, CreditCard, Clock,
  MapPin, Tag, BarChart3, Home, Settings, Mail, Grid, User, LayoutDashboard, Search, Bell, Info, ArrowUpRight, ArrowDownRight, TrendingUp, Download, ArrowRight, Zap, RefreshCw, ArrowRightLeft
} from "lucide-react";

// ═══════════════════════════════════════════════════════════════════
// TYPES — Mirror backend Pydantic schemas
// ═══════════════════════════════════════════════════════════════════

interface RFQHeader {
  rfq_reference_number: string;
  issue_date: string;
  submission_deadline: string;
  question_deadline: string;
  buyer_company: string;
  buyer_contact: string;
}

interface LineItem {
  description: string;
  part_number: string;
  quantity: string;
  unit: string;
  unit_price: string;
  total_price: string;
  pricing_basis: string;
}

interface TechnicalSpec {
  parameter: string;
  value: string;
}

interface ExtractedRFQData {
  vendor_name: string;
  header: RFQHeader;
  line_items: LineItem[];
  technical_specs: TechnicalSpec[];
  delivery_location: string;
  required_delivery_date: string;
  lead_time: string;
  payment_terms: string;
  incoterms: string;
  price_validity: string;
  evaluation_criteria: string;
  certifications: string[];
}

interface NormalizationNote {
  field: string;
  original: string;
  normalized: string;
  conversion_note: string;
}

interface NormalizationReport {
  vendor_name: string;
  notes: NormalizationNote[];
  normalized_specs: TechnicalSpec[];
}

interface ComparisonItem {
  feature: string;
  baseline_value: string;
  vendor_value: string;
  status: "match" | "deviation" | "missing";
  notes: string;
}

interface ComparisonReport {
  vendor_name: string;
  run_name: string;
  comparison_items: ComparisonItem[];
  overall_summary: string;
}

interface AnalysisResult {
  extraction: ExtractedRFQData;
  normalization: NormalizationReport;
  comparison: ComparisonReport;
}

// ═══════════════════════════════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════════════════════════════

function Toast({ message, type, onClose }: { message: string; type: "success" | "error" | "loading"; onClose: () => void }) {
  return (
    <div className={`toast toast-${type}`}>
      <div className="toast-icon">
        {type === "success" && <CheckCircle2 size={20} />}
        {type === "error"   && <XCircle size={20} />}
        {type === "loading" && <Loader2 size={20} className="animate-spin" />}
      </div>
      <span className="toast-msg">{message}</span>
      {type !== "loading" && (
        <button className="toast-close" onClick={onClose}><X size={16} /></button>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// EMPTY STATE
// ═══════════════════════════════════════════════════════════════════

function EmptyState({ tab }: { tab: string }) {
  return (
    <div className="empty-state animate-fade-in">
      <Upload size={48} color="var(--border-light)" style={{ margin: "0 auto 16px" }} />
      <h2 style={{ marginBottom: "8px", color: "var(--text-primary)" }}>No data available</h2>
      <p style={{ color: "var(--text-secondary)" }}>
        Upload an RFQ/RFP PDF using the button in the top right to view <strong>{tab}</strong> data.
      </p>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// INFO FIELD RENDERER
// ═══════════════════════════════════════════════════════════════════

function InfoField({ label, value }: { label: string; value: string | undefined }) {
  const displayValue = value && value !== "Not Provided" ? value : "Not Provided";
  const isNotProvided = displayValue === "Not Provided";
  return (
    <div className="info-item">
      <span className="info-label">{label}</span>
      <span className={`info-value ${isNotProvided ? "not-provided" : ""}`} style={{ opacity: isNotProvided ? 0.4 : 1 }}>
        {displayValue}
      </span>
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "match": return <CheckCircle2 size={14} />;
    case "deviation": return <AlertCircle size={14} />;
    case "missing": return <XCircle size={14} />;
    default: return <AlertCircle size={14} />;
  }
}

// ═══════════════════════════════════════════════════════════════════
// MAIN DASHBOARD
// ═══════════════════════════════════════════════════════════════════

export default function Dashboard() {
  const [activeTab, setActiveTab]       = useState("Overview");
  const [isUploading, setIsUploading]   = useState(false);
  const [toast, setToast]               = useState<{ message: string; type: "success" | "error" | "loading" } | null>(null);
  const [result, setResult]             = useState<AnalysisResult | null>(null);
  const [history, setHistory]           = useState<AnalysisResult[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Modal state
  const [showModal, setShowModal]       = useState(false);
  const [pendingFile, setPendingFile]   = useState<File | null>(null);
  const [formData, setFormData]         = useState({
    run_name: "",
    description: "",
    purpose: "",
    key_features: "Price, Delivery, Technical Specs, Certifications",
    additional_considerations: "",
    baseline_criteria: ""
  });

  const tabs = [
    { name: "Overview",       icon: <BarChart3 size={16} /> },
    { name: "Extraction",     icon: <FileText size={16} /> },
    { name: "Comparison",     icon: <GitCompareArrows size={16} /> },
    { name: "Pricing",        icon: <DollarSign size={16} /> },
  ];

  const showToast = (message: string, type: "success" | "error" | "loading") => {
    setToast({ message, type });
    if (type !== "loading") {
      setTimeout(() => setToast(null), 5000);
    }
  };

  const handleUploadClick = () => fileInputRef.current?.click();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setPendingFile(file);
    setShowModal(true);
  };

  const handleModalClose = () => {
    setShowModal(false);
    setPendingFile(null);
  };

  const handleRunAnalysis = async () => {
    if (!pendingFile) return;
    setShowModal(false);
    setIsUploading(true);
    showToast(`Uploading "${pendingFile.name}" and running 3-agent analysis...`, "loading");

    const body = new FormData();
    body.append("file", pendingFile);
    body.append("run_name",       formData.run_name || "Default Run");
    body.append("description",    formData.description);
    body.append("purpose",        formData.purpose);
    body.append("key_features",   formData.key_features);
    body.append("additional_considerations", formData.additional_considerations);
    body.append("baseline_criteria",         formData.baseline_criteria);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/ingest`, {
        method: "POST",
        body,
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}: ${res.statusText}`);
      const raw = await res.json();
      if (raw.status !== "success") throw new Error(raw.message || "Unknown error from server");

      const d = raw.data;
      const newResult = {
        extraction:    d.extraction    as ExtractedRFQData,
        normalization: d.normalization as NormalizationReport,
        comparison:    d.comparison    as ComparisonReport,
      };
      setResult(newResult);
      setHistory(prev => [newResult, ...prev]);
      showToast(`Analysis complete for "${d.extraction?.vendor_name || pendingFile.name}"`, "success");
      setActiveTab("Comparison");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to upload. Is the backend running?";
      showToast(message, "error");
    } finally {
      setIsUploading(false);
      setPendingFile(null);
    }
  };

  // Derived Stats
  const matchCount     = result ? result.comparison.comparison_items.filter(i => i.status === "match").length : 0;
  const deviationCount = result ? result.comparison.comparison_items.filter(i => i.status === "deviation").length : 0;
  const missingCount   = result ? result.comparison.comparison_items.filter(i => i.status === "missing").length : 0;
  const totalItems     = result ? result.comparison.comparison_items.length : 0;
  const compliancePct  = totalItems > 0 ? Math.round((matchCount / totalItems) * 100) : 0;

  const uniqueVendors = new Set(history.map(r => r.extraction.vendor_name)).size;

  return (
    <div className="dashboard-theme">
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

      {/* ─────────────────────────────────────────────────────────────────
          MODAL
          ───────────────────────────────────────────────────────────────── */}
      {showModal && pendingFile && (
        <div className="modal-overlay" onClick={handleModalClose}>
          <div className="modal-panel" onClick={e => e.stopPropagation()}>
            <div className="section-header-box" style={{ marginBottom: "16px" }}>
              <h2 className="modal-title">Comparison Details</h2>
              <button className="modal-close" onClick={handleModalClose}><X size={20} /></button>
            </div>
            
            <div className="info-item" style={{ marginBottom: "24px", display: "flex", alignItems: "center", gap: "10px" }}>
              <FileText size={20} color="var(--accent-blue)" />
              <span style={{ fontWeight: 600 }}>{pendingFile.name}</span>
            </div>

            <div style={{ display: "grid", gap: "16px" }}>
              <div>
                <label className="form-label">Run name</label>
                <input className="form-input" placeholder="e.g. Q3 Server Hardware" value={formData.run_name} onChange={e => setFormData(f => ({ ...f, run_name: e.target.value }))} />
              </div>
              <div>
                <label className="form-label">Description</label>
                <textarea className="form-textarea" placeholder="Brief description of the items being compared" rows={2} value={formData.description} onChange={e => setFormData(f => ({ ...f, description: e.target.value }))} />
              </div>
              <div>
                <label className="form-label">Purpose of comparison</label>
                <textarea className="form-textarea" placeholder="Goal of this comparison" rows={2} value={formData.purpose} onChange={e => setFormData(f => ({ ...f, purpose: e.target.value }))} />
              </div>
              <div>
                <label className="form-label">Baseline criteria</label>
                <textarea className="form-textarea" placeholder="Paste the buyer's requirements or master RFP criteria..." rows={4} value={formData.baseline_criteria} onChange={e => setFormData(f => ({ ...f, baseline_criteria: e.target.value }))} />
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "24px" }}>
              <button className="btn-secondary" onClick={handleModalClose}>Cancel</button>
              <button className="btn-primary" onClick={handleRunAnalysis} disabled={!formData.run_name.trim()}>
                <ShieldCheck size={18} /> Run Analysis
              </button>
            </div>
          </div>
        </div>
      )}



      {/* ─────────────────────────────────────────────────────────────────
          MAIN WRAPPER
          ───────────────────────────────────────────────────────────────── */}
      <div className="dashboard-container">
        <main className="main-content">
          
          {/* TOPBAR */}
          <header className="topbar">
            <div className="topbar-left">
              <h1 className="brand-name">RFQ Analyzer</h1>
              <div className="main-tabs">
                {tabs.map((tab) => (
                  <button
                    key={tab.name}
                    className={`main-tab ${activeTab === tab.name ? "active" : ""}`}
                    onClick={() => setActiveTab(tab.name)}
                  >
                    {tab.name}
                  </button>
                ))}
              </div>
            </div>
            <div className="topbar-right">

            </div>
          </header>

          <div className="main-content-inner">
            <header className="greeting-section" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
              <div>
                <h1 className="greeting-title">Good morning, Admin</h1>
                <p className="greeting-subtitle">Stay on top of your RFQ analyses, monitor compliance, and track vendor status.</p>
              </div>
              <div style={{ display: "flex", gap: "12px" }}>
                <input type="file" accept=".pdf" ref={fileInputRef} style={{ display: "none" }} onChange={handleFileChange} />
                <button className="btn-secondary" onClick={() => setActiveTab("Extraction")}><RefreshCw size={16} /> Refresh</button>
                <button className="btn-primary" onClick={handleUploadClick} disabled={isUploading}>
                  {isUploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                  {isUploading ? "Analyzing..." : "Upload RFQ"}
                </button>
              </div>
            </header>

            {/* ════════════════════════════════════════════════════════════
                OVERVIEW TAB
                ════════════════════════════════════════════════════════════ */}
            {activeTab === "Overview" && (
              <div className="animate-fade-in">
                {/* KPI Cards */}
                <div className="kpi-grid">
                  <div className="kpi-card featured">
                    <div className="kpi-header">
                      <span className="kpi-title">Total Analyzed</span>
                      <div className="currency-badge" style={{ color: "var(--accent-primary)" }}>
                        <Tag size={12} /> RFQs
                      </div>
                    </div>
                    <div className="kpi-value">{history.length}</div>
                  </div>

                  <div className="kpi-card">
                    <div className="kpi-header">
                      <span className="kpi-title">Avg Compliance</span>
                      <Info size={16} color="var(--text-tertiary)" />
                    </div>
                    <div className="kpi-value">{compliancePct}%</div>
                  </div>

                  <div className="kpi-card">
                    <div className="kpi-header">
                      <span className="kpi-title">Deviations</span>
                      <Info size={16} color="var(--text-tertiary)" />
                    </div>
                    <div className="kpi-value">{deviationCount}</div>
                  </div>

                  <div className="kpi-card">
                    <div className="kpi-header">
                      <span className="kpi-title">Total Vendors</span>
                      <Info size={16} color="var(--text-tertiary)" />
                    </div>
                    <div className="kpi-value">{uniqueVendors}</div>
                  </div>
                </div>

                <div className="dashboard-main-grid">


                  {/* Right Column */}
                  <div className="section-card">
                    <div className="section-header-box">
                      <span className="section-title">Recent Activities</span>
                      <div style={{ display: "flex", gap: "8px" }}>
                        <div className="currency-badge" style={{ background: "var(--bg-hover)", border: "1px solid var(--border-light)" }}>
                          <Search size={12} /> Search
                        </div>
                        <div className="currency-badge" style={{ background: "var(--bg-hover)", border: "1px solid var(--border-light)" }}>
                          Filter <Settings size={12} />
                        </div>
                      </div>
                    </div>

                    <div className="activity-list">
                      {history.length > 0 ? (
                        history.map((h, i) => {
                          const mCount = h.comparison.comparison_items.filter(item => item.status === "match").length;
                          const tCount = h.comparison.comparison_items.length;
                          const pct = tCount > 0 ? Math.round((mCount / tCount) * 100) : 0;
                          return (
                            <div key={i} className="activity-item">
                              <div className="activity-left">
                                <div className="activity-icon success"><CheckCircle2 size={20} /></div>
                                <div className="activity-details">
                                  <span className="activity-title">Analysis Completed</span>
                                  <span className="activity-desc">For {h.extraction.vendor_name}</span>
                                </div>
                              </div>
                              <div className="activity-right">
                                <span className="activity-amount positive">Score: {pct}%</span>
                                <span className="activity-time">Just now</span>
                              </div>
                            </div>
                          );
                        })
                      ) : (
                        <div style={{ padding: "24px", textAlign: "center", color: "var(--text-secondary)" }}>
                          No recent activities.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ════════════════════════════════════════════════════════════
                EXTRACTION TAB
                ════════════════════════════════════════════════════════════ */}
            {activeTab === "Extraction" && (
              <div className="animate-fade-in section-card">
                {result ? (
                  <>
                    <h2 className="section-title" style={{ marginBottom: "24px" }}>Header &amp; Tracking Information</h2>
                    <div className="info-grid" style={{ marginBottom: "32px" }}>
                      <InfoField label="RFQ Reference Number" value={result.extraction.header.rfq_reference_number} />
                      <InfoField label="Issue Date" value={result.extraction.header.issue_date} />
                      <InfoField label="Question Deadline" value={result.extraction.header.question_deadline} />
                      <InfoField label="Submission Deadline" value={result.extraction.header.submission_deadline} />
                      <InfoField label="Buyer Company" value={result.extraction.header.buyer_company} />
                      <InfoField label="Buyer Contact" value={result.extraction.header.buyer_contact} />
                    </div>

                    <h2 className="section-title" style={{ marginBottom: "24px" }}>Technical Specifications</h2>
                    {result.extraction.technical_specs.length > 0 ? (
                      <div className="table-container" style={{ marginBottom: "32px" }}>
                        <table className="premium-table">
                          <thead>
                            <tr><th>Parameter</th><th>Value</th></tr>
                          </thead>
                          <tbody>
                            {result.extraction.technical_specs.map((spec, i) => (
                              <tr key={i}>
                                <td style={{ fontWeight: 600 }}>{spec.parameter}</td>
                                <td>{spec.value}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p style={{ color: "var(--text-secondary)", marginBottom: "32px" }}>No technical specifications extracted.</p>
                    )}
                  </>
                ) : <EmptyState tab="Extraction" />}
              </div>
            )}

            {/* ════════════════════════════════════════════════════════════
                COMPARISON TAB
                ════════════════════════════════════════════════════════════ */}
            {activeTab === "Comparison" && (
              <div className="animate-fade-in section-card">
                {result ? (
                  <>
                    <h2 className="section-title" style={{ marginBottom: "24px" }}>Requirements Comparison</h2>
                    <div className="table-container">
                      <table className="premium-table">
                        <thead>
                          <tr>
                            <th>Feature / Requirement</th>
                            <th>Baseline Value</th>
                            <th>Vendor Value</th>
                            <th>Status</th>
                            <th>Notes</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.comparison.comparison_items.map((item, i) => (
                            <tr key={i}>
                              <td style={{ fontWeight: 600 }}>{item.feature}</td>
                              <td style={{ color: "var(--text-secondary)" }}>{item.baseline_value}</td>
                              <td>{item.vendor_value}</td>
                              <td>
                                <span className={`status-tag status-${item.status}`}>
                                  <StatusIcon status={item.status} /> {item.status}
                                </span>
                              </td>
                              <td style={{ color: "var(--text-secondary)", fontSize: "0.85rem", maxWidth: "280px" }}>
                                {item.notes}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : <EmptyState tab="Comparison" />}
              </div>
            )}

            {/* ════════════════════════════════════════════════════════════
                PRICING TAB
                ════════════════════════════════════════════════════════════ */}
            {activeTab === "Pricing" && (
              <div className="animate-fade-in section-card">
                {result ? (
                  <>
                    <h2 className="section-title" style={{ marginBottom: "24px" }}>Bill of Quantities / Line Items</h2>
                    {result.extraction.line_items.length > 0 ? (
                      <div className="table-container" style={{ marginBottom: "32px" }}>
                        <table className="premium-table">
                          <thead>
                            <tr>
                              <th>Description</th>
                              <th>Part #</th>
                              <th>Qty</th>
                              <th>Unit Price</th>
                              <th>Total Price</th>
                            </tr>
                          </thead>
                          <tbody>
                            {result.extraction.line_items.map((item, i) => (
                              <tr key={i}>
                                <td style={{ fontWeight: 500 }}>{item.description}</td>
                                <td style={{ color: "var(--text-secondary)" }}>{item.part_number !== "Not Provided" ? item.part_number : "—"}</td>
                                <td>{item.quantity !== "Not Provided" ? `${item.quantity} ${item.unit !== "Not Provided" ? item.unit : ""}` : "—"}</td>
                                <td style={{ color: "var(--text-primary)", fontWeight: 600 }}>{item.unit_price !== "Not Provided" ? item.unit_price : "—"}</td>
                                <td style={{ fontWeight: 700 }}>{item.total_price !== "Not Provided" ? item.total_price : "—"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p style={{ color: "var(--text-secondary)", marginBottom: "32px" }}>No line items extracted.</p>
                    )}
                  </>
                ) : <EmptyState tab="Pricing" />}
              </div>
            )}

          </div>
        </main>
      </div>
    </div>
  );
}
