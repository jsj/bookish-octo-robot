import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_kubernetes_emulator_launcher_command():
    result = subprocess.run(
        [
            "node",
            str(REPO_ROOT / "local" / "emulate" / "start-kubernetes-emulator.mjs"),
            "--print-command",
            "--port",
            "4199",
        ],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)

    assert payload["executable"] == "node"
    assert payload["url"] == "http://localhost:4199"
    assert "--service" in payload["args"]
    assert "kubernetes" in payload["args"]
    assert str(REPO_ROOT / "local" / "emulate" / "kubernetes-plugin.mjs") in payload["args"]
    assert str(REPO_ROOT / "local" / "emulate" / "kubernetes-crashloop.json") in payload["args"]


def test_package_script_exposes_kubernetes_emulator():
    package_json = json.loads((REPO_ROOT / "package.json").read_text())

    assert package_json["scripts"]["emulate:kubernetes"] == (
        "node local/emulate/start-kubernetes-emulator.mjs"
    )
