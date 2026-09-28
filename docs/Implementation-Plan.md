# ProcureGuard — Implementation Plan

## Target

| Item | Detail |
|---|---|
| Event | AMD Developer Hackathon: ACT III (lablab.ai) |
| Track | **Evolus Business Agents on AMD** (track partner: Evolus) |
| Build window | Mon Oct 12, 2026 15:00 UTC → **Sun Oct 18, 2026 15:00 UTC** (submission deadline) |
| On-site | Oct 17–18 (Rome, Milan, Imperia) — optional, travel not covered |
| Judging | Application of Technology, Presentation, Business Value, Originality |

The track asks for an agent that takes a real business input, reasons over it with an **open model served on AMD**, and acts by **running an Evolus workflow, turning documents into data, using AI Tools, updating another system, or handing the case to a person**. ProcureGuard is designed to show every one of those verbs in a single case.

## Strategy in One Paragraph

Evolus owns the business process: email intake, workflow, the human review task and notifications. ProcureGuard is a small service that exposes **AI Tools** to Evolus: invoice extraction on the AMD-hosted model, vendor/PO/duplicate/bank/sender checks against ERPNext, the deterministic policy engine and a guarded ERP write. The story is **invoice payment fraud**, not invoice OCR, because invoice processing is Evolus's own marketing example and other teams will build it. We win on the fraud scenario (lookalike-domain email + bank change), on a real prompt-injection defence, and on measured AMD results.

## Key Decisions

| Decision | Choice | Why |
|---|---|---|
| Orchestration | Evolus (required by track) | Judges are the track partner; Evolus must do visible work |
| Agent framework | PydanticAI | Typed tools and outputs; less setup than LangGraph |
| Model serving | vLLM on ROCm | Most mature OpenAI-compatible server on AMD |
| Model | 70B-class Qwen vision-language model on one MI300X (final pick after the Oct 9 spike) | One model handles both scanned-invoice reading and tool calling; 192 GB HBM makes this an AMD-specific claim |
| Fallback model | 7B–8B Qwen vision-language model | Keeps the demo alive if the large model is unstable or credits run low |
| ERP | ERPNext in Docker | Real Supplier / Purchase Order / Purchase Invoice records |
| State and audit | PostgreSQL | One store for cases, idempotency keys and audit events |
| Dropped from MVP | Redis, full OpenTelemetry tracing, SGLang, LangGraph, CORD/SROIE benchmarks, digital-vs-scan document router | Scope; none of them move a judging criterion within 6 days |

## Open Questions (Blocking)

