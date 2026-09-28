# ProcureGuard — Technical Architecture

## Architecture Overview

ProcureGuard uses layered architecture separating workflow orchestration, AI reasoning, business tools, deterministic policy, enterprise integration and AMD-hosted inference.

```text
INPUTS: Email | PDF | API | Web Form | Chat
                    |
                    v
+------------------------------------------------+
| EVOLUS                                         |
| Workflow | Case Management | Human Tasks       |
+----------------------+-------------------------+
                       |
                       v
+------------------------------------------------+
| AGENT SERVICE                                  |
| FastAPI | Pydantic | LangGraph/PydanticAI      |
| State | Planner | Tool Router                  |
+----------------------+-------------------------+
                       |
          +------------+-------------+
          |            |             |
          v            v             v
   Business Tools  Policy Engine  Retrieval/Data
   ERP/Vendor/PO   Thresholds     Policies/Context
          |            |             |
          +------------+-------------+
                       |
                       v
                Model Gateway
                       |
                       v
              vLLM / SGLang
                       |
                       v
              Open Model + ROCm
                       |
                       v
                    AMD GPU
```

## Evolus Responsibilities

Evolus owns the durable business process: case creation, workflow state, AI invocation, decision routing, human tasks, business exceptions and completion tracking. The agent complements Evolus rather than replacing it.

## Agent Service

Recommended stack:

```text
Python
FastAPI
Pydantic
PydanticAI and/or LangGraph
HTTPX
PostgreSQL
Redis
OpenTelemetry
```

Example API:

```http
POST /v1/invoices/analyze
```

Example result:

```json
{
  "case_id": "CASE-92381",
  "decision": "HUMAN_REVIEW",
  "risk_level": "HIGH",
  "reason_codes": ["BANK_ACCOUNT_MISMATCH"],
  "confidence": 0.98,
  "recommended_action": "VERIFY_VENDOR_BANK_INFORMATION"
}
```

## Structured Agent State

```python
class InvoiceAgentState(BaseModel):
    case_id: str
    invoice: Invoice
    vendor: Vendor | None = None
    purchase_order: PurchaseOrder | None = None
    duplicate_check: CheckResult | None = None
    po_validation: CheckResult | None = None
    bank_validation: CheckResult | None = None
    compliance_result: CheckResult | None = None
    risk_score: float | None = None
    decision: Decision | None = None
    tool_history: list[ToolExecution] = []
```

Agent execution should be inspectable and persist business state independently of conversation history.

## Agent Graph

```text
START
  |
UNDERSTAND_INVOICE
  |
PLAN
  +--> GET_VENDOR
  +--> GET_PO
  +--> DUPLICATE_CHECK
  +--> BANK_CHECK
  +--> COMPLIANCE_CHECK
             |
       COLLECT_RESULTS
             |
        POLICY_ENGINE
          /  |  \
   APPROVE REVIEW REJECT
          \  |  /
            END
```

Independent read-only tools may execute concurrently.

## Tool Architecture

Tools are the security boundary between the LLM and enterprise systems. The model never receives unrestricted database credentials.

Each tool should provide strongly typed input/output, authentication, authorization, timeouts, retries, idempotency, audit logging and validation.

| Tool | Purpose |
|---|---|
| `get_vendor` | Retrieve trusted vendor record |
| `get_purchase_order` | Retrieve PO |
| `check_duplicate_invoice` | Detect duplicate |
| `validate_po` | Compare invoice and PO |
| `verify_bank_account` | Validate payment information |
| `check_vendor_risk` | Retrieve risk/compliance data |
| `calculate_risk` | Calculate normalized risk |
| `create_erp_invoice` | Create ERPNext transaction |
| `create_human_task` | Escalate through Evolus |
| `send_notification` | Notify stakeholder |

## AMD Model Architecture

```text
ProcureGuard Agent
       |
OpenAI-compatible API
       |
Model Gateway
       |
vLLM / SGLang
       |
Qwen / Llama / Mistral
       |
ROCm
       |
AMD GPU
```

Model selection should consider tool-calling reliability, structured-output accuracy, context length, latency, memory requirements and runtime compatibility.

## Structured Decisions

Natural-language parsing should not control workflow routing. Model output is validated against schemas.

```python
class AgentDecision(BaseModel):
    decision: Literal["APPROVE", "HUMAN_REVIEW", "REJECT", "REQUEST_INFORMATION"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    reason_codes: list[str]
    explanation: str
    confidence: float
```

## Policy Engine

The policy engine is deterministic.

```python
if bank_account_changed:
    return Decision.HUMAN_REVIEW
if sanctions_match:
    return Decision.REJECT
if invoice_amount > auto_approval_limit:
    return Decision.HUMAN_REVIEW
if extraction_confidence < MIN_CONFIDENCE:
    return Decision.HUMAN_REVIEW
```

Final workflow decisions combine AI findings, verified tool results and deterministic policy.

## Idempotency

All state-changing operations carry idempotency keys such as:

```text
CASE-92381:CREATE_ERP_INVOICE
```

Retries return the previous result rather than creating duplicate transactions.

## Concurrency

Database constraints remain the final source of truth. A unique `(vendor_id, invoice_number)` constraint prevents duplicate invoices. Distributed workers may use PostgreSQL locking patterns such as `FOR UPDATE SKIP LOCKED` when claiming queued work.

## Security Model

```text
LLM
 |
 | no direct enterprise access
 v
Tool Layer
 |- Authentication
 |- Authorization
 |- Schema validation
 |- Business validation
 |- Rate limiting
 |- Audit logging
 |- Idempotency
 v
Enterprise Systems
```

Invoice content is untrusted input. Text embedded inside a document can never override system policy, tool authorization or workflow controls.

## Observability

Every execution should correlate `case_id`, `trace_id`, `agent_run_id`, `model_request_id` and `tool_call_id`. OpenTelemetry traces Evolus invocation, model calls, tool executions, policy evaluation and final workflow decisions.

Recommended metrics include model latency, tokens, tool latency/failure rate, end-to-end processing time, tool count, escalation rate, human override rate and AMD GPU utilization.

## Audit Events

Store business evidence rather than model chain-of-thought.

```json
{
  "case_id": "CASE-92381",
  "actor_type": "AI_AGENT",
  "event_type": "RISK_DETECTED",
  "reason_code": "BANK_ACCOUNT_MISMATCH",
  "evidence": {
    "vendor_account_last4": "3921",
    "invoice_account_last4": "8219"
  }
}
```

## Failure Handling

Financial workflows fail closed. Model timeouts or invalid structured output may be retried. ERP timeouts use idempotent retries. Missing critical data, unavailable compliance services, low extraction confidence and unknown states route to human review.

## Deployment

```text
Evolus
  |
HTTPS / API Gateway
  |
Agent Service --------------------+
  |                               |
PostgreSQL / Redis          Model Gateway
                                  |
                             vLLM/SGLang
                                  |
                            Open Model
                                  |
                                ROCm
                                  |
                              AMD GPU
```

## Core Architectural Principle

> **The model reasons. Tools act. Policies govern. Evolus orchestrates. Humans remain in control of exceptions.**