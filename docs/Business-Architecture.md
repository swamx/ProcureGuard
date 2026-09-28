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
| Evolus | Orchestrates business workflow |
| ProcureGuard Agent | Reasons and selects business tools |
| ERPNext | Financial system of record for the demo |
| Vendor Master | Trusted vendor information |

## End-to-End Business Process

```text
Vendor sends invoice
        |
        v
Invoice Intake: Email / PDF / API / Form
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
| Valid PO + known vendor + matching bank + low risk | Auto-process |
| Small PO variance | Apply deterministic policy |
| Missing PO | Human review |
| Duplicate invoice | Reject or review |
| Bank account changed | Block + review |
| Compliance block | Block + compliance review |
| Low extraction confidence | Human review |
| Critical tool unavailable | Fail closed / review |
| Model uncertainty high | Human review |

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

The reviewer receives the original document, extracted fields, vendor record, PO data, tool results, risk indicators, reason codes and recommended action.

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
RISK_HIGH
PAYMENT_BLOCKED
HUMAN_TASK_CREATED
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
| Human override rate | Agent recommendations changed by people |
| Cost per invoice | Operational processing cost |
| Tool failure rate | External integration reliability |

## Reusable Business-Agent Pattern

The same architecture can later support vendor onboarding, contract compliance, expenses, procurement, claims, customer onboarding and compliance investigations.