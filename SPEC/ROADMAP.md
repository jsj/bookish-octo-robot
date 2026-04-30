# Roadmap

## Reference Point

Traversal is a useful market reference because it frames the category as **AI SRE for complex systems**.

The important lesson is not to copy Traversal feature-for-feature. The lesson is that the buyer value ladder is:

1. Alert intelligence
2. Root cause analysis
3. Safe remediation
4. Self-healing
5. Production feedback into engineering

This project should adapt that ladder for a different wedge:

> Open-source, Kubernetes-first, read-only-first cluster guardianship.

## Product Position

Traversal appears to sell enterprise AI SRE outcomes across broad infrastructure.

This project should start narrower and sharper:

- Kubernetes-native
- Self-hostable
- Inspectable
- Read-only by default
- Evidence-first
- Emulator-validated
- Extensible by operators

The goal is not "FOSS Traversal." The goal is to own the open Kubernetes cluster guardian lane.

## Roadmap Principles

- Start with trust before automation.
- Prefer evidence-backed diagnosis over flashy remediation.
- Make every answer inspectable.
- Use emulator scenarios to expose fidelity and reasoning gaps before production.
- Treat remediation as a separate trust boundary.
- Keep `kubectl` compatibility as a reference point, not the product experience.

## Phase 1: Evidence-Backed Cluster Assessment

Goal: answer "what is wrong and why should I believe you?"

Capabilities:

- Gather context from pods, deployments, services, ingresses, PVCs, nodes, events, RBAC, and K8sGPT.
- Produce a concise assessment with cited evidence.
- Separate primary causes from secondary symptoms.
- Show uncertainty when evidence is incomplete.
- Keep all actions read-only.

Validation:

- Emulator scenarios for CrashLoopBackOff, unschedulable pods, NotReady nodes, missing endpoints, pending PVCs, and rollout failures.
- Tests should exercise real Kubernetes client paths, not static Python-only mocks.

## Phase 2: Alert Intelligence

Goal: reduce noisy signals into prioritized investigation starting points.

Capabilities:

- Introduce the runtime heartbeat as a background sense-making loop.
- Ingest or poll K8sGPT results, events, and health signals.
- Group related symptoms by namespace, workload, node, or service.
- Rank severity using evidence, not only keyword matching.
- Explain why a signal matters now.

Potential integrations:

- Prometheus alerts
- Loki log excerpts
- Grafana links
- K8sGPT Result CRDs

Validation:

- Emulator scenarios with multiple simultaneous issues where only one is causal.
- Tests for deduplication, severity ranking, and incident grouping.
- Timeline-based emulator scenarios that prove the heartbeat tracks deltas rather than repeating cron snapshots.

## Phase 3: Root Cause Analysis Workflow

Goal: move from "resource summary" to "causal investigation."

Capabilities:

- Trace from symptom to workload to dependency to recent change.
- Connect deployments, pods, services, endpoints, ingresses, nodes, PVCs, and events.
- Identify likely causal chain.
- Produce a structured RCA:
  - Summary
  - Evidence
  - Likely cause
  - Contributing factors
  - Safe next checks
  - Unknowns

Validation:

- Emulator scenarios with misleading secondary symptoms.
- Golden assessments for known incidents.
- Regression tests that fail if answers become less evidence-backed.

## Phase 4: Guarded Remediation Recommendations

Goal: recommend safe next steps without crossing into unsafe automation.

Capabilities:

- Recommend read-only commands or checks first.
- Classify remediation by risk.
- Require explicit user approval for mutating actions.
- Prefer reversible or low-blast-radius steps.
- Generate runbook-style remediation plans.

Validation:

- Policy tests that block destructive or broad mutations.
- Emulator scenarios where the correct answer is "do not act yet."

## Phase 5: Optional Self-Healing

Goal: only after trust exists, automate narrow, reversible fixes.

Candidate actions:

- Restart a known-safe failed controller in a dev namespace.
- Reconcile a stale read-only diagnostic cache.
- Trigger a pre-approved runbook.

Non-goals until proven:

- General-purpose autonomous cluster mutation.
- Broad production self-healing.
- Any write action without policy, audit, and approval boundaries.

Validation:

- Explicit policy gates.
- Audit logs.
- Dry-run mode.
- Emulator-backed mutation simulations before any live-cluster action.

## Phase 6: Production Feedback Into Engineering

Goal: turn incidents into better code, manifests, runbooks, and tests.

Capabilities:

- Save resolved incidents as knowledge base entries.
- Generate emulator scenarios from real incident shape.
- Link failures to deployments, manifests, or recent changes.
- Suggest tests or guardrails that would have caught the issue earlier.

Validation:

- Every recurring incident should create or update a scenario.
- The emulator library becomes a living regression suite for operational knowledge.

## Differentiation From Traversal

Traversal-style promise:

> AI SRE agents for enterprise-scale complex systems.

This project's promise:

> Open Kubernetes cluster guardian that gives inspectable, evidence-backed diagnosis before action.

Differentiators:

- Open-source and self-hostable.
- Kubernetes-first depth instead of broad infrastructure breadth.
- Read-only-first trust model.
- Local emulator-backed validation.
- Operator-extensible scenarios.
- Transparent evidence chain.

## Near-Term Priorities

1. Strengthen assessment quality:
   - structured RCA output
   - evidence citations
   - uncertainty section

2. Expand emulator scenarios:
   - missing service endpoints
   - ingress backend mismatch
   - rollout deadline exceeded
   - pending PVC
   - node pressure and taints
   - RBAC denied reads

3. Add alert grouping:
   - K8sGPT plus events
   - group by workload and namespace
   - identify top causal candidate

4. Build a golden assessment suite:
   - scenario input
   - expected issue
   - expected evidence
   - forbidden unsafe recommendation

5. Keep remediation guarded:
   - read-only recommendations first
   - mutating actions require explicit product policy later

## What Not To Do Yet

- Do not lead with self-healing.
- Do not turn the product into a generic chat shell.
- Do not make the emulator the product.
- Do not chase every observability integration before the RCA loop is strong.
- Do not optimize for impressive demos at the cost of evidence quality.
