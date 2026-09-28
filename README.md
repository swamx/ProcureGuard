# ProcureGuard

**Fraud-Aware Accounts Payable Agent on Evolus + AMD**

ProcureGuard is an entry for the **Evolus Business Agents on AMD** track of the AMD Developer Hackathon: ACT III. An agent runs a real Accounts Payable process in Evolus — from an invoice email to an ERPNext Purchase Invoice — reasoning with an open model served on AMD, while suspicious cases are stopped and handed to a person.

> **Design principle:** The model reasons. Tools act. Policies govern. Evolus orchestrates. Humans remain in control of exceptions.

## Business Problem

AP teams turn invoice emails into payments every day: read the document, find the vendor and purchase order, check for duplicates, confirm the amount and payment details, enter it in the ERP and escalate exceptions. A particularly costly failure is vendor-payment fraud: an attacker impersonates a known vendor and asks for payment to a new bank account.

ProcureGuard automates routine invoices while deliberately failing closed on fraud, ambiguity, missing controls and document-integrity problems.

## How It Maps to the Track

| Track asks the agent to… | ProcureGuard |
|---|---|
| Take an input | Invoice email with PDF attachment via an Evolus email trigger |
| Reason with an open model on AMD | Qwen vision-language candidate selected by a reliability/latency gate and served by vLLM on ROCm |
| Run an Evolus workflow | Evolus owns case state, branching, writes, review and notifications |
| Turn documents into data | `extract_invoice` on AMD with a deterministic text-layer integrity cross-check |
| Use AI Tools | Vendor, PO, duplicate, bank, sender-domain and risk checks |
| Update another system | Creates the Purchase Invoice in ERPNext after a stored APPROVE |
| Hand the case to a person | Evolus review task with evidence and vendor verification via the contact on file |

## Architecture

```text
Invoice email
      |
      v
    Evolus  -- workflow, agent, human review task, notifications
      |
      |  AI Tools (HTTPS)
      v
ProcureGuard service  -- extraction, mandatory checks, policy, guarded ERP write, audit
      |                         |
      v                         v
   ERPNext               vLLM on ROCm (AMD MI300X)
                                |
                        Selected open Qwen VL model
      |
      v
APPROVE      -> ERPNext Purchase Invoice
HUMAN_REVIEW -> Evolus review task
REJECT       -> notify and close
```

See [Technical Architecture](docs/Technical-Architecture.md) for Plan A (preferred: Evolus agent uses the AMD model) and Plan B (Evolus calls ProcureGuard, which reasons on AMD).

## Mandatory Controls

The model may choose additional tools, but it cannot omit the controls required to authorize straight-through processing:

```text
✓ Extraction integrity
✓ Vendor lookup/status
✓ Purchase-order validation
✓ Duplicate check
✓ Bank-account validation
✓ Sender-domain validation for email cases
✓ Vendor risk check
```

If any required result is missing or unavailable, the completeness gate returns `HUMAN_REVIEW`. The LLM never decides whether these controls are optional.

## Headline Fraud Scenario

A convincing invoice arrives from `acme-logistlcs.com` instead of the trusted `acme-logistics.com` and requests payment to a new bank account. Vendor, PO, amount and currency all match.

The fraud score is deterministic and evidence-based:

```text
Known vendor                       +0
Valid PO                           +0
Amount/currency match              +0
Lookalike sender domain           +40
Bank account changed              +60
                                  ---
Fraud score                       100

Decision: HUMAN_REVIEW
Payment:  BLOCKED
```

Weights are demo policy configuration, not LLM-generated values. Any hard policy condition can force review regardless of score.

## Demo Scenarios

1. **Normal invoice** — all mandatory checks pass; the Purchase Invoice is created in ERPNext.
2. **Lookalike domain + bank change** (headline) — payment is blocked, a review task is created and the vendor is contacted via details already on file.
3. **Duplicate invoice** — rejected; retries never create a second ERP record.
4. **PO amount variance** — above the configured threshold; routed to review.
5. **Document-layer prompt injection attack** — hidden PDF text attempts to corrupt extraction; the integrity cross-check catches the conflict and fails closed.

## Stack

| Component | Technology |
|---|---|
| Business workflow | Evolus |
| Agent service | Python, FastAPI, PydanticAI |
| Model | Qwen vision-language candidate chosen after the AMD spike |
| Model serving | vLLM on ROCm |
| Compute | AMD Instinct MI300X / AMD Developer Cloud |
| ERP | ERPNext (Docker) |
| State, audit, idempotency | PostgreSQL |
| PDF text layer | pdfplumber |
| Data | Synthetic "Nova Industries" vendors, POs, emails and invoices |

## Model Selection Gate

ProcureGuard uses the **largest model that meets the reliability and latency gate**, not simply the largest model that fits in GPU memory. Candidate models are compared on the same evaluation set.

A candidate must demonstrate:

- Near-perfect schema-valid structured output.
- Reliable tool calling and arguments.
- Strong invoice-field extraction.
- **0 unsafe/wrong auto-approvals** in the evaluation set.
- Containment of all injection test cases.
- Acceptable p95 latency for the live workflow.

If a smaller model is more reliable operationally than a 70B-class candidate, the smaller model wins.

## Evaluation

Two business metrics anchor the evaluation:

- **Unsafe Straight-Through Rate (USTR):** suspicious/fraud/invalid cases that were automatically approved. Target: **0%**.
- **Legitimate Straight-Through Processing Rate (STP):** safe invoices automatically completed without unnecessary human review. Higher is better once USTR is zero.

Results are shown as a decision confusion matrix plus extraction accuracy, escalation recall, false-escalation rate, injection containment, latency, throughput and AMD GPU utilization. All reported performance numbers are measured, never hand-entered.

## Documentation

- [Implementation Plan](docs/Implementation-Plan.md) — timeline, model gate, vertical-slice priority, open questions, submission checklist and risks
- [Proposal](docs/Proposal.md)
- [Business Architecture](docs/Business-Architecture.md)
- [Technical Architecture](docs/Technical-Architecture.md)
- [Open-Source Projects & Datasets](docs/Open-Source-and-Datasets.md)
- [Demo Scenario](docs/Demo-Scenario.md)

## MVP Success Criteria

An invoice email arrives in Evolus; the document is turned into structured data using the AMD-hosted model; all mandatory controls execute; deterministic policy decides whether straight-through processing is permitted; safe invoices become ERPNext Purchase Invoices; fraud and injection cases land in an Evolus review task with evidence; and the evaluation set records **0 unsafe auto-approvals**.

## Safety Boundary

The model never has ERP or database credentials. It calls read-only tools; state-changing actions are triggered by the Evolus workflow after a decision, and the ERP write is refused unless a stored `APPROVE` exists for the case. Required controls are deterministic, fraud scoring is policy-driven, and anything uncertain fails closed into human review.