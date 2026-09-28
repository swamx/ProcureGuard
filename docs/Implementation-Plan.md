# ProcureGuard — Implementation Plan

## Target

| Item | Detail |
|---|---|
| Event | AMD Developer Hackathon: ACT III (lablab.ai) |
| Track | **Evolus Business Agents on AMD** |
| Build window | Mon Oct 12, 2026 15:00 UTC → **Sun Oct 18, 2026 15:00 UTC** |
| On-site | Oct 17–18 (Rome, Milan, Imperia) — optional |
| Judging | Application of Technology, Presentation, Business Value, Originality |

The track asks for an agent that takes a real business input, reasons with an **open model served on AMD**, and acts by running an Evolus workflow, turning documents into data, using AI Tools, updating another system, or handing a case to a person. ProcureGuard demonstrates all of those in one Accounts Payable workflow.

## Strategy

Evolus owns the visible business process: email intake, case state, workflow branching, human review and notifications. ProcureGuard exposes controlled AI Tools for AMD-powered invoice extraction, ERPNext checks, deterministic fraud/policy evaluation and guarded ERP writes.

The story is **vendor-payment fraud**, not generic invoice OCR. The headline scenario combines a lookalike sender domain with a changed bank account; the security scenario demonstrates a document-layer prompt injection that attempts to corrupt extraction.

## Non-Negotiable Vertical Slice

Before implementing secondary scenarios, complete this path from a real input to a real system action:

```text
Real invoice email
      |
Evolus email trigger
      |
AMD-hosted open model
      |
mandatory AI Tools
      |
deterministic policy
      |
Evolus workflow decision
      |
ERPNext Purchase Invoice
```

**Do not begin CASE-003 or CASE-004 until CASE-001 works end-to-end through Evolus and ERPNext.** This prevents the project from becoming a strong Python demo with Evolus only represented in an architecture diagram.

## Key Decisions

| Decision | Choice | Why |
|---|---|---|
| Orchestration | Evolus | Required by track and must be visible in demo |
| Agent framework | PydanticAI | Typed tools/outputs and low setup cost |
| Model serving | vLLM on ROCm | OpenAI-compatible serving on AMD |
| Model | **Reliability-gated Qwen VL candidate** | Choose after spike; parameter count is secondary to correctness/latency |
| Candidate large model | 70B-class Qwen VL if stable | Tests the MI300X advantage but is not a commitment |
| Fallback | Smaller Qwen VL candidate | Use if it is more reliable, faster or more economical |
| ERP | ERPNext in Docker | Real Supplier / PO / Purchase Invoice entities |
| State and audit | PostgreSQL | Cases, audit, idempotency and evaluation results |
| Dropped from MVP | Redis, full OTel, SGLang, LangGraph, CORD/SROIE benchmark, document router | Scope control |

## Model Selection Gate

The rule is:

> **Use the largest model that meets the reliability and latency gate — not the largest model that fits in memory.**

Run candidate models on the same synthetic evaluation subset. Record:

- Schema-valid structured-output rate.
- Tool selection and argument correctness.
- Invoice-field extraction accuracy.
- Unsafe auto-approvals — must be **0**.
- Injection containment — target **100%**.
- p50/p95 latency.
- Throughput and GPU memory/utilization.

Schema/tool/extraction thresholds are set from the pre-event spike based on observed capability rather than invented beforehand. If a smaller model is operationally stronger than the 70B-class candidate, select the smaller model.

## Mandatory Controls

Straight-through approval requires all applicable controls:

```text
Extraction integrity
Vendor lookup/status
Purchase-order validation
Duplicate check
Bank-account validation
Vendor-risk check
Sender-domain validation for email cases
```

The model can select additional tools, but it cannot skip mandatory controls. `evaluate_case` returns `REQUIRED_CHECK_MISSING -> HUMAN_REVIEW` whenever a required result is absent.

## Headline Fraud Policy

CASE-002 uses deterministic evidence and policy. Example demo weights:

```text
SENDER_DOMAIN_MISMATCH  +40
BANK_ACCOUNT_MISMATCH   +60
```

The combined headline case therefore scores 100. These weights are configuration, not model output. Hard conditions such as a changed bank account can force review independently of the aggregate score.

## Open Questions — Blocking

| # | Question | Needed by | Impact |
|---|---|---|---|
| Q1 | Can an Evolus agent use our custom OpenAI-compatible vLLM endpoint? | Oct 5 | Chooses Plan A vs Plan B |
| Q2 | Can Evolus call external HTTP APIs as AI Tools and pass attachments? | Oct 5 | Determines tool wiring |
| Q3 | Does Evolus built-in extraction run on a model we choose? | Oct 5 | Determines extraction placement |
| Q4 | Can Evolus create a human task with attachments/structured fields and resume after reviewer choice? | Oct 5 | Required for CASE-002 |
| Q5 | Is code/infrastructure written before Oct 12 allowed? | Oct 5 | Limits pre-event implementation |
| Q6 | GPU credits and AMD Developer Cloud instance type | Kickoff | GPU budget |
| Q7 | Exact submission fields | Kickoff | Final checklist |

**Q1–Q4 are the highest-priority work items. Resolve them before investing in nonessential implementation.**

## Phase 0 — Before Event

| When | Task | Done when |
|---|---|---|
| Sep 29 – Oct 2 | Register, AMD AI Developer Program, Discord, Evolus access | Accounts active |
| Sep 29 – Oct 5 | Resolve Q1–Q5 | Plan A/B chosen; integration contract known |
| Oct 1 – Oct 4 | ERPNext Docker + Nova Industries seed | `make seed` restores demo state |
| Oct 3 – Oct 9 | AMD model spike across candidate sizes | Model selected using gate; measurements saved |
| Oct 5 – Oct 9 | Generate five demo cases + evaluation data | Ground truth committed/generated reproducibly |
| Oct 10 – Oct 11 | Evolus spike: email -> HTTP tool -> human task | Round trip proven |

If pre-event code is prohibited, limit work accordingly and keep spikes disposable.

## Phase 1 — Build Week

| Day | Focus | Exit criterion |
|---|---|---|
| **Mon Oct 12** | Repo scaffold, ERPNext client, Evolus email trigger, minimal service | Real email reaches service through Evolus |
| **Tue Oct 13** | AMD extraction, mandatory checks, completeness gate, policy, guarded/idempotent ERP write | **CASE-001 fully end-to-end** through Evolus -> ERPNext |
| **Wed Oct 14** | CASE-002 lookalike + bank-change fraud; human review; trusted-contact verification | Headline fraud demo passes repeatedly |
| **Thu Oct 15** | CASE-005 document-layer injection + audit evidence | Injection contained in repeated runs |
| **Fri Oct 16 AM** | CASE-003 duplicate; CASE-004 variance only after core cases stable | Secondary cases pass |
| **Fri Oct 16 PM** | Evaluation batch; metrics; **feature freeze 18:00 UTC**; fallback video | Measured results captured |
| **Sat Oct 17** | Slides, video, README results, deployment, showcase | Draft submission saved |
| **Sun Oct 18** | Buffer only; submit by 12:00 UTC | Submitted |

Cut order if behind: metrics UI -> drafted vendor email -> CASE-004 -> CASE-003 -> shrink evaluation set. **Never cut CASE-001, CASE-002 or CASE-005.**

## Workstreams

| Workstream | Scope |
|---|---|
| A — Evolus | Email trigger, workflow, AI Tool wiring, human task, notifications |
| B — Service | FastAPI, tools, ERPNext client, mandatory controls, policy, idempotency, audit |
| C — AMD | vLLM deployment, candidate evaluation, extraction, injection test, GPU metrics |
| D — Story | Synthetic data, demo, slides, video, submission |

## Evaluation

### Primary Safety Metric

**Unsafe Straight-Through Rate (USTR)**

```text
unsafe/suspicious/invalid cases auto-approved
----------------------------------------------
all unsafe/suspicious/invalid cases
```

Target: **0%**.

### Automation Metric

**Legitimate Straight-Through Processing Rate (STP)**

```text
legitimate cases automatically completed
------------------------------------------
all legitimate cases
```

Once USTR is zero, maximize legitimate STP without weakening controls.

### Report Format

Use a decision confusion matrix:

| Actual | Auto Approve | Human Review | Reject |
|---|---:|---:|---:|
| Safe | measured | measured | measured |
| Suspicious | **0 target** | measured | measured |
| Fraud / invalid | **0 target** | measured | measured |

Also report extraction-field accuracy, escalation recall, false-escalation rate, injection containment, p50/p95 latency, throughput and GPU utilization.

## AMD Evidence

Capture:

- Exact selected model, parameter count and precision.
- Single-MI300X deployment when applicable.
- `rocm-smi` memory/utilization during evaluation.
- Candidate comparison showing why the selected model won.
- Batch evaluation throughput and p50/p95 latency.
- USTR, legitimate STP, extraction accuracy and injection containment.

This creates a stronger AMD story than parameter count alone: AMD hosts a measured, production-style agent workload and enables model-size experimentation.

## GPU Budget

Keep large candidates running only during spikes, evaluation, rehearsal and live demo. Log every GPU session. Keep the selected fallback image/config ready for fast recovery.

## Submission Checklist

Confirm against the actual form at kickoff:

- [ ] Project title and concise fraud-focused description
- [ ] Long description covering Evolus and AMD roles
- [ ] Technology tags
- [ ] Cover image
- [ ] <=3 minute presentation video
- [ ] Slide deck
- [ ] Public GitHub repository and setup instructions
- [ ] Demo URL if required
- [ ] Measured evaluation results
- [ ] AMD metrics and selected-model rationale

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Evolus cannot use custom AMD endpoint | Medium | Plan B: Evolus calls ProcureGuard, which calls AMD |
| External AI Tools/attachments unsupported | Medium | Resolve Q2 early; adapt API boundary |
| Human-task semantics insufficient | Medium | Resolve Q4 early; simplify reviewer interaction if needed |
| Large model unstable/slow | Medium | Reliability gate; smaller candidate can win |
| GPU credits exhausted | Medium | Session log, stop instances, fallback candidate |
| ERPNext consumes build time | High without prep | Docker + deterministic seed |
| Live demo failure | Medium | Fresh seed, pre-warm, fallback recording |
| Invoice-agent competition | High | Lead with fraud + document-layer injection + measured safety |
| Pre-built code disallowed | Unknown | Respect official rules and constrain Phase 0 accordingly |

## Build Discipline

The project wins by showing one complete business process, not by accumulating frameworks. Do not add infrastructure or secondary scenarios unless they improve a judging criterion or reduce demo risk.