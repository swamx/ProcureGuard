# ProcureGuard — Proposal

## Autonomous Vendor Invoice & Compliance Agent on Evolus + AMD

**Project Type:** Agentic Business Process Automation  
**Platform:** Evolus  
**AI Runtime:** Open model served on AMD  
**Domain:** Accounts Payable, Procurement, Vendor Risk & Compliance

## Executive Summary

ProcureGuard is an AI-powered business agent that automates vendor invoice processing from receipt through payment approval. Organizations receive invoices through email, PDFs, portals and APIs. Processing normally requires employees to extract invoice data, identify vendors, locate purchase orders, validate amounts and payment details, assess risk, update enterprise systems and decide whether a transaction can proceed.

ProcureGuard combines **Evolus** for email intake, workflow, human review tasks and notifications, an **open model running on AMD** for document understanding and agent reasoning, controlled **AI Tools** for enterprise operations, **ERPNext** as the demonstration ERP, deterministic policies for financial controls, and **human-in-the-loop** review for high-risk or ambiguous cases.

The objective is not simply to use an LLM to read invoices — invoice extraction is a common demo. The objective is to let an AI agent safely run a real business process end to end **and stop invoice payment fraud**: a vendor lookalike emailing a genuine-looking invoice with new bank details.

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

An invoice email arrives in the AP mailbox. An Evolus email trigger creates a case and hands the attachment to the agent, which reasons with an open model on AMD, turns the document into data and calls ProcureGuard's AI Tools. A deterministic policy engine decides; the Evolus workflow then creates the ERPNext Purchase Invoice, opens a review task for a person, or rejects the invoice.

Tools (full catalogue in [Technical Architecture](Technical-Architecture.md#tool-catalogue)):

```text
extract_invoice()
get_vendor()
get_purchase_order()
check_duplicate_invoice()
validate_invoice_against_po()
verify_bank_account()
verify_sender_domain()
check_vendor_risk()
evaluate_case()
create_purchase_invoice()
create_review_task()
request_vendor_verification()
send_notification()
```

The model does not directly manipulate enterprise databases. Tools form the controlled boundary for external actions, and write tools are triggered by the Evolus workflow only after a decision.

## Example Risk Scenario

An email arrives from `billing@acme-logistlcs.com` — one letter away from the vendor's real domain, `acme-logistics.com` — saying the vendor has changed banks. The attached invoice is extracted as:

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

The trusted vendor master contains approved bank account `****3921`. The PO and amount are valid, but the payment account has changed and the sender is not the vendor. ProcureGuard must not process the transaction automatically.

Expected result:

```json
{
  "decision": "HUMAN_REVIEW",
  "risk_level": "CRITICAL",
  "reason_codes": ["BANK_ACCOUNT_MISMATCH", "SENDER_DOMAIN_MISMATCH"],
  "recommended_action": "VERIFY_VIA_KNOWN_CONTACT"
}
```

Evolus blocks the payment, opens a review task for Accounts Payable with the evidence, and sends a verification request to the vendor's contact on file — never to the email's reply-to address.

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

### Fraud-First, Not OCR-First

The headline scenario is a realistic payment-fraud attempt, and the injection defence works even if the model is fooled: extracted values are cross-checked against the document's text layer and the vendor master.

### Tool-Based Security

The model can only interact with approved, strongly typed and auditable tools, and the ERP write is refused without a stored approval.

### Explainable Decisions

Business decisions produce evidence and reason codes rather than relying on hidden model reasoning.

## MVP Scope

- Invoice email intake through an Evolus email trigger (PDF upload as secondary)
- Structured extraction on the AMD model with text-layer cross-check
- Vendor lookup and PO lookup/comparison
- Duplicate detection
- Bank-account and sender-domain validation
- Basic vendor risk checks
- Deterministic policy engine with completeness gate
- Automatic processing of safe cases
- Evolus review task for risky cases, plus vendor verification via the contact on file
- ERPNext Purchase Invoice creation
- Notifications
- Audit trail
- Hidden-text prompt-injection scenario
- 100-case evaluation run on AMD with measured metrics

Delivery timeline: see [Implementation Plan](Implementation-Plan.md).

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
Lookalike email -> Extract -> Vendor -> PO -> Bank + Sender Mismatch
                -> Critical Risk -> Payment Block -> Review Task + Vendor Verification
```

### Safety Target

Zero wrong auto-approvals across the evaluation set.

## Business Value

Potential benefits include lower manual data-entry effort, faster invoice processing, earlier duplicate detection, improved payment-fraud controls, automated compliance checks, better auditability and greater AP scalability.

## Vision

Invoice processing establishes a reusable pattern for vendor onboarding, procurement, contract review, expenses, customer onboarding, insurance claims, compliance investigations and other document-heavy enterprise workflows.