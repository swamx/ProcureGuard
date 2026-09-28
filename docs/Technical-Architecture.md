# ProcureGuard — Technical Architecture

## Architecture Overview

ProcureGuard separates four concerns: **Evolus** runs the business process, the **ProcureGuard service** exposes controlled AI Tools and the deterministic policy engine, an **open model on AMD** handles document understanding and reasoning, and **ERPNext** is the system of record.

```text
INPUTS: Email (primary) | PDF upload | Web Form | Chat
                    |
                    v
+------------------------------------------------+
| EVOLUS                                         |
| Email trigger | Workflow | Agent | Human Tasks |
| Notifications | Case history                   |
+-----------------------+------------------------+
                        |  AI Tools (HTTPS, typed)
                        v
+------------------------------------------------+
| PROCUREGUARD SERVICE (FastAPI + PydanticAI)    |
| extract_invoice | read-only checks             |
| policy engine + completeness gate              |
| guarded ERP write | audit log | idempotency    |
+-----------+----------------------+-------------+
            |                      |
            v                      v
   ERPNext (Docker)         Model endpoint
   Supplier / PO /          (OpenAI-compatible)
   Purchase Invoice                |
            |                      v
      PostgreSQL              vLLM on ROCm
   cases, audit,                   |
   idempotency keys                v
                          Qwen VL model, AMD MI300X
```

## Evolus Responsibilities

Evolus must do visible, substantive work — the track is judged by the Evolus partner.

| Evolus does | Detail |
|---|---|
| Intake | Email trigger on the AP mailbox; attachment handed to the workflow |
| Workflow | Case creation, branching on the decision, retries, completion |
| Agent reasoning (Plan A) | Evolus agent, using the AMD model, calls ProcureGuard AI Tools |
| Human review | Task for Accounts Payable with evidence; resumes the workflow on Approve / Reject / Request Info |
| Communication | Notification to AP; vendor verification message to the contact on file |

## Evolus Integration Plans

