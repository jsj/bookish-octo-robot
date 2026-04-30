"""CLI surface for evidence-backed SRE assessments."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from kubernetes import client

from enrichment_engine import EnrichedContext, EnrichmentEngine
from query_router import EnrichmentPlan, QueryCategory
from sre_assessment import build_cluster_assessment


DEFAULT_CATEGORIES = [
    QueryCategory.POD_ISSUE,
    QueryCategory.DEPLOYMENT_STATUS,
    QueryCategory.SERVICE_NETWORKING,
    QueryCategory.STORAGE,
    QueryCategory.NODE_HEALTH,
    QueryCategory.SECURITY,
]


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "assess":
        assessment = asyncio.run(_run_assess(args))
        _print_assessment(assessment.to_dict(), args.output)
        return 0

    parser.print_help()
    return 1


async def _run_assess(args: argparse.Namespace):
    if args.context_file:
        context = _context_from_mapping(_read_json(args.context_file))
    else:
        clients = _build_k8s_clients(args.api_server, args.token)
        plan = EnrichmentPlan(
            categories=_parse_categories(args.categories),
            resource_names=[],
            namespaces=args.namespace or [],
            include_k8sgpt_results=not args.no_k8sgpt,
            include_aws_context=False,
        )
        context = await EnrichmentEngine(clients, aws_creds=None).execute(plan)

    return build_cluster_assessment(context)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sre-cli",
        description="Evidence-backed Kubernetes SRE assessment CLI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    assess = subparsers.add_parser("assess", help="Assess cluster or captured context")
    assess.add_argument("--context-file", type=Path, help="Path to captured EnrichedContext JSON")
    assess.add_argument("--api-server", help="Kubernetes API server URL, including emulator URLs")
    assess.add_argument("--token", default="test_token_admin", help="Bearer token for the API server")
    assess.add_argument("--namespace", action="append", help="Namespace to assess; repeatable")
    assess.add_argument(
        "--category",
        dest="categories",
        action="append",
        choices=[category.value for category in QueryCategory],
        help="Enrichment category to include; repeatable",
    )
    assess.add_argument("--no-k8sgpt", action="store_true", help="Skip K8sGPT result enrichment")
    assess.add_argument("--output", choices=["text", "json"], default="text")

    return parser


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _context_from_mapping(data: dict[str, Any]) -> EnrichedContext:
    return EnrichedContext(
        k8sgpt_results=data.get("k8sgpt_results", []),
        pod_data=data.get("pod_data"),
        deployment_data=data.get("deployment_data"),
        service_data=data.get("service_data"),
        node_data=data.get("node_data"),
        storage_data=data.get("storage_data"),
        argocd_data=data.get("argocd_data"),
        security_data=data.get("security_data"),
        aws_data=data.get("aws_data"),
        errors=data.get("errors", []),
        enrichment_plan=data.get("enrichment_plan"),
        cluster_name=data.get("cluster_name"),
    )


def _build_k8s_clients(api_server: str | None, token: str) -> dict[str, Any]:
    if not api_server:
        raise SystemExit("--api-server is required unless --context-file is provided")

    configuration = client.Configuration()
    configuration.host = api_server
    configuration.verify_ssl = False
    configuration.api_key = {"authorization": token}
    configuration.api_key_prefix = {"authorization": "Bearer"}
    api_client = client.ApiClient(configuration)
    return {
        "core_v1": client.CoreV1Api(api_client),
        "apps_v1": client.AppsV1Api(api_client),
        "custom_objects": client.CustomObjectsApi(api_client),
        "networking_v1": client.NetworkingV1Api(api_client),
        "rbac_v1": client.RbacAuthorizationV1Api(api_client),
    }


def _parse_categories(values: list[str] | None) -> list[QueryCategory]:
    if not values:
        return DEFAULT_CATEGORIES
    return [QueryCategory(value) for value in values]


def _print_assessment(assessment: dict[str, Any], output: str) -> None:
    if output == "json":
        print(json.dumps(assessment, indent=2))
        return

    print(f"{assessment['severity'].upper()}: {assessment['summary']}")
    for index, incident in enumerate(assessment["incidents"], start=1):
        print(f"\n{index}. [{incident['severity']}] {incident['title']}")
        print(f"   likely cause: {incident['likely_cause']}")
        for evidence in incident["evidence"][:3]:
            print(f"   evidence: {evidence['source']}:{evidence['signal']} - {evidence['detail']}")
        if incident["safe_next_steps"]:
            print("   next:")
            for step in incident["safe_next_steps"][:3]:
                print(f"   - {step}")

    if assessment["unknowns"]:
        print("\nUnknowns:")
        for unknown in assessment["unknowns"]:
            print(f"- {unknown}")


if __name__ == "__main__":
    sys.exit(main())
