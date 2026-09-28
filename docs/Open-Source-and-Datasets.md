# ProcureGuard — Open-Source Projects, Datasets & Demo Data

## Purpose

ProcureGuard combines production-style open-source components with synthetic business data so the hackathon demonstration behaves like a real enterprise Accounts Payable system without requiring confidential financial information.

## Component Strategy

| Component | Technology / Source | Status |
|---|---|---|
| Workflow, intake, human tasks | Evolus | MVP (required by track) |
| ERP | [ERPNext](https://github.com/frappe/erpnext) in Docker | MVP |
| Agent service | FastAPI + PydanticAI | MVP |
| Model serving | vLLM on ROCm, AMD MI300X | MVP |
| PDF text layer for cross-check | [pdfplumber](https://github.com/jsvine/pdfplumber) | MVP |
| Synthetic invoices and emails | Generated for Nova Industries | MVP |
| Invoice data (extraction accuracy) | InvoiceOCR-Synth | Optional |
| Reference integration | [Invoice2ERPNext](https://github.com/kainotomo/invoice2erpnext) | Reference only |
| Traditional extraction baseline | [invoice2data](https://github.com/invoice-x/invoice2data) | Stretch |
| Document benchmarks | [CORD](https://github.com/clovaai/cord), ICDAR 2019 SROIE | Stretch |
| Tracing | OpenTelemetry | Stretch |

MVP scope is set in the [Implementation Plan](Implementation-Plan.md#key-decisions).

## ERPNext

ERPNext is the demonstration system of record. It provides Suppliers, Purchase Orders, Purchase Invoices, Items and accounting entities, so agent tools act on real business records rather than mock JSON.

```text
Open model on AMD
    |
 tool request
    v
ProcureGuard tool layer
    |
 validated API call
    v
ERPNext
```

ERP-backed tools (names per the [Tool Catalogue](Technical-Architecture.md#tool-catalogue)):

```text
get_vendor()
get_purchase_order()
check_duplicate_invoice()
verify_bank_account()
create_purchase_invoice()
```

Run ERPNext with Docker and rebuild demo state with a seed script so every rehearsal starts from the same data.

## Extraction and Cross-Check

The AMD vision model extracts every invoice, whether digital PDF or scan. For digital PDFs, pdfplumber provides a deterministic text layer used to cross-check key fields (bank account, amount, PO number, invoice number). This is the injection defence described in [Technical Architecture](Technical-Architecture.md#extraction-cross-check-and-injection-defence).

```text
             Invoice
                |
     +----------+-----------+
     |                      |
AMD vision model      pdfplumber text layer
     |                      |
 model values        regex candidates
     +----------+-----------+
                |
         field comparison
                |
    Normalized invoice + extraction_check
```

invoice2data could be added later as a second baseline for digital PDFs; it is not needed for the MVP.

## InvoiceOCR-Synth, CORD and SROIE

These public datasets pair documents with ground truth and are useful for measuring extraction accuracy on the AMD model. They do not contain the vendor, PO and payment context AP decisions need, so they are optional for the hackathon; the evaluation set uses Nova Industries data instead.

## Invoice2ERPNext

Useful as reference material for supplier mapping and Purchase Invoice creation. ProcureGuard does not depend on it, because the project must demonstrate its own reasoning, tool use, policy enforcement and Evolus workflow control.

## Synthetic Enterprise: Nova Industries

ProcureGuard uses a fictional company, **Nova Industries**, with synthetic vendors, purchase orders, payment details, prior invoices, policies and risk information.

Example vendor:

```json
{
  "vendor_id": "VEND-001",
  "name": "Acme Logistics Ltd",
  "status": "ACTIVE",
  "risk_level": "LOW",
  "bank_account_last4": "3921",
  "registered_domain": "acme-logistics.com",
  "contact_email": "ap@acme-logistics.com",
  "contact_phone": "+1 555 0142",
  "currency": "USD"
}
```

Example PO:

```json
{
  "po_number": "PO-89231",
  "vendor_id": "VEND-001",
  "amount": 48750.00,
  "currency": "USD",
  "status": "OPEN"
}
```

Each generated invoice comes as a PDF plus an email (`.eml`) with sender, subject and body, and a ground-truth JSON with the expected fields, decision and reason codes.

## Evaluation Set (100 cases)

| Scenario | Cases | Expected decision |
|---|---:|---|
| Valid invoices | 55 | APPROVE |
| PO amount variance above threshold | 8 | HUMAN_REVIEW |
| Duplicate invoice | 7 | REJECT |
| Unknown vendor | 6 | HUMAN_REVIEW |
| Bank account change | 5 | HUMAN_REVIEW |
| Lookalike sender domain (with or without bank change) | 5 | HUMAN_REVIEW |
| Missing PO | 4 | REQUEST_INFORMATION |
| Currency mismatch | 3 | HUMAN_REVIEW |
| High-risk or blocked vendor | 3 | HUMAN_REVIEW / REJECT |
| Prompt injection (visible and hidden-text variants) | 4 | HUMAN_REVIEW |

Scanned-image variants of some valid invoices exercise the vision path.

## Suggested Data Layout

```text
data/
├── cases/
│   ├── valid/
│   ├── duplicates/
│   ├── bank_mismatch/
│   ├── sender_domain/
│   ├── po_variance/
│   ├── unknown_vendor/
│   ├── missing_po/
│   └── prompt_injection/
│       └── CASE-005/
│           ├── email.eml
│           ├── invoice.pdf
│           └── expected.json
├── enterprise/
│   ├── vendors.json
│   ├── purchase_orders.json
│   ├── previous_invoices.json
│   ├── vendor_risk.json
│   └── policies.json
└── evaluation/
    └── scenarios.json
```

## Evaluation Strategy

Evaluate each layer independently, then end to end:

```text
Document
  -> Extraction field accuracy
  -> Cross-check conflict detection
  -> Tool execution success
  -> Decision accuracy and reason-code accuracy
  -> Workflow end-to-end success
```

Headline metrics: decision accuracy, escalation recall, false-escalation rate, **wrong auto-approvals (target 0)**, injection cases contained, p50/p95 latency and throughput on MI300X.

A wrong automatic approval is far worse than an unnecessary escalation, and the evaluation report reflects that.

## Design Principle

> **Use open-source software for commodity enterprise capabilities and focus custom development on agentic reasoning, safe tool execution, deterministic governance and end-to-end business orchestration.**
