import json

from sre_cli import main


def test_sre_cli_assess_context_file_outputs_text(tmp_path, capsys):
    context_file = tmp_path / "context.json"
    context_file.write_text(
        json.dumps(
            {
                "pod_data": {
                    "pods": [
                        {
                            "name": "checkout-api-7c9d4f-8x2ps",
                            "namespace": "payments",
                            "containers": [
                                {
                                    "state": "waiting",
                                    "reason": "CrashLoopBackOff",
                                    "message": "back-off restarting failed container",
                                    "last_termination": {
                                        "message": "missing required env var STRIPE_API_KEY"
                                    },
                                }
                            ],
                            "logs": "fatal: missing required env var STRIPE_API_KEY",
                        }
                    ]
                }
            }
        )
    )

    exit_code = main(["assess", "--context-file", str(context_file)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "HIGH:" in output
    assert "Pod/checkout-api-7c9d4f-8x2ps is unhealthy" in output
    assert "STRIPE_API_KEY" in output


def test_sre_cli_assess_context_file_outputs_json(tmp_path, capsys):
    context_file = tmp_path / "context.json"
    context_file.write_text(json.dumps({"service_data": {"services": []}}))

    exit_code = main(["assess", "--context-file", str(context_file), "--output", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["severity"] == "low"
    assert payload["incidents"] == []
