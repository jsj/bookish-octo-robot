import json
from pathlib import Path

import pytest

from enrichment_engine import EnrichmentEngine
from k8s_tools import K8sToolExecutor
from k8sgpt_reader import K8sGPTReader
from query_router import EnrichmentPlan, QueryCategory
from tests.emulate_bridge import (
    build_k8s_clients_from_emulate_seed,
    load_emulate_scenario,
)


FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "emulate_k8s_crashloop.json"
)


@pytest.fixture
def emulate_k8s_clients():
    seed = load_emulate_scenario(FIXTURE_PATH)
    return build_k8s_clients_from_emulate_seed(seed)


def test_emulate_bridge_drives_k8s_tool_executor(emulate_k8s_clients):
    executor = K8sToolExecutor(emulate_k8s_clients)

    namespaces = json.loads(executor.execute("list_namespaces", {}))
    pods = json.loads(executor.execute("list_pods", {"namespace": "payments"}))
    pod = json.loads(
        executor.execute(
            "get_pod",
            {"namespace": "payments", "pod_name": "checkout-api-7c9d4f-8x2ps"},
        )
    )
    logs = json.loads(
        executor.execute(
            "get_pod_logs",
            {"namespace": "payments", "pod_name": "checkout-api-7c9d4f-8x2ps"},
        )
    )

    assert {namespace["name"] for namespace in namespaces} >= {"payments", "platform"}
    assert len(pods) == 3
    assert pods[0]["containers"][0]["reason"] == "CrashLoopBackOff"
    assert pod["events"][0]["reason"] == "BackOff"
    assert "STRIPE_API_KEY" in logs["logs"]


@pytest.mark.asyncio
async def test_emulate_bridge_drives_k8sgpt_reader(emulate_k8s_clients):
    reader = K8sGPTReader(emulate_k8s_clients["custom_objects"])

    results = await reader.read_results(namespace="payments")

    assert len(results) == 2
    assert results[0].severity == "high"
    assert results[0].details["resource_name"] == "checkout-api-7c9d4f-8x2ps"
    assert "STRIPE_API_KEY" in results[0].solution


@pytest.mark.asyncio
async def test_emulate_bridge_drives_enrichment_engine(emulate_k8s_clients):
    engine = EnrichmentEngine(emulate_k8s_clients, aws_creds=None)
    plan = EnrichmentPlan(
        categories=[QueryCategory.POD_ISSUE],
        resource_names=["checkout-api-7c9d4f-8x2ps"],
        namespaces=["payments"],
        include_k8sgpt_results=True,
        include_aws_context=False,
    )

    context = await engine.execute(plan)

    assert context.errors == []
    assert context.pod_data is not None
    assert context.k8sgpt_results
    assert context.pod_data["pods"][0]["containers"][0]["reason"] == "CrashLoopBackOff"
    assert "STRIPE_API_KEY" in context.pod_data["pods"][0]["logs"]
