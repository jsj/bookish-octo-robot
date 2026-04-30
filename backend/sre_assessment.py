"""Evidence-backed SRE assessment builder."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from enrichment_engine import EnrichedContext


SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


@dataclass
class Evidence:
    source: str
    resource: str
    namespace: str | None
    signal: str
    detail: str


@dataclass
class IncidentAssessment:
    title: str
    severity: str
    likely_cause: str
    affected_resources: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    safe_next_steps: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)


@dataclass
class ClusterAssessment:
    summary: str
    severity: str
    incidents: list[IncidentAssessment] = field(default_factory=list)
    evidence_count: int = 0
    unknowns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_cluster_assessment(context: EnrichedContext) -> ClusterAssessment:
    incidents = _build_incidents(context)
    severity = _highest_severity([incident.severity for incident in incidents])
    evidence_count = sum(len(incident.evidence) for incident in incidents)
    unknowns = _global_unknowns(context)

    if incidents:
        summary = f"{len(incidents)} candidate incident(s), highest severity: {severity}"
    elif context.errors:
        summary = "Assessment incomplete due to enrichment errors"
        severity = "medium"
    else:
        summary = "No active incident candidates found in enriched context"
        severity = "low"

    return ClusterAssessment(
        summary=summary,
        severity=severity,
        incidents=incidents,
        evidence_count=evidence_count,
        unknowns=unknowns,
    )


def _build_incidents(context: EnrichedContext) -> list[IncidentAssessment]:
    incidents: list[IncidentAssessment] = []
    incidents.extend(_incidents_from_k8sgpt(context))
    incidents.extend(_incidents_from_pods(context))
    incidents.extend(_incidents_from_deployments(context))
    incidents.extend(_incidents_from_services(context))
    incidents.extend(_incidents_from_storage(context))
    incidents.extend(_incidents_from_nodes(context))
    return _merge_related_incidents(incidents)


def _incidents_from_k8sgpt(context: EnrichedContext) -> list[IncidentAssessment]:
    incidents = []
    for result in context.k8sgpt_results:
        result_dict = _result_to_dict(result)
        details = result_dict.get("details") or {}
        resource = f"{result_dict.get('kind', 'Unknown')}/{details.get('resource_name') or result_dict.get('name', 'unknown')}"
        namespace = result_dict.get("namespace")
        severity = result_dict.get("severity", "medium")
        raw_errors = details.get("error") or []
        problem = result_dict.get("problem") or "K8sGPT reported an issue"
        likely_cause = _pick_likely_cause(
            [
                Evidence(
                    source="k8sgpt",
                    resource=resource,
                    namespace=namespace,
                    signal="finding",
                    detail=problem,
                ),
                *[
                    Evidence(
                        source="k8sgpt",
                        resource=resource,
                        namespace=namespace,
                        signal="raw_error",
                        detail=str(error),
                    )
                    for error in raw_errors[:3]
                ],
            ],
            [str(error) for error in raw_errors],
        )
        solution = result_dict.get("solution") or "Review the K8sGPT finding and related resource state."

        evidence = [
            Evidence(
                source="k8sgpt",
                resource=resource,
                namespace=namespace,
                signal="finding",
                detail=problem,
            )
        ]
        for error in raw_errors[:3]:
            evidence.append(
                Evidence(
                    source="k8sgpt",
                    resource=resource,
                    namespace=namespace,
                    signal="raw_error",
                    detail=str(error),
                )
            )

        incidents.append(
            IncidentAssessment(
                title=f"{resource} reported by K8sGPT",
                severity=severity,
                likely_cause=likely_cause,
                affected_resources=[resource],
                evidence=evidence,
                safe_next_steps=[_read_only_step_for_resource(resource, namespace), solution],
            )
        )
    return incidents


def _incidents_from_pods(context: EnrichedContext) -> list[IncidentAssessment]:
    incidents = []
    for pod in (context.pod_data or {}).get("pods", []):
        namespace = pod.get("namespace")
        resource = f"Pod/{pod.get('name')}"
        evidence: list[Evidence] = []
        reasons = []

        for container in pod.get("containers", []):
            reason = container.get("reason")
            if container.get("state") in {"waiting", "terminated"} or reason:
                reasons.append(reason or container.get("state", "container_not_ready"))
                evidence.append(
                    Evidence(
                        source="pod_status",
                        resource=resource,
                        namespace=namespace,
                        signal=reason or container.get("state", "container_status"),
                        detail=container.get("message") or f"restart_count={container.get('restart_count', 0)}",
                    )
                )
            if container.get("last_termination"):
                evidence.append(
                    Evidence(
                        source="pod_status",
                        resource=resource,
                        namespace=namespace,
                        signal="last_termination",
                        detail=str(container["last_termination"]),
                    )
                )

        for event in pod.get("events", [])[:5]:
            if event.get("type") == "Warning":
                evidence.append(
                    Evidence(
                        source="event",
                        resource=resource,
                        namespace=namespace,
                        signal=event.get("reason") or "Warning",
                        detail=event.get("message") or "",
                    )
                )

        if pod.get("logs"):
            evidence.append(
                Evidence(
                    source="logs",
                    resource=resource,
                    namespace=namespace,
                    signal="recent_logs",
                    detail=pod["logs"][:500],
                )
            )

        if evidence:
            likely_cause = _pick_likely_cause(evidence, reasons)
            incidents.append(
                IncidentAssessment(
                    title=f"{resource} is unhealthy",
                    severity=_severity_from_signals(reasons),
                    likely_cause=likely_cause,
                    affected_resources=[resource],
                    evidence=evidence,
                    safe_next_steps=[
                        f"kubectl describe pod {pod.get('name')} -n {namespace}",
                        f"kubectl logs {pod.get('name')} -n {namespace} --tail=100",
                    ],
                )
            )
    return incidents


def _incidents_from_deployments(context: EnrichedContext) -> list[IncidentAssessment]:
    incidents = []
    for deployment in (context.deployment_data or {}).get("deployments", []):
        namespace = deployment.get("namespace")
        resource = f"Deployment/{deployment.get('name')}"
        replicas = deployment.get("replicas", {})
        unavailable = replicas.get("unavailable", 0) if isinstance(replicas, dict) else deployment.get("unavailable", 0)
        evidence = []

        for condition in deployment.get("conditions", []):
            if condition.get("status") == "False" or condition.get("reason"):
                evidence.append(
                    Evidence(
                        source="deployment_condition",
                        resource=resource,
                        namespace=namespace,
                        signal=condition.get("reason") or condition.get("type", "condition"),
                        detail=condition.get("message") or "",
                    )
                )
        if unavailable:
            evidence.append(
                Evidence(
                    source="deployment_status",
                    resource=resource,
                    namespace=namespace,
                    signal="unavailable_replicas",
                    detail=f"{unavailable} unavailable replica(s)",
                )
            )

        if evidence:
            incidents.append(
                IncidentAssessment(
                    title=f"{resource} rollout is degraded",
                    severity="high" if unavailable else "medium",
                    likely_cause=evidence[0].detail or evidence[0].signal,
                    affected_resources=[resource],
                    evidence=evidence,
                    safe_next_steps=[
                        f"kubectl describe deployment {deployment.get('name')} -n {namespace}",
                        f"kubectl rollout status deployment/{deployment.get('name')} -n {namespace}",
                    ],
                )
            )
    return incidents


def _incidents_from_services(context: EnrichedContext) -> list[IncidentAssessment]:
    incidents = []
    for service in (context.service_data or {}).get("services", []):
        endpoints = service.get("endpoints") or {}
        ready = endpoints.get("ready") or []
        not_ready = endpoints.get("not_ready") or []
        if ready and not not_ready:
            continue
        namespace = service.get("namespace")
        resource = f"Service/{service.get('name')}"
        evidence = [
            Evidence(
                source="endpoints",
                resource=resource,
                namespace=namespace,
                signal="endpoint_readiness",
                detail=f"ready={len(ready)} not_ready={len(not_ready)}",
            )
        ]
        incidents.append(
            IncidentAssessment(
                title=f"{resource} has endpoint readiness risk",
                severity="high" if not ready else "medium",
                likely_cause="Service has no ready endpoints" if not ready else "Service has not-ready endpoints",
                affected_resources=[resource],
                evidence=evidence,
                safe_next_steps=[
                    f"kubectl get endpoints {service.get('name')} -n {namespace} -o wide",
                    f"kubectl describe service {service.get('name')} -n {namespace}",
                ],
            )
        )
    return incidents


def _incidents_from_storage(context: EnrichedContext) -> list[IncidentAssessment]:
    incidents = []
    for pvc in (context.storage_data or {}).get("pvcs", []):
        if pvc.get("status") == "Bound":
            continue
        namespace = pvc.get("namespace")
        resource = f"PVC/{pvc.get('name')}"
        incidents.append(
            IncidentAssessment(
                title=f"{resource} is not bound",
                severity="medium",
                likely_cause=f"PVC status is {pvc.get('status')}",
                affected_resources=[resource],
                evidence=[
                    Evidence(
                        source="pvc_status",
                        resource=resource,
                        namespace=namespace,
                        signal=pvc.get("status") or "Unknown",
                        detail=f"storage_class={pvc.get('storage_class')} capacity={pvc.get('capacity')}",
                    )
                ],
                safe_next_steps=[f"kubectl describe pvc {pvc.get('name')} -n {namespace}"],
            )
        )
    return incidents


def _incidents_from_nodes(context: EnrichedContext) -> list[IncidentAssessment]:
    incidents = []
    for node in (context.node_data or {}).get("nodes", []):
        if node.get("status") == "Ready":
            continue
        resource = f"Node/{node.get('name')}"
        evidence = [
            Evidence(
                source="node_status",
                resource=resource,
                namespace=None,
                signal=node.get("status") or "Unknown",
                detail=f"pod_count={node.get('pod_count')} taints={node.get('taints', [])}",
            )
        ]
        incidents.append(
            IncidentAssessment(
                title=f"{resource} is not ready",
                severity="high",
                likely_cause=f"Node status is {node.get('status')}",
                affected_resources=[resource],
                evidence=evidence,
                safe_next_steps=[
                    f"kubectl describe node {node.get('name')}",
                    "kubectl get pods -A --field-selector spec.nodeName="
                    f"{node.get('name')}",
                ],
            )
        )
    return incidents


def _merge_related_incidents(incidents: list[IncidentAssessment]) -> list[IncidentAssessment]:
    merged: dict[tuple[str, str | None], IncidentAssessment] = {}
    for incident in incidents:
        key = _merge_key(incident)
        if key not in merged:
            merged[key] = incident
            continue
        existing = merged[key]
        existing.evidence.extend(incident.evidence)
        existing.safe_next_steps = _unique(existing.safe_next_steps + incident.safe_next_steps)
        existing.affected_resources = _unique(existing.affected_resources + incident.affected_resources)
        existing.severity = _highest_severity([existing.severity, incident.severity])
        if _is_more_specific_cause(incident.likely_cause, existing.likely_cause):
            existing.likely_cause = incident.likely_cause
    return sorted(
        merged.values(),
        key=lambda item: SEVERITY_RANK.get(item.severity, 0),
        reverse=True,
    )


def _merge_key(incident: IncidentAssessment) -> tuple[str, str | None]:
    first = incident.evidence[0] if incident.evidence else None
    if not first:
        return (incident.title, None)
    return (first.resource, first.namespace)


def _result_to_dict(result: Any) -> dict[str, Any]:
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if isinstance(result, dict):
        return result
    return {}


def _read_only_step_for_resource(resource: str, namespace: str | None) -> str:
    kind, _, name = resource.partition("/")
    kind = kind.lower()
    namespace_arg = f" -n {namespace}" if namespace and kind != "node" else ""
    return f"kubectl describe {kind} {name}{namespace_arg}"


def _pick_likely_cause(evidence: list[Evidence], reasons: list[str]) -> str:
    for item in evidence:
        lowered = item.detail.lower()
        if "missing required env var" in lowered:
            return item.detail.splitlines()[-1]
    for item in evidence:
        if item.signal in {"CrashLoopBackOff", "ImagePullBackOff", "OOMKilled", "FailedScheduling"}:
            return item.detail or item.signal
    return ", ".join(_unique([reason for reason in reasons if reason])) or evidence[0].detail


def _is_more_specific_cause(candidate: str, current: str) -> bool:
    candidate_lower = candidate.lower()
    current_lower = current.lower()
    specificity_markers = ["missing required env var", "exit code", "failedscheduling", "oomkilled", "imagepullbackoff"]
    if any(marker in candidate_lower for marker in specificity_markers) and not any(
        marker in current_lower for marker in specificity_markers
    ):
        return True
    return len(candidate) > len(current)


def _severity_from_signals(signals: list[str]) -> str:
    lowered = {signal.lower() for signal in signals if signal}
    if {"crashloopbackoff", "imagepullbackoff", "oomkilled", "failedscheduling"} & lowered:
        return "high"
    if lowered:
        return "medium"
    return "low"


def _highest_severity(severities: list[str]) -> str:
    if not severities:
        return "low"
    return max(severities, key=lambda item: SEVERITY_RANK.get(item, 0))


def _global_unknowns(context: EnrichedContext) -> list[str]:
    unknowns = list(context.errors)
    if not context.k8sgpt_results:
        unknowns.append("No K8sGPT findings were available for this assessment.")
    return unknowns


def _unique(items: list[str]) -> list[str]:
    seen = set()
    unique_items = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)
    return unique_items
