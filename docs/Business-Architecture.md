# ProcureGuard — Business Architecture

## Purpose

ProcureGuard defines how an AI business agent participates in an enterprise Accounts Payable process while preserving governance, auditability, human oversight and deterministic business controls.

## Business Actors

| Actor | Responsibility |
|---|---|
| Vendor | Submits invoice |
| Accounts Payable | Reviews invoice exceptions |
| Procurement | Owns purchase orders |
| Compliance | Reviews vendor risk |
| Finance Approver | Approves policy-sensitive transactions |
| Evolus | Email intake, workflow, human review tasks, notifications |
| ProcureGuard Agent | Reasons on the AMD-hosted model and calls AI Tools |
| ERPNext | Financial system of record for the demo |
| Vendor Master | Trusted vendor information |

## End-to-End Business Process

```text
Vendor (or impersonator) sends invoice email
        |
        v
Evolus email trigger (also: PDF upload / form / chat)
        |
        v
Evolus creates case
        |
        v
Extract and normalize invoice
        |
        v
ProcureGuard analyzes case
        |
        v
+--------------------------------------+
| Business Validation                  |
| - Vendor verification                |
| - PO validation                      |
| - Duplicate detection                |
| - Amount/currency validation         |
| - Bank-account validation            |
| - Sender-domain validation           |
| - Compliance/risk checks             |
+------------------+-------------------+
                   |
                   v
             Policy Decision
              /     |     \
             /      |      \
        APPROVE   REVIEW   REJECT
           |         |        |
           |     Human Task   |
           +---------+--------+
                     |
                     v
                 ERP Update
                     |
                     v
                  Notify
                     |
                     v
                 Close Case
```

## Business Capabilities

ProcureGuard supports invoice intake, document understanding, vendor resolution, purchase-order matching, duplicate detection, payment-detail verification, compliance validation, risk-based routing, enterprise update and stakeholder communication.

## Decision Model

The LLM does not independently authorize financial transactions. AI reasoning is separated from business authorization.

| Condition | Outcome |
|---|---|
| Valid PO + known vendor + matching bank + expected sender + low risk | Auto-process (APPROVE) |
| PO variance within threshold (5%) | Auto-process |
| PO variance above threshold | HUMAN_REVIEW |
| Missing PO | REQUEST_INFORMATION |
| Duplicate invoice | REJECT |
| Bank account changed | Block payment + HUMAN_REVIEW + verify via contact on file |
| Sender domain is not the vendor's registered domain | Block payment + HUMAN_REVIEW |
| Vendor blocked by compliance | REJECT |
| Vendor flagged high risk | HUMAN_REVIEW |
| Extracted values conflict with the document text layer | HUMAN_REVIEW |
| A required check did not run | HUMAN_REVIEW (fail closed) |
| Critical tool unavailable | HUMAN_REVIEW (fail closed) |

Reason codes are listed in [Technical Architecture](Technical-Architecture.md#decisions-and-reason-codes).

## Human-in-the-Loop

Human intervention is a normal workflow state rather than an AI failure.

```text
Agent
  |
  +-- high confidence + policy permits --> automated action
  |
  +-- uncertainty / risk --> Evolus Human Task
                                  |
                                  v
                           Human Reviewer
                            /    |     \
                       Approve Reject Request Info
```

The reviewer receives the original email and document, extracted fields, vendor record, PO data, tool results, reason codes and recommended action.

For a bank-account change, the agent also sends a verification request to the vendor's **contact on file** (email and phone from the vendor master), never to the address that sent the invoice. This mirrors the standard AP control against payment-redirection fraud.

## AI Reasoning vs Business Rules

AI is appropriate for document understanding, ambiguous-field resolution, classification, tool selection, evidence summarization and recommendations.

Deterministic systems remain responsible for monetary thresholds, authorization limits, duplicate constraints, vendor status, compliance blocks, payment execution and mandatory approval requirements.

```text
AI Findings + Verified Tool Results + Business Rules
                         |
                         v
                Workflow Decision
```

## Business State Model

```text
RECEIVED
   |
EXTRACTING
   |
VALIDATING
   |
AGENT_ANALYSIS
   |
DECISION_PENDING
   +--> APPROVED
   +--> HUMAN_REVIEW
   +--> REJECTED
   +--> INFORMATION_REQUIRED
             |
          ERP_PENDING
             |
          PROCESSED
             |
           CLOSED
```

Explicit states allow long-running workflows to survive retries, system outages and human delays.

## Auditability

Representative event history:

```text
CASE_CREATED
DOCUMENT_RECEIVED
EXTRACTION_COMPLETED
VENDOR_MATCHED
PO_VALIDATED
DUPLICATE_CHECK_PASSED
BANK_ACCOUNT_MISMATCH
SENDER_DOMAIN_MISMATCH
RISK_CRITICAL
PAYMENT_BLOCKED
REVIEW_TASK_CREATED
VENDOR_VERIFICATION_REQUESTED
```

The audit trail records evidence and actions, not hidden chain-of-thought.

## Business KPIs

| KPI | Description |
|---|---|
| Straight-through rate | Invoices requiring no human interaction |
| Processing latency | Receipt to decision |
| Exception rate | Cases routed to humans |
| Extraction accuracy | Correct structured fields |
| PO match rate | Automatically matched invoices |
| Duplicate detection | Duplicate payments prevented |
| Risk detection | Suspicious cases identified |
| Wrong auto-approvals | Risky invoices approved without review (target: 0) |
| Human override rate | Agent recommendations changed by people |
| Cost per invoice | Operational processing cost |
| Tool failure rate | External integration reliability |

## Reusable Business-Agent Pattern

The same architecture can later support vendor onboarding, contract compliance, expenses, procurement, claims, customer onboarding and compliance investigations.