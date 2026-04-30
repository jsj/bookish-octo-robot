"""Helpers for turning emulate-style scenario seeds into Kubernetes client doubles."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from kubernetes.client.exceptions import ApiException


def load_emulate_scenario(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as scenario_file:
        return json.load(scenario_file)


def build_k8s_clients_from_emulate_seed(seed: dict[str, Any]) -> dict[str, Any]:
    cluster = seed["services"]["kubernetes"]["clusters"][0]
    return {
        "core_v1": _CoreV1Double(cluster),
        "apps_v1": _AppsV1Double(cluster),
        "custom_objects": _CustomObjectsDouble(cluster),
        "networking_v1": SimpleNamespace(),
        "rbac_v1": SimpleNamespace(),
    }


class _CoreV1Double:
    def __init__(self, cluster: dict[str, Any]) -> None:
        self.cluster = cluster

    def list_namespace(self) -> SimpleNamespace:
        items = [
            _namespace(namespace)
            for namespace in self.cluster.get("namespaces", [])
        ]
        return SimpleNamespace(items=items)

    def list_node(self) -> SimpleNamespace:
        items = [_node(node) for node in self.cluster.get("nodes", [])]
        return SimpleNamespace(items=items)

    def list_namespaced_pod(
        self, namespace: str, limit: int | None = None
    ) -> SimpleNamespace:
        pods = [
            _pod(pod)
            for pod in self.cluster.get("pods", [])
            if pod["namespace"] == namespace
        ]
        return SimpleNamespace(items=_limit(pods, limit))

    def read_namespaced_pod(self, name: str, namespace: str) -> SimpleNamespace:
        for pod in self.cluster.get("pods", []):
            if pod["name"] == name and pod["namespace"] == namespace:
                return _pod(pod)
        raise ApiException(status=404, reason="Pod not found")

    def list_namespaced_event(
        self,
        namespace: str,
        field_selector: str | None = None,
        limit: int | None = None,
    ) -> SimpleNamespace:
        resource_name = _field_selector_name(field_selector)
        events = []
        for event in self.cluster.get("events", []):
            if event["namespace"] != namespace:
                continue
            if resource_name and event["involved_object"]["name"] != resource_name:
                continue
            events.append(_event(event))
        return SimpleNamespace(items=_limit(events, limit))

    def read_namespaced_pod_log(
        self,
        name: str,
        namespace: str,
        tail_lines: int | None = None,
        **_: Any,
    ) -> str:
        pod_logs = self.cluster.get("logs", {}).get(namespace, {}).get(name)
        if pod_logs is None:
            raise ApiException(status=404, reason="Pod logs not found")
        if tail_lines is None:
            return pod_logs
        return "\n".join(pod_logs.splitlines()[-tail_lines:])


class _AppsV1Double:
    def __init__(self, cluster: dict[str, Any]) -> None:
        self.cluster = cluster

    def list_namespaced_deployment(
        self, namespace: str, limit: int | None = None
    ) -> SimpleNamespace:
        deployments = [
            _deployment(deployment)
            for deployment in self.cluster.get("deployments", [])
            if deployment["namespace"] == namespace
        ]
        return SimpleNamespace(items=_limit(deployments, limit))

    def read_namespaced_deployment(
        self, name: str, namespace: str
    ) -> SimpleNamespace:
        for deployment in self.cluster.get("deployments", []):
            if deployment["name"] == name and deployment["namespace"] == namespace:
                return _deployment(deployment)
        raise ApiException(status=404, reason="Deployment not found")


class _CustomObjectsDouble:
    def __init__(self, cluster: dict[str, Any]) -> None:
        self.cluster = cluster

    def list_cluster_custom_object(self, **_: Any) -> dict[str, Any]:
        return {"items": self.cluster.get("k8sgpt_results", [])}

    def list_namespaced_custom_object(self, namespace: str, **_: Any) -> dict[str, Any]:
        return {
            "items": [
                result
                for result in self.cluster.get("k8sgpt_results", [])
                if result.get("metadata", {}).get("namespace") == namespace
            ]
        }


def _namespace(namespace: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        metadata=SimpleNamespace(name=namespace["name"]),
        status=SimpleNamespace(phase=namespace.get("status", "Active")),
    )


def _node(node: dict[str, Any]) -> SimpleNamespace:
    conditions = [
        SimpleNamespace(type=condition["type"], status=condition["status"])
        for condition in node.get("conditions", [])
    ]
    return SimpleNamespace(
        metadata=SimpleNamespace(
            name=node["name"],
            labels=node.get("labels", {}),
        ),
        status=SimpleNamespace(conditions=conditions),
    )


def _pod(pod: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        metadata=SimpleNamespace(name=pod["name"], namespace=pod["namespace"]),
        spec=SimpleNamespace(node_name=pod.get("node")),
        status=SimpleNamespace(
            phase=pod.get("phase", "Unknown"),
            conditions=[
                _condition(condition) for condition in pod.get("conditions", [])
            ],
            container_statuses=[
                _container_status(container)
                for container in pod.get("containers", [])
            ],
        ),
    )


def _deployment(deployment: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        metadata=SimpleNamespace(
            name=deployment["name"],
            namespace=deployment["namespace"],
        ),
        spec=SimpleNamespace(replicas=deployment.get("replicas", 1)),
        status=SimpleNamespace(
            ready_replicas=deployment.get("ready_replicas", 0),
            available_replicas=deployment.get("available_replicas", 0),
            unavailable_replicas=deployment.get("unavailable_replicas", 0),
            conditions=[
                _condition(condition)
                for condition in deployment.get("conditions", [])
            ],
        ),
    )


def _event(event: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        type=event.get("type", "Normal"),
        reason=event.get("reason"),
        message=event.get("message"),
        count=event.get("count", 1),
        last_timestamp=None,
        involved_object=SimpleNamespace(
            kind=event["involved_object"]["kind"],
            name=event["involved_object"]["name"],
        ),
    )


def _condition(condition: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        type=condition.get("type"),
        status=condition.get("status"),
        reason=condition.get("reason"),
        message=condition.get("message"),
    )


def _container_status(container: dict[str, Any]) -> SimpleNamespace:
    state_name = container.get("state", "running")
    reason = container.get("reason")
    message = container.get("message")
    return SimpleNamespace(
        name=container["name"],
        ready=container.get("ready", False),
        restart_count=container.get("restart_count", 0),
        state=SimpleNamespace(
            running=SimpleNamespace(started_at=None) if state_name == "running" else None,
            waiting=(
                SimpleNamespace(reason=reason, message=message)
                if state_name == "waiting"
                else None
            ),
            terminated=(
                SimpleNamespace(
                    reason=reason,
                    message=message,
                    exit_code=container.get("exit_code", 1),
                )
                if state_name == "terminated"
                else None
            ),
        ),
        last_state=SimpleNamespace(
            terminated=(
                SimpleNamespace(
                    reason=container["last_termination"].get("reason"),
                    message=container["last_termination"].get("message"),
                    exit_code=container["last_termination"].get("exit_code", 1),
                )
                if container.get("last_termination")
                else None
            )
        ),
    )


def _field_selector_name(field_selector: str | None) -> str | None:
    if not field_selector:
        return None
    prefix = "involvedObject.name="
    if field_selector.startswith(prefix):
        return field_selector.removeprefix(prefix)
    return None


def _limit(items: list[Any], limit: int | None) -> list[Any]:
    return items[:limit] if limit else items
