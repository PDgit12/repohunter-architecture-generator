import argparse
import asyncio
import json

from github_repohunter.architecture_agents import run_parallel_agents, render_architecture_markdown
from github_repohunter.rag_engine import build_index, retrieve
from github_repohunter.security_utils import validate_markdown_output_path


def _banner() -> None:
    print("=" * 58)
    print("🏹 REPOHUNTER HUB")
    print("Parallel Agent Architecture Generator")
    print("=" * 58)


def _generate() -> None:
    _banner()
    product = input("Product name: ").strip()
    requirement = input("Core requirement/problem statement: ").strip()
    if not product or not requirement:
        print("❌ Product name and requirement are required.")
        return

    output = input("Output markdown path [architecture.md]: ").strip() or "architecture.md"
    stacks_raw = input("Preferred stack (comma-separated, optional): ").strip()
    stack_preferences = [s.strip() for s in stacks_raw.split(",") if s.strip()] if stacks_raw else None

    try:
        output_path = validate_markdown_output_path(output)
    except ValueError as exc:
        print(f"❌ Invalid output path: {exc}")
        return

    print("\n🔍 Loading retrieval index...")
    repos = []
    try:
        collection = build_index()
        repos = retrieve(collection, requirement, n_results=8)
        print(f"✅ Retrieved {len(repos)} reference repos")
    except Exception as exc:
        print(f"⚠️ Retrieval unavailable, continuing without context: {exc}")

    print("🤝 Running parallel agent mesh...")
    mesh_output = asyncio.run(
        run_parallel_agents(
            requirement=requirement,
            repos=repos,
            stack_preferences=stack_preferences,
        )
    )

    markdown = render_architecture_markdown(
        product_name=product,
        requirement=requirement,
        mesh_output=mesh_output,
        repos=repos,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"✅ architecture generated: {output_path}")
    print("💡 You can now copy the final prompt section into your coding platform.")


def _status(as_json: bool = False) -> None:
    payload = {
        "index_exists": True,
        "server_entrypoint": "python -m github_repohunter.server",
        "cli_entrypoint": "repohunter",
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        _banner()
        print(f"Index available: {payload['index_exists']}")
        print(f"Server entrypoint: {payload['server_entrypoint']}")
        print(f"CLI entrypoint: {payload['cli_entrypoint']}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="repohunter-hub", description="Minimal RepoHunter runtime hub")
    parser.add_argument("command", choices=["generate", "status"])
    parser.add_argument("--json", action="store_true", help="JSON output for status command")
    args = parser.parse_args()

    if args.command == "generate":
        _generate()
        return
    _status(as_json=args.json)


if __name__ == "__main__":
    main()