| # | Question | Needed by | Where to ask | Impact |
|---|---|---|---|---|
| Q1 | Can an Evolus agent use a **custom OpenAI-compatible endpoint** (our vLLM server)? | Oct 5 | Evolus docs, lablab Discord, track partner | Chooses Plan A or Plan B (see [Technical Architecture](Technical-Architecture.md#evolus-integration-plans)) |
| Q2 | Can Evolus call **external HTTP APIs as AI Tools** and pass file attachments to them? | Oct 5 | Same | Determines how extraction and checks are wired |
| Q3 | Does Evolus's built-in document extraction run on a model we choose? | Oct 5 | Same | If not, extraction runs as our `extract_invoice` tool so the document-to-data step is still on AMD |
| Q4 | Can Evolus create a **human task** with attachments and structured fields, and resume the workflow on the reviewer's choice? | Oct 5 | Same | Core of CASE-002 |
| Q5 | Is code or infrastructure written **before** Oct 12 allowed? | Oct 5 | Official rules / Discord | Until confirmed, pre-event work is limited to environment setup, synthetic data and throwaway spikes |
| Q6 | GPU credits and instance type on AMD Developer Cloud for ACT III | Kickoff | Event page | GPU-hour budget (ACT II gave $100 in AMD GPU credits; assume similar) |
| Q7 | Exact submission fields | Kickoff | Submission form | Final checklist below |

## Phase 0 — Before the Event (Sep 29 – Oct 11)

| When | Task | Done when |
|---|---|---|
| Sep 29 – Oct 2 | Register, create AMD AI Developer Program account, join Discord, request Evolus access | Accounts active |
| Sep 29 – Oct 5 | Answer Q1–Q5 | Plan A or B chosen and written down |
| Oct 1 – Oct 4 | ERPNext in Docker; seed Nova Industries (suppliers, POs, one paid invoice for CASE-003) with a seed script | `make seed` rebuilds the demo state from scratch |
| Oct 3 – Oct 9 | Model spike on AMD Developer Cloud: vLLM ROCm image, candidate large model and fallback, measure tool-call reliability and extraction on 20 synthetic invoices | Model picked; numbers recorded |
| Oct 5 – Oct 9 | Generate synthetic invoice PDFs and emails for the 5 demo cases plus the 100-case evaluation set, with ground-truth JSON | `data/` populated per [Open-Source & Datasets](Open-Source-and-Datasets.md#suggested-data-layout) |
| Oct 10 – Oct 11 | Evolus spike: email trigger → HTTP call → human task, with a dummy tool | Round trip works |

If Q5 says prior code is allowed, also scaffold the FastAPI service and ERPNext client in Phase 0.

## Phase 1 — Build Week

| Day | Focus | Exit criterion |
|---|---|---|
| **Mon Oct 12** (from 15:00 UTC) | Repo scaffold; FastAPI service; ERPNext client; read-only tools; Evolus workflow skeleton | Evolus email trigger reaches the service and gets back a stub decision |
| **Tue Oct 13** | `extract_invoice` on the AMD model + text-layer cross-check; policy engine + completeness gate; `create_purchase_invoice` with idempotency | **CASE-001 end to end**: email → Evolus → AMD → ERPNext Purchase Invoice |
| **Wed Oct 14** | `verify_sender_domain`, `create_review_task`, `request_vendor_verification`; duplicate and PO-variance rules | **CASE-002, 003, 004** pass |
| **Thu Oct 15** | CASE-005 hidden-text injection; audit event table; reviewer view of evidence in Evolus | All 5 demo cases pass three runs in a row from a fresh seed |
| **Fri Oct 16** | 100-case evaluation run as a batch on MI300X; metrics panel; **feature freeze 18:00 UTC**; first rehearsal; record fallback video | Evaluation table and latency/throughput numbers captured |
| **Sat Oct 17** | Slides, final video, README, public demo deployment; on-site showcase if attending | Draft submission saved |
| **Sun Oct 18** | Buffer only. **Submit by 12:00 UTC** (3 hours before deadline) | Submitted |

Cut order if behind schedule: metrics panel → `request_vendor_verification` (show as a drafted email only) → CASE-004 → 100-case evaluation shrinks to 30 cases. **Never cut** CASE-001, CASE-002 or CASE-005.

## Workstreams

Assign an owner to each; one person can hold several on a small team.

| Workstream | Scope |
|---|---|
| A — Evolus | Workflows, email trigger, AI Tool wiring, human review task, notifications |
| B — Service | FastAPI, tools, ERPNext client, policy engine, idempotency, audit |
| C — AMD model | vLLM deployment, extraction prompts, cross-check, evaluation harness, GPU metrics |
| D — Story | Synthetic data, demo script, slides, video, submission |

## AMD Evidence to Capture

The "Application of Technology" score depends on showing AMD doing work only AMD-class hardware makes easy:

- Model name, size and precision served from a **single MI300X**, with `rocm-smi` memory use on screen.
- Batch run of the 100-case evaluation: invoices per minute, p50/p95 latency per case, GPU utilisation.
- Evaluation table: extraction field accuracy, decision accuracy, escalation recall, false-escalation rate, **wrong auto-approvals (target: 0)**, injection cases contained.
- All numbers measured, never typed in by hand.

## GPU Budget

- Keep the large model running only during spikes, the evaluation run, rehearsal and the live demo; stop the instance otherwise.
- Record every GPU session (start, stop, purpose) so credits do not run out on Oct 17.
- Keep the fallback model image ready to start in under 10 minutes.

## Submission Checklist

Confirm against the actual form at kickoff (Q7). Typical lablab submissions ask for:

- [ ] Project title and short description
- [ ] Long description (problem, solution, Evolus usage, AMD usage)
- [ ] Technology tags (Evolus, AMD, ROCm, vLLM, model name)
- [ ] Cover image
- [ ] Video presentation (≤ 3 min, follows [Demo Scenario](Demo-Scenario.md#3-minute-presentation))
- [ ] Slide deck
- [ ] Public GitHub repository with setup instructions
- [ ] Demo application URL
- [ ] Evaluation results and AMD metrics in the README

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Evolus cannot use our AMD endpoint | Medium | Plan B: Evolus calls ProcureGuard, which calls the AMD model |
| Large model unstable or slow on ROCm | Medium | Decide at the Oct 9 spike; fallback model ready |
| GPU credits exhausted | Medium | GPU session log; stop instances; fallback model |
| ERPNext setup eats build time | High without prep | Docker + seed script finished in Phase 0 |
| Live demo failure | Medium | Fresh-seed script, pre-warmed model, recorded fallback video |
| Other teams submit invoice agents | High | Lead with the fraud scenario and the injection defence, not extraction |
| Pre-built code disallowed | Unknown | Phase 0 limited to setup, data and spikes until Q5 is answered |
