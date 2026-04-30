import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from kubernetes import client

from enrichment_engine import EnrichmentEngine
from k8s_tools import K8sToolExecutor
from k8sgpt_reader import K8sGPTReader
from query_router import EnrichmentPlan, QueryCategory
from sre_assessment import build_cluster_assessment


REPO_ROOT = Path(__file__).resolve().parents[2]
EMULATE_ROOT = REPO_ROOT.parent / "emulate"
EMULATE_CLI = EMULATE_ROOT / "packages" / "emulate" / "dist" / "index.js"
PLUGIN_PATH = REPO_ROOT / "local" / "emulate" / "kubernetes-plugin.mjs"
SEED_PATH = REPO_ROOT / "local" / "emulate" / "kubernetes-crashloop.json"


@pytest.fixture(scope="module")
def kubernetes_emulator_url():
    if not EMULATE_CLI.exists():
        pytest.skip("emulate CLI dist is not built")

    port = _free_port()
    process = subprocess.Popen(
        [
            "node",
            str(EMULATE_CLI),
            "start",
            "--service",
            "kubernetes",
            "--plugin",
            str(PLUGIN_PATH),
            "--seed",
            str(SEED_PATH),
            "--port",
            str(port),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
    )
    url = f"http://localhost:{port}"

    try:
        _wait_for_emulator(url, process)
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture
def emulate_k8s_clients(kubernetes_emulator_url):
    configuration = client.Configuration()
    configuration.host = kubernetes_emulator_url
    configuration.verify_ssl = False
    configuration.api_key = {"authorization": "test_token_admin"}
    configuration.api_key_prefix = {"authorization": "Bearer"}
    api_client = client.ApiClient(configuration)
    return {
        "core_v1": client.CoreV1Api(api_client),
        "apps_v1": client.AppsV1Api(api_client),
        "custom_objects": client.CustomObjectsApi(api_client),
        "networking_v1": client.NetworkingV1Api(api_client),
        "rbac_v1": client.RbacAuthorizationV1Api(api_client),
    }


def test_emulate_plugin_serves_kubernetes_http(kubernetes_emulator_url):
    with urlopen(f"{kubernetes_emulator_url}/api/v1/namespaces", timeout=5) as response:
        body = json.loads(response.read().decode())

    assert response.status == 200
    assert [item["metadata"]["name"] for item in body["items"]] == [
        "payments",
        "platform",
        "k8sgpt-operator-system",
    ]


def test_emulate_plugin_serves_expanded_resource_http(kubernetes_emulator_url):
    paths = {
        "services": "/api/v1/namespaces/payments/services",
        "ingresses": "/apis/networking.k8s.io/v1/namespaces/payments/ingresses",
        "pvcs": "/api/v1/namespaces/payments/persistentvolumeclaims",
        "roles": "/apis/rbac.authorization.k8s.io/v1/namespaces/payments/roles",
    }

    responses = {}
    for key, path in paths.items():
        with urlopen(f"{kubernetes_emulator_url}{path}", timeout=5) as response:
            responses[key] = json.loads(response.read().decode())

    assert responses["services"]["items"][0]["metadata"]["name"] == "checkout-api"
    assert responses["ingresses"]["items"][0]["spec"]["rules"][0]["host"] == "checkout.example.test"
    assert responses["pvcs"]["items"][0]["status"]["phase"] == "Pending"
    assert responses["roles"]["items"][0]["metadata"]["name"] == "checkout-reader"


def test_emulate_plugin_informs_k8s_tool_executor(emulate_k8s_clients):
    executor = K8sToolExecutor(emulate_k8s_clients)

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

    assert len(pods) == 3
    assert pods[0]["containers"][0]["reason"] == "CrashLoopBackOff"
    assert pod["events"][0]["reason"] == "BackOff"
    assert "STRIPE_API_KEY" in logs["logs"]


@pytest.mark.asyncio
async def test_emulate_plugin_informs_k8sgpt_reader(emulate_k8s_clients):
    reader = K8sGPTReader(emulate_k8s_clients["custom_objects"])

    results = await reader.read_results(namespace="payments")

    assert len(results) == 2
    assert results[0].severity == "high"
    assert results[0].details["resource_name"] == "checkout-api-7c9d4f-8x2ps"
    assert "STRIPE_API_KEY" in results[0].solution


@pytest.mark.asyncio
async def test_emulate_plugin_informs_enrichment_engine(emulate_k8s_clients):
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


@pytest.mark.asyncio
async def test_emulate_plugin_informs_networking_storage_nodes_and_security(emulate_k8s_clients):
    engine = EnrichmentEngine(emulate_k8s_clients, aws_creds=None)
    plan = EnrichmentPlan(
        categories=[
            QueryCategory.SERVICE_NETWORKING,
            QueryCategory.STORAGE,
            QueryCategory.NODE_HEALTH,
            QueryCategory.SECURITY,
        ],
        resource_names=[],
        namespaces=["payments"],
        include_k8sgpt_results=False,
        include_aws_context=False,
    )

    context = await engine.execute(plan)

    assert context.errors == []
    assert context.service_data["services"][0]["name"] == "checkout-api"
    assert context.service_data["services"][0]["endpoints"]["ready"] == ["10.244.1.23:8080"]
    assert context.service_data["ingresses"][0]["rules"][0]["host"] == "checkout.example.test"
    assert context.storage_data["pvcs"][0]["name"] == "checkout-cache"
    assert context.storage_data["pvcs"][0]["status"] == "Pending"
    assert context.node_data["nodes"][1]["status"] == "NotReady"
    assert context.security_data["roles"][0]["rules_count"] == 1
    assert context.security_data["service_accounts"][0]["name"] == "checkout-api"


@pytest.mark.asyncio
async def test_emulate_plugin_drives_evidence_backed_sre_assessment(emulate_k8s_clients):
    engine = EnrichmentEngine(emulate_k8s_clients, aws_creds=None)
    plan = EnrichmentPlan(
        categories=[
            QueryCategory.POD_ISSUE,
            QueryCategory.DEPLOYMENT_STATUS,
            QueryCategory.SERVICE_NETWORKING,
            QueryCategory.STORAGE,
            QueryCategory.NODE_HEALTH,
        ],
        resource_names=[],
        namespaces=["payments"],
        include_k8sgpt_results=True,
        include_aws_context=False,
    )

    context = await engine.execute(plan)
    assessment = build_cluster_assessment(context)
    payload = assessment.to_dict()

    assert payload["severity"] == "high"
    assert payload["evidence_count"] >= 8
    assert any(
        "STRIPE_API_KEY" in incident["likely_cause"]
        for incident in payload["incidents"]
    )
    assert any(
        incident["title"] == "Service/checkout-api has endpoint readiness risk"
        for incident in payload["incidents"]
    )
    assert all(
        step.startswith("kubectl describe")
        or step.startswith("kubectl logs")
        or step.startswith("kubectl get")
        or step.startswith("kubectl rollout status")
        or not step.startswith("kubectl")
        for incident in payload["incidents"]
        for step in incident["safe_next_steps"]
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_emulator(url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + 20
    last_error = ""
    while time.time() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            pytest.fail(f"emulate exited early with {process.returncode}: {output}")
        try:
            with urlopen(f"{url}/api/v1/namespaces", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.25)
    print(last_error, file=sys.stderr)
    pytest.fail("timed out waiting for kubernetes emulate plugin")