Chosen in Phase 0 once we know whether Evolus accepts a custom model endpoint (see [Implementation Plan](Implementation-Plan.md#open-questions-blocking), Q1–Q3).

### Plan A — Evolus agent reasons on AMD (preferred)

```text
Email --> Evolus workflow --> Evolus agent (model = our vLLM endpoint on AMD)
                                   |
                                   +--> AI Tool: extract_invoice
                                   +--> AI Tools: get_vendor, get_purchase_order,
                                   |    check_duplicate_invoice, verify_bank_account,
                                   |    verify_sender_domain, validate_invoice_against_po,
                                   |    check_vendor_risk
                                   +--> AI Tool: evaluate_case  (policy engine)
                                   |
                     Evolus workflow branches on the decision
                        APPROVE      -> create_purchase_invoice -> notify -> close
                        HUMAN_REVIEW -> review task (+ request_vendor_verification)
                        REJECT       -> notify -> close
```

### Plan B — Evolus calls ProcureGuard, which reasons on AMD

Used if Evolus cannot point its agent at our endpoint.

```text
Email --> Evolus workflow --> AI Tool: POST /v1/cases/analyze
                                   |
                   ProcureGuard agent (PydanticAI, AMD model) runs
                   extraction, checks and policy internally
                                   |
                     Evolus workflow branches on the decision (same as Plan A)
```

In both plans the **Evolus workflow**, not the model, triggers the ERP write and the human task.

## ProcureGuard Service

Stack: Python, FastAPI, Pydantic, PydanticAI, HTTPX, PostgreSQL.

Endpoints:

```http
POST /v1/tools/{tool_name}      # individual AI Tools (Plan A)
POST /v1/cases/analyze          # full analysis (Plan B)
POST /v1/cases/{case_id}/erp    # guarded ERP write, called by the Evolus workflow
GET  /v1/cases/{case_id}/audit  # evidence for the reviewer and the demo
GET  /v1/metrics                # measured latency, throughput, decision counts
```

Example analysis result:

```json
{
  "case_id": "CASE-002",
  "decision": "HUMAN_REVIEW",
  "risk_level": "CRITICAL",
  "reason_codes": ["BANK_ACCOUNT_MISMATCH", "SENDER_DOMAIN_MISMATCH"],
  "recommended_action": "VERIFY_VIA_KNOWN_CONTACT",
  "explanation": "Invoice matches PO-89231, but the payment account differs from the vendor master and the email came from a domain that is not the vendor's registered domain.",
  "evidence_url": "/v1/cases/CASE-002/audit"
}
```

## Tool Catalogue

Tools are the security boundary. Every tool has typed input/output, a timeout, an audit event and an explicit read/write classification. This is the single source of truth for tool names across all docs.

| Tool | Type | Purpose |
|---|---|---|
| `extract_invoice` | read | Document → structured invoice on the AMD model, with text-layer cross-check |
| `get_vendor` | read | Trusted vendor record: status, bank last 4, registered email domain, contact on file |
| `get_purchase_order` | read | PO amount, currency, status, vendor |
| `check_duplicate_invoice` | read | Same vendor + invoice number already in ERPNext |
| `validate_invoice_against_po` | read | Deterministic amount/currency/vendor comparison and variance |
| `verify_bank_account` | read | Invoice bank vs vendor master |
| `verify_sender_domain` | read | Email sender domain vs vendor's registered domain; flags lookalikes |
| `check_vendor_risk` | read | Vendor risk/compliance flags from the synthetic risk list |
| `evaluate_case` | read | Runs the completeness gate and the policy engine; returns the decision |
| `create_purchase_invoice` | **write** | Creates the ERPNext Purchase Invoice; refused unless the case has a stored `APPROVE` decision |
| `create_review_task` | **write** | Creates the Evolus human task with evidence |
| `request_vendor_verification` | **write** | Sends a verification request to the **contact on file**, never to the email's reply-to |
| `send_notification` | **write** | Notifies AP / stakeholders |

The model may call read tools freely. Write tools are called by the Evolus workflow after a decision, and `create_purchase_invoice` enforces the stored decision server-side, so a manipulated model cannot trigger it.

## Where the Model Adds Value

The mandatory checks always run; the model is not needed to decide *whether* to check the bank account. The model is used where deterministic code is weak:

- Reading scanned or irregular invoices (vision extraction).
- Fuzzy vendor matching ("ACME Logistics Limited" → `VEND-001`).
- Mapping invoice line items to PO lines.
- Choosing and sequencing additional checks for unusual cases.
- Writing the evidence summary for the reviewer.
- Drafting the vendor verification message.

## Structured Agent State

```python
class CaseState(BaseModel):
    case_id: str
    source: Literal["EMAIL", "UPLOAD", "FORM", "CHAT"]
    sender_address: str | None = None
    invoice: Invoice | None = None
    extraction_check: CheckResult | None = None
    vendor: Vendor | None = None
    purchase_order: PurchaseOrder | None = None
    duplicate_check: CheckResult | None = None
    po_validation: CheckResult | None = None
    bank_validation: CheckResult | None = None
    sender_validation: CheckResult | None = None
    risk_check: CheckResult | None = None
    decision: CaseDecision | None = None
    tool_history: list[ToolExecution] = []
```

Business state is persisted in PostgreSQL independently of conversation history.

## Decisions and Reason Codes

```python
class CaseDecision(BaseModel):
    decision: Literal["APPROVE", "HUMAN_REVIEW", "REJECT", "REQUEST_INFORMATION"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    reason_codes: list[ReasonCode]
    recommended_action: str | None
    explanation: str
```

| Reason code | Decision |
|---|---|
| `DUPLICATE_INVOICE` | REJECT |
| `VENDOR_BLOCKED` | REJECT |
| `BANK_ACCOUNT_MISMATCH` | HUMAN_REVIEW |
| `SENDER_DOMAIN_MISMATCH` | HUMAN_REVIEW |
| `EXTRACTED_FIELD_CONFLICT` | HUMAN_REVIEW |
| `PO_AMOUNT_VARIANCE` | HUMAN_REVIEW (above threshold) |
| `CURRENCY_MISMATCH` | HUMAN_REVIEW |
| `UNKNOWN_VENDOR` | HUMAN_REVIEW |
| `VENDOR_HIGH_RISK` | HUMAN_REVIEW |
| `ABOVE_AUTO_APPROVAL_LIMIT` | HUMAN_REVIEW (demo limit set above CASE-001's $48,750) |
| `MISSING_PO` | REQUEST_INFORMATION |
| `REQUIRED_CHECK_MISSING` | HUMAN_REVIEW |
| `TOOL_UNAVAILABLE` | HUMAN_REVIEW |

The model does not produce a self-reported confidence score. Uncertainty is measured through checks (see extraction cross-check).

## Policy Engine and Completeness Gate

The policy engine is deterministic and runs inside `evaluate_case`.

```python
REQUIRED_CHECKS = {
    "extraction_check", "vendor", "purchase_order", "duplicate_check",
    "po_validation", "bank_validation", "risk_check",
}  # plus sender_validation when source == "EMAIL"

def evaluate(state: CaseState, policy: Policy) -> CaseDecision:
    missing = [c for c in required_checks(state) if getattr(state, c) is None]
    if missing:
        return review("REQUIRED_CHECK_MISSING", missing)   # fail closed
    if state.duplicate_check.failed:
        return reject("DUPLICATE_INVOICE")
    if state.vendor.status == "BLOCKED":
        return reject("VENDOR_BLOCKED")
    codes = collect_failures(state)  # bank, sender, conflict, variance, currency, risk
    if codes:
        return review(*codes)
    if state.invoice.amount > policy.auto_approval_limit:
        return review("ABOVE_AUTO_APPROVAL_LIMIT")
    return approve()
```

The **completeness gate** means a prompt injection that convinces the model to skip a check produces `REQUIRED_CHECK_MISSING` → review, not approval.

## Extraction Cross-Check and Injection Defence

Invoice content is untrusted. The realistic attack is not "approve this invoice" text — policy already ignores that — but text that **changes what gets extracted**, such as hidden text telling the model to report the old bank account.

```text
PDF / image
   |
   +--> AMD vision model  --> structured invoice (model values)
   |
   +--> PDF text layer (pdfplumber) --> deterministic candidates
        (regex for bank account, IBAN, amount, PO number, invoice number)
   |
   v
Compare key fields
   - model value not among candidates           --> EXTRACTED_FIELD_CONFLICT
   - more than one distinct bank account found  --> EXTRACTED_FIELD_CONFLICT
   - all agree                                  --> extraction_check PASS
```

Combined with the bank check against the vendor master, the attack fails whether or not the model is fooled:

- Model extracts the real (new) account → `BANK_ACCOUNT_MISMATCH`.
- Model is tricked into reporting the trusted account → `EXTRACTED_FIELD_CONFLICT`.

For image-only scans with no text layer, key fields must still match the vendor master and PO; any mismatch is reviewed.

## Idempotency and Concurrency

State-changing operations carry idempotency keys such as `CASE-001:CREATE_PURCHASE_INVOICE`; a retry returns the stored result. A unique `(vendor_id, invoice_number)` constraint in PostgreSQL and the ERPNext duplicate check both prevent a second record.

## Security Model

```text
Model (on AMD)
  | no credentials, no direct ERP access
  v
ProcureGuard tools
  |- service token from Evolus (authentication)
  |- read/write classification (authorization)
  |- schema + business validation
  |- stored-decision check on ERP write
  |- audit event per call
  |- idempotency on writes
  v
ERPNext / Evolus
```

## Audit and Observability

Each tool call writes an audit event to PostgreSQL correlated by `case_id` and `tool_call_id`. Business evidence is stored, not model chain-of-thought.

```json
{
  "case_id": "CASE-002",
  "actor_type": "AI_AGENT",
  "event_type": "RISK_DETECTED",
  "reason_code": "BANK_ACCOUNT_MISMATCH",
  "evidence": { "vendor_account_last4": "3921", "invoice_account_last4": "8219" }
}
```

`GET /v1/metrics` reports measured model latency, tokens, tool latency and failures, end-to-end time, decision counts and escalation rate. GPU memory and utilisation are captured from `rocm-smi` during the evaluation run. Full OpenTelemetry tracing is a stretch goal.

## Failure Handling

Financial workflows fail closed. Invalid structured model output is retried once, then reviewed. ERP timeouts use idempotent retries. Missing data, unavailable tools and conflicting extraction route to human review.

## Deployment

```text
Evolus (hosted)
   |  HTTPS + service token
   v
ProcureGuard service + PostgreSQL + ERPNext   (Docker Compose, one VM)
   |  OpenAI-compatible HTTPS
   v
vLLM on ROCm  --  AMD Developer Cloud, MI300X
```

## Core Architectural Principle

> **The model reasons. Tools act. Policies govern. Evolus orchestrates. Humans remain in control of exceptions.**
