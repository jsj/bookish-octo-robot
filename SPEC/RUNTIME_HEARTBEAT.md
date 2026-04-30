# Runtime Heartbeat

## Purpose

The heartbeat is the product's background sense-making loop.

It exists to avoid a naive cron pattern where the system periodically wakes up, dumps raw cluster state, and leaves humans or the LLM to rediscover context from scratch.

The heartbeat should maintain a living operational picture of the cluster so the guardian can answer from recent, structured, evidence-backed context.

## Problem: The Cron Loop

A cron-style loop tends to:

- Poll everything on a fixed interval.
- Treat every run as stateless.
- Recompute the same facts repeatedly.
- Generate noisy snapshots instead of meaningful deltas.
- Miss causal sequence because it does not preserve evolving context.
- Make the assistant reactive rather than watchful.

That is not the desired product loop.

## Desired Loop

The heartbeat should:

1. Collect key signals.
2. Normalize them into a stable resource graph.
3. Detect deltas, regressions, recoveries, and new risks.
4. Group related symptoms into candidate incidents.
5. Keep evidence trails fresh.
6. Make the current cluster assessment queryable by chat, API, or UI.

## What It Watches

Initial signals:

- K8sGPT Result CRDs
- Pod phases and container statuses
- Events
- Deployment conditions
- Service and Endpoint health
- Ingress backend shape
- PVC status
- Node readiness, taints, and capacity
- RBAC read failures

Later signals:

- Prometheus alerts
- Loki log excerpts
- Recent deployment metadata
- ArgoCD application health
- Cloud provider context

## Heartbeat Output

Each heartbeat should update a compact operational state:

- Cluster health summary
- Active candidate incidents
- Recently changed resources
- New or resolved K8sGPT findings
- Evidence grouped by workload, namespace, node, and service
- Confidence and uncertainty notes
- Suggested safe next checks

## Product Contract

The heartbeat does not mutate the cluster.

It prepares evidence. It does not remediate.

It should make the guardian faster and more consistent, but every user-facing assessment must still show the evidence it relies on.

## Relationship to the Emulator

The emulator should validate heartbeat behavior with deterministic timelines, not just static snapshots.

Useful heartbeat scenarios:

- A pod enters CrashLoopBackOff, then recovers.
- A deployment rollout stalls after a new ReplicaSet appears.
- A node becomes NotReady and pods become unschedulable.
- A service loses ready endpoints while pods still exist.
- A PVC remains Pending and blocks a workload.

The emulator should help verify that the heartbeat notices deltas, groups symptoms, and preserves causal order.

## Success Criteria

- The guardian can answer "what changed?" without a fresh full-cluster scan.
- Repeated polls produce state transitions, not duplicate noise.
- Related symptoms are grouped into a coherent candidate incident.
- Recovered issues are marked resolved rather than forgotten.
- Assessments cite heartbeat evidence and timestamps.

## Non-Goals

- Replacing Kubernetes watches with a fragile custom state store.
- Building autonomous remediation into the heartbeat.
- Treating heartbeat output as truth without source evidence.
- Polling every possible resource before proving value on high-signal resources.
