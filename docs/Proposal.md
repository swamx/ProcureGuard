# ProcureGuard — Proposal

## Autonomous Vendor Invoice & Compliance Agent on Evolus + AMD

**Project Type:** Agentic Business Process Automation  
**Platform:** Evolus  
**AI Runtime:** Open model served on AMD  
**Domain:** Accounts Payable, Procurement, Vendor Risk & Compliance

## Executive Summary

ProcureGuard is an AI-powered business agent that automates vendor invoice processing from receipt through payment approval. Organizations receive invoices through email, PDFs, portals and APIs. Processing normally requires employees to extract invoice data, identify vendors, locate purchase orders, validate amounts and payment details, assess risk, update enterprise systems and decide whether a transaction can proceed.

ProcureGuard combines **Evolus** for durable workflow orchestration, an **open model running on AMD** for document understanding and agent reasoning, controlled **AI tools** for enterprise operations, **ERPNext** as the demonstration ERP, deterministic policies for financial controls, and **human-in-the-loop** review for high-risk or ambiguous cases.

The objective is not simply to use an LLM to read invoices. The objective is to allow an AI agent to safely execute a real business process end-to-end.

## Business Problem

Accounts Payable teams repeatedly perform the same workflow:

1. Receive an invoice.
2. Open and understand the document.
3. Identify the vendor.
4. Extract invoice information.
5. Locate the purchase order.
6. Compare invoice and PO values.
7. Verify vendor payment information.
8. Detect duplicate invoices.
9. Determine whether approval is required.
10. Enter information into an ERP.
11. Contact the vendor when information is missing.
12. Escalate suspicious transactions.
13. Maintain an audit trail.

Traditional workflow automation handles predictable steps but struggles with unstructured documents, ambiguity and exceptions. ProcureGuard adds an AI reasoning layer while preserving deterministic business controls.

## Proposed Solution

An invoice enters through email, upload, API, web form or chat. Evolus creates a case and invokes document processing. The normalized invoice is passed to ProcureGuard, whose AMD-hosted open model determines what information is needed and selects approved tools.

Representative tools:

```text
get_vendor()
get_purchase_order()
check_duplicate_invoice()
validate_invoice_against_po()
verify_bank_account()
check_vendor_risk()
calculate_risk()
create_erp_invoice()
request_human_review()
send_notification()
```

The model does not directly manipulate enterprise databases. Tools form the controlled boundary for external actions.

## Example Risk Scenario

An invoice is extracted as:

```json
{
  "invoice_id": "INV-2026-1842",
  "vendor": "Acme Logistics Ltd",
  "po_number": "PO-89231",
  "amount": 48750.00,
  "currency": "USD",
  "bank_account_last4": "8219"
}
```

The trusted vendor master contains approved bank account `****3921`. The PO and amount are valid, but the payment account has changed. ProcureGuard must not process the transaction automatically.

Expected result:

```json
{
  "decision": "HUMAN_REVIEW",
  "risk_level": "HIGH",
  "reason_codes": ["BANK_ACCOUNT_MISMATCH"],
  "recommended_action": "BLOCK_PAYMENT_AND_VERIFY_VENDOR"
}
```

Evolus routes the case to Accounts Payable for review.

## Objectives

- Convert unstructured invoices into validated business objects.
- Use an open model on AMD for reasoning and tool selection.
- Execute a real business process through Evolus.
- Integrate with ERPNext and other controlled enterprise tools.
- Automatically process safe cases.
- Escalate high-risk or uncertain cases to people.
- Produce an auditable evidence trail.

## Key Differentiators

### AI Agent Rather Than Chatbot

ProcureGuard performs business operations instead of merely answering questions.

### End-to-End Process

The same case progresses from document intake through validation, decision, system update and notification.

### Responsible Autonomy

The system explicitly recognizes when automation must stop and human judgment is required.

### Tool-Based Security

The model can only interact with approved, strongly typed and auditable tools.

### Explainable Decisions

Business decisions produce evidence and reason codes rather than relying on hidden model reasoning.

## MVP Scope

- PDF invoice ingestion
- Structured extraction
- Vendor lookup
- PO lookup and comparison
- Duplicate detection
- Bank-account validation
- Basic vendor risk checks
- Risk classification
- Automatic processing of safe cases
- Human escalation of risky cases
- ERPNext Purchase Invoice creation
- Notifications
- Complete audit trail
- Prompt-injection security scenario

## Out of Scope

The hackathon MVP does not execute real bank transfers, implement full production SAP/Oracle integrations, provide global tax determination, or autonomously override high-value financial controls.

## Success Criteria

### Straight-Through Case

```text
Invoice -> Extract -> Vendor -> PO -> Duplicate Check -> Bank Check
        -> Low Risk -> ERPNext Purchase Invoice -> Complete
```

### Risk Case

```text
Invoice -> Extract -> Vendor -> PO -> Bank Mismatch
        -> High Risk -> Payment Block -> Human Review
```

## Business Value

Potential benefits include lower manual data-entry effort, faster invoice processing, earlier duplicate detection, improved payment-fraud controls, automated compliance checks, better auditability and greater AP scalability.

## Vision

Invoice processing establishes a reusable pattern for vendor onboarding, procurement, contract review, expenses, customer onboarding, insurance claims, compliance investigations and other document-heavy enterprise workflows.