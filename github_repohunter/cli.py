import argparse
import asyncio
import json
import os
from pathlib import Path

from github_repohunter.architecture_agents import run_parallel_agents, render_architecture_markdown
from github_repohunter.rag_engine import build_index, retrieve
from github_repohunter.security_utils import validate_markdown_output_path


def _banner() -> str:
    return (
        "╭──────────────────────────────────────────────╮\n"
        "│               RepoHunter CLI                │\n"
        "│    Parallel Agent Architecture Generator     │\n"
        "╰──────────────────────────────────────────────╯"
    )


def _print_section(title: str) -> None:
    print(f"\n▶ {title}")


def _load_repos(requirement: str, top_k: int) -> list[dict]:
    try:
        collection = build_index()
        return retrieve(collection, requirement, n_results=top_k)
    except Exception:
        return []


def cmd_generate(args: argparse.Namespace) -> int:
    product = args.product.strip()
    requirement = args.requirement.strip()
    if not product:
        raise SystemExit("error: --product cannot be empty")
    if not requirement:
        raise SystemExit("error: --requirement cannot be empty")
    if len(product) > 200:
        raise SystemExit("error: --product too long (max 200 chars)")
    if len(requirement) > 8000:
        raise SystemExit("error: --requirement too long (max 8000 chars)")
    if args.top_k < 1 or args.top_k > 25:
        raise SystemExit("error: --top-k must be in range [1, 25]")

    if not args.json:
        print(_banner())
        _print_section("Input")
        print(f"Product       : {product}")
        print(f"Requirement   : {requirement[:140]}{'...' if len(requirement) > 140 else ''}")
        print(f"Top-K         : {args.top_k}")
        print(f"PreferredStack: {', '.join(args.stack) if args.stack else 'None'}")

    if not args.json:
        _print_section("Retrieval")
    repos = _load_repos(args.requirement, args.top_k)
    if not args.json:
        print(f"Retrieved repos: {len(repos)}")
        for idx, repo in enumerate(repos[:3], 1):
            print(f"  {idx}. {repo.get('name','unknown')} ({repo.get('stars',0)}⭐)")

    if not args.json:
        _print_section("Parallel Agent Mesh")
        print("Running: requirements-analyst, system-designer, execution-planner")
        print("Reviewer loop: requirements-reviewer, design-reviewer, execution-reviewer")
        print("Synthesizer: synthesis-agent")

    mesh_output = asyncio.run(
        run_parallel_agents(
            requirement=requirement,
            repos=repos,
            stack_preferences=args.stack,
        )
    )
    markdown = render_architecture_markdown(
        product_name=product,
        requirement=requirement,
        mesh_output=mesh_output,
        repos=repos,
    )

    try:
        output_path = validate_markdown_output_path(args.output)
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    if args.json:
        print(
            json.dumps(
                {
                    "output_path": str(output_path),
                    "repos_used": len(repos),
                    "agents": sorted(k for k in mesh_output.keys() if "-" in k),
                },
                indent=2,
            )
        )
    else:
        _print_section("Output")
        print("✅ architecture generated successfully")
        print(f"📄 markdown file : {output_path}")
        print(f"📚 repos used    : {len(repos)}")
        print(f"🤝 agents active : {len([k for k in mesh_output.keys() if '-' in k])}")
        print("💡 Next step     : copy the prompt section from the generated markdown into your coding platform")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    demo_requirement = (
        "Design a production-ready AI architecture copilot that generates architecture.md "
        "for SaaS teams with scalable API, worker orchestration, and observability."
    )
    ns = argparse.Namespace(
        product="RepoHunter Demo Product",
        requirement=demo_requirement,
        output=args.output,
        top_k=6,
        stack=["FastAPI", "PostgreSQL", "Redis", "React"],
        json=args.json,
    )
    return cmd_generate(ns)


def cmd_status(args: argparse.Namespace) -> int:
    out = {
        "cwd": os.getcwd(),
        "index_exists": Path("github_repohunter/database/chroma").exists(),
        "server_module": "github_repohunter.server",
    }
    if getattr(args, "json", False):
        print(json.dumps(out, indent=2))
        return 0
    print(_banner())
    _print_section("Status")
    print(f"Working directory : {out['cwd']}")
    print(f"RAG index exists  : {out['index_exists']}")
    print(f"Server module     : {out['server_module']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repohunter", description="RepoHunter CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate architecture markdown")
    gen.add_argument("--product", required=True, help="Product name")
    gen.add_argument("--requirement", required=True, help="Requirement statement")
    gen.add_argument("--output", default="architecture.md", help="Output markdown path")
    gen.add_argument("--top-k", type=int, default=8, help="Number of repos to retrieve")
    gen.add_argument("--stack", action="append", default=[], help="Preferred stack (repeatable)")
    gen.add_argument("--json", action="store_true", help="JSON output summary")
    gen.set_defaults(func=cmd_generate)

    demo = sub.add_parser("demo", help="Run one-command showcase")
    demo.add_argument("--output", default="architecture.demo.md", help="Demo output path")
    demo.add_argument("--json", action="store_true", help="JSON output summary")
    demo.set_defaults(func=cmd_demo)

    status = sub.add_parser("status", help="Show local status")
    status.add_argument("--json", action="store_true", help="JSON output")
    status.set_defaults(func=cmd_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    code = args.func(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
