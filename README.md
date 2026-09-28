# ProcureGuard

**Fraud-Aware Accounts Payable Agent on Evolus + AMD**

ProcureGuard is an entry for the **Evolus Business Agents on AMD** track of the AMD Developer Hackathon: ACT III. An agent runs a real Accounts Payable process in Evolus — from an invoice email to a paid invoice in ERPNext — reasoning with an open model served on AMD, and hands anything suspicious to a person.

> **Design principle:** The model reasons. Tools act. Policies govern. Evolus orchestrates. Humans remain in control of exceptions.

## Business Problem

AP teams turn invoice emails into payments every day: read the document, find the vendor and purchase order, check for duplicates, confirm the amount and payment details, enter it in the ERP and escalate exceptions. The most costly failure is paying a fraudster who impersonates a known vendor and asks for payment to a new bank account. ProcureGuard automates the routine cases and reliably stops that one.

## How It Maps to the Track

| Track asks the agent to… | ProcureGuard |
|---|---|
| Take an input (email, PDF, form, chat) | Invoice email with PDF attachment via an Evolus email trigger |
| Reason with an open model on AMD | Qwen vision-language model served by vLLM on ROCm, AMD MI300X |
| Run an Evolus workflow | Case workflow branches on the decision |
| Turn documents into data | `extract_invoice` with a text-layer cross-check |
| Use AI Tools | Vendor, PO, duplicate, bank, sender-domain and risk checks |
| Update another system | Creates the Purchase Invoice in ERPNext |
| Hand the case to a person | Evolus review task with evidence, plus vendor verification via the contact on file |

## Architecture

```text
Invoice email
      |
      v
    Evolus  -- workflow, agent, human review task, notifications
      |
      |  AI Tools (HTTPS)
      v
ProcureGuard service  -- extraction, checks, policy engine, guarded ERP write, audit
      |                         |
      v                         v
   ERPNext               vLLM on ROCm (AMD MI300X)
                                |
                          Open Qwen VL model
      |
      v
APPROVE -> ERPNext Purchase Invoice
HUMAN_REVIEW -> Evolus review task
REJECT -> notify and close
```

See [Technical Architecture](docs/Technical-Architecture.md) for Plan A (Evolus agent on the AMD model) and Plan B (Evolus calls ProcureGuard).

## Demo Scenarios

1. **Normal invoice** — all checks pass; the Purchase Invoice is created in ERPNext.
2. **Lookalike domain + bank change** (headline) — email from `acme-logistlcs.com` asks for payment to a new account; payment is blocked, a review task is created and the vendor is contacted via the details on file.
3. **Duplicate invoice** — rejected; retries never create a second ERP record.
4. **PO amount variance** — above the 5% threshold; routed to review.
5. **Hidden-text injection** — invisible text tries to make the model extract the trusted bank account; the cross-check catches it.

## Stack

| Component | Technology |
|---|---|
| Business workflow | Evolus |
| Agent service | Python, FastAPI, PydanticAI |
| Model | Qwen vision-language model (final size chosen after the pre-event spike) |
| Model serving | vLLM on ROCm |
| Compute | AMD Instinct MI300X (AMD Developer Cloud) |
| ERP | ERPNext (Docker) |
| State, audit, idempotency | PostgreSQL |
| PDF text layer | pdfplumber |
| Data | Synthetic "Nova Industries" vendors, POs and invoices |

## Documentation

- [Implementation Plan](docs/Implementation-Plan.md) — timeline, open questions, submission checklist, risks
- [Proposal](docs/Proposal.md)
- [Business Architecture](docs/Business-Architecture.md)
- [Technical Architecture](docs/Technical-Architecture.md)
- [Open-Source Projects & Datasets](docs/Open-Source-and-Datasets.md)
- [Demo Scenario](docs/Demo-Scenario.md)

## MVP Success Criteria

An invoice email arrives in Evolus; the document is turned into data on the AMD-hosted model; AI Tools check it against ERPNext; the deterministic policy engine decides; safe invoices become ERPNext Purchase Invoices automatically; the fraud and injection cases land in an Evolus review task with evidence; and there are **zero wrong auto-approvals** across the evaluation set.

## Safety Boundary

The model never has ERP or database credentials. It can call read-only tools; writes are triggered by the Evolus workflow after a decision, and the ERP write is refused unless a stored `APPROVE` exists for the case. Financial decisions are deterministic, every required check must run, and anything uncertain fails closed into human review.
