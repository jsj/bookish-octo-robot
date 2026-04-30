# Product Strategy

## Product Thesis

This product is a **conscientious cluster guardian**.

Its core loop is not "chat with Kubernetes" or "run kubectl through an LLM." The loop is:

1. Continuously gather trustworthy cluster signals.
2. Detect and explain operational drift, failure, or risk.
3. Synthesize what matters across noisy tools and resources.
4. Recommend the safest next diagnostic or remediation step.
5. Preserve operator confidence by staying read-only unless explicitly designed otherwise.

The product should feel like a calm senior SRE watching the cluster with you, not like a command shell.

## Job to Be Done

When I am responsible for keeping Kubernetes-based systems healthy, and something breaks or may break, help me quickly understand what is happening, why it is happening, and what safe next action to take, without needing deep cluster-specific context or risky live experimentation.

## Product Role

The product is hired to provide **safe operational understanding under pressure**.

It should help users:

- See the state of the cluster without drowning in raw output.
- Connect symptoms across pods, deployments, services, ingresses, storage, nodes, RBAC, events, and K8sGPT findings.
- Separate root cause from incidental noise.
- Explain incidents in language a teammate can act on.
- Reduce the fear of making a production situation worse.

## The Core Promise

**Trustworthy cluster judgment before action.**

This means the product must optimize for:

- Read-only safety.
- High-signal synthesis.
- Explainable evidence.
- Repeatable validation.
- Low operator anxiety.

## What Customers Hire Today

Customers currently hire a mix of tools and people:

- Raw `kubectl`
- Grafana, Loki, and Prometheus dashboards
- K8sGPT
- Runbooks
- Senior engineers
- Slack war rooms
- Kind or k3d toy clusters
- Static JSON or YAML mocks
- Nothing: they test against prod-like clusters and hope

## Why Those Fall Short

- `kubectl` gives facts, not synthesis.
- Dashboards show signals, not causality.
- K8sGPT gives findings, but not full workflow context.
- Runbooks go stale.
- Senior engineers do not scale.
- Slack war rooms are expensive coordination mechanisms, not durable diagnosis systems.
- Toy clusters miss real-world complexity.
- Static mocks do not reveal Kubernetes API shape and wire-format fidelity gaps.
- Real clusters are expensive, risky, inconsistent, and hard to reset.

## Forces of Progress

### Push of the Situation

- Clusters are too complex for one human to hold in working memory.
- On-call diagnosis is stressful and time-sensitive.
- Existing tools create fragmented evidence.
- LLM answers are hard to trust without realistic validation.

### Pull of the Product

- A single place to ask: "What is wrong, why, and what should I safely check next?"
- Evidence-backed synthesis across cluster resources.
- Repeatable scenarios for validating the assistant before production use.
- A calmer operational loop for engineers and teams.

### Habits of the Present

- Engineers know `kubectl`.
- Teams already have dashboards and runbooks.
- Senior engineers are used as the escalation path.
- Prod-like clusters are treated as the only trustworthy test environment.

### Anxiety About the New

- The assistant may hallucinate.
- It may miss important context.
- It may recommend unsafe actions.
- Mock data may be too fake to create trust.

The product wins only if it lowers anxiety faster than it adds abstraction.

## Emulator Positioning

The emulator is **developer tooling**, not the core product.

Its job is to support the product promise by making realistic, repeatable cluster states available during development and validation.

The emulator should:

- Reveal gaps in API fidelity.
- Exercise the same tool paths the product uses against Kubernetes.
- Make failure scenarios deterministic.
- Help prove the assistant can synthesize realistic cluster conditions.

The emulator should not become the user-facing value proposition. Users hire the cluster guardian, not the emulator.

## Good Assessment Criteria

A good answer from the product should:

- Name the likely issue clearly.
- Cite the concrete evidence used.
- Explain why the evidence matters.
- Distinguish primary cause from secondary symptoms.
- Recommend a safe next action.
- Avoid destructive commands unless explicitly authorized by product policy.
- Admit uncertainty when evidence is incomplete.

A bad answer:

- Dumps raw `kubectl`-style output.
- Over-indexes on one signal.
- Treats K8sGPT output as unquestionable truth.
- Gives remediation without evidence.
- Ignores blast radius.
- Fails to say what it does not know.

## Directional Product Metrics

- Time from question to credible diagnosis.
- Percent of answers with cited cluster evidence.
- Percent of recommendations that are read-only or explicitly safe.
- Reduction in escalation to senior engineers for known classes of incidents.
- Number of realistic failure scenarios covered by emulator-backed validation.
- Number of API fidelity gaps discovered before production.

## Product Guardrails

- The default posture is read-only.
- Synthesis is more valuable than command execution.
- Evidence should be visible and inspectable.
- The product should reduce operator anxiety, not create a black box.
- The emulator should remain a validation system for realistic scenarios, not the main product surface.
