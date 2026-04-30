# Emulator Role

## Purpose

The emulator exists to validate the conscientious cluster guardian against realistic, repeatable Kubernetes states.

It is a dev and test tool. It is not the core customer-facing product.

## Job

When we are building or evaluating the cluster guardian, help us create realistic, repeatable cluster failure scenarios so we can prove the assistant gives useful, evidence-backed answers before connecting it to real infrastructure.

## What It Should Emulate First

The emulator should prioritize resources that directly improve diagnosis quality:

- Pods, container statuses, previous termination details, and logs
- Events
- Deployments and rollout conditions
- Services and Endpoints
- Ingresses
- PVCs and storage state
- Nodes, conditions, taints, capacity, and allocatable resources
- RBAC Roles and ServiceAccounts
- K8sGPT Result CRDs

## What It Should Reveal

The emulator is valuable when it reveals gaps such as:

- Missing Kubernetes wire-format fields
- Incomplete API endpoint coverage
- Incorrect assumptions in client code
- Scenarios where static mocks pass but real Kubernetes clients fail
- Cases where the assistant has facts but fails to synthesize causality

## What It Should Not Become

- A replacement for real cluster testing
- A product feature marketed to end users
- A fake demo layer that hides product weaknesses
- A separate source of truth from the Kubernetes API shape

## Current Implementation

The repo contains an external `emulate` plugin at:

- `local/emulate/kubernetes-plugin.mjs`
- `local/emulate/kubernetes-crashloop.json`
- `local/emulate/start-kubernetes-emulator.mjs`

The launcher is:

```bash
npm run emulate:kubernetes
```

By default it starts the Kubernetes emulator on:

```text
http://localhost:4100
```

## Success Bar

The emulator is doing its job when product tests exercise the same backend paths used in production:

- `K8sToolExecutor`
- `K8sGPTReader`
- `EnrichmentEngine`

The important validation question is:

> Did the emulator cause the cluster guardian to produce a better, safer, more evidence-backed assessment?
