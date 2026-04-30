from enrichment_engine import EnrichedContext
from sre_assessment import build_cluster_assessment


def test_build_cluster_assessment_from_unhealthy_context():
    context = EnrichedContext(
        pod_data={
            "pods": [
                {
                    "name": "checkout-api-7c9d4f-8x2ps",
                    "namespace": "payments",
                    "phase": "Running",
                    "containers": [
                        {
                            "name": "checkout-api",
                            "state": "waiting",
                            "reason": "CrashLoopBackOff",
                            "message": "back-off restarting failed container",
                            "restart_count": 17,
                            "last_termination": {
                                "reason": "Error",
                                "exit_code": 1,
                                "message": "missing required env var STRIPE_API_KEY",
                            },
                        }
                    ],
                    "events": [
                        {
                            "type": "Warning",
                            "reason": "BackOff",
                            "message": "Back-off restarting failed container checkout-api",
                        }
                    ],
                    "logs": "fatal: missing required env var STRIPE_API_KEY",
                }
            ]
        },
        service_data={
            "services": [
                {
                    "name": "checkout-api",
                    "namespace": "payments",
                    "endpoints": {"ready": [], "not_ready": ["10.244.2.19:8080"]},
                }
            ]
        },
        storage_data={
            "pvcs": [
                {
                    "name": "checkout-cache",
                    "namespace": "payments",
                    "status": "Pending",
                    "storage_class": "gp3",
                    "capacity": None,
                }
            ]
        },
        node_data={
            "nodes": [
                {"name": "node-a", "status": "Ready", "pod_count": 2, "taints": []},
                {
                    "name": "node-b",
                    "status": "NotReady",
                    "pod_count": 1,
                    "taints": [{"key": "node.kubernetes.io/not-ready"}],
                },
            ]
        },
    )

    assessment = build_cluster_assessment(context)
    payload = assessment.to_dict()

    assert payload["severity"] == "high"
    assert payload["evidence_count"] >= 4
    assert any(
        "STRIPE_API_KEY" in incident["likely_cause"]
        for incident in payload["incidents"]
    )
    assert any(
        step.startswith("kubectl describe pod checkout-api")
        for incident in payload["incidents"]
        for step in incident["safe_next_steps"]
    )
    assert any(
        incident["title"] == "Service/checkout-api has endpoint readiness risk"
        for incident in payload["incidents"]
    )


def test_build_cluster_assessment_with_no_findings():
    assessment = build_cluster_assessment(EnrichedContext())

    assert assessment.severity == "low"
    assert assessment.incidents == []
    assert "No active incident" in assessment.summary
    assert "No K8sGPT findings" in assessment.unknowns[0]
