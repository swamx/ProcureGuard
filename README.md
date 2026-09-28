# ProcureGuard

**Autonomous Vendor Invoice & Compliance Agent on Evolus + AMD**

ProcureGuard is an agentic business-process automation project for the **Evolus Business Agents on AMD** challenge. It automates a real Accounts Payable workflow from invoice intake through document understanding, vendor and purchase-order validation, risk analysis, human escalation, and ERP update.

> **Design principle:** The model reasons. Tools act. Policies govern. Evolus orchestrates. Humans remain in control of exceptions.

## Business Problem

Accounts Payable teams repeatedly receive invoices, extract fields, identify vendors, locate purchase orders, check duplicates, validate amounts and payment details, assess risk, update ERP systems, and route exceptions to people. ProcureGuard combines workflow orchestration and agentic AI to automate this process safely.

## Architecture

```text
Invoice / Email / Web Form
          |
          v
       Evolus
  Workflow + Case
          |
          v
 Document Processing
          |
          v
   ProcureGuard Agent
  FastAPI + PydanticAI/
       LangGraph
          |
          v
 Open Model on AMD
  vLLM/SGLang + ROCm
          |
   +------+------+----------------+
   |             |                |
   v             v                v
ERPNext      Policy Engine     Risk Tools
Vendor/PO    Deterministic     Compliance
Invoices     Controls          Validation
   |             |                |
   +-------------+----------------+
                 |
                 v
       APPROVE / REVIEW / REJECT
                 |
                 v
              Evolus
                 |
       +---------+---------+
       |                   |
       v                   v
 ERPNext Update       Human Review
```

## Core Capabilities

- PDF/email invoice intake
- Structured invoice extraction
- Vendor resolution and PO matching
- Duplicate invoice and bank-account-change detection
- Vendor risk/compliance checks
- Open-model reasoning and tool selection on AMD
- Deterministic policy enforcement
- Straight-through processing for low-risk cases
- Human-in-the-loop escalation
- ERPNext integration
- Audit trail and OpenTelemetry observability
- Prompt-injection-resistant document processing

## Open-Source Stack

| Component | Technology |
|---|---|
| Business workflow | Evolus |
| ERP | ERPNext |
| Agent service | Python + FastAPI |
| Agent orchestration | PydanticAI and/or LangGraph |
| Model | Qwen / Llama / Mistral |
| Model serving | vLLM / SGLang |
| GPU runtime | ROCm |
| Compute | AMD GPU |
| State/Audit | PostgreSQL |
| Cache/coordination | Redis |
| Observability | OpenTelemetry |
| Invoice baseline | invoice2data |
| Document datasets | InvoiceOCR-Synth, CORD, SROIE |

## Demo Scenarios

1. **Normal invoice** — validations pass and a Purchase Invoice is created automatically.
2. **Bank-account mismatch** — payment is blocked and routed to human review.
3. **Duplicate invoice** — duplicate is detected and no second ERP transaction is created.
4. **PO amount mismatch** — policy threshold is exceeded and the case is escalated.
5. **Prompt injection** — malicious instructions embedded in a PDF are treated as untrusted data and cannot bypass policy or tools.

## Documentation

- [Proposal](docs/Proposal.md)
- [Business Architecture](docs/Business-Architecture.md)
- [Technical Architecture](docs/Technical-Architecture.md)
- [Open-Source Projects & Datasets](docs/Open-Source-and-Datasets.md)
- [Demo Scenario](docs/Demo-Scenario.md)

## MVP Success Criteria

ProcureGuard succeeds when it can ingest an invoice, extract structured information, use an AMD-hosted open model to reason about the case, call controlled business tools, apply deterministic policies, execute the appropriate Evolus workflow path, update ERPNext for safe cases, and route risky cases to a human with supporting evidence.

## Safety Boundary

The language model never receives unrestricted ERP or database access. Enterprise actions are exposed only through strongly typed, authenticated, authorized, auditable, and idempotent tools. Financial authorization rules remain deterministic, and high-risk or uncertain cases fail closed into human review.
