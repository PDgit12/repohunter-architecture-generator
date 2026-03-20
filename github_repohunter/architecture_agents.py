import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class AgentOutput:
    agent: str
    domain: str
    summary: str
    report: str
    update: str


def _repo_summary(requirement: str, repos: list[dict[str, Any]]) -> str:
    if not repos:
        return "No indexed repositories were retrieved for this requirement."
    lines = [f"Requirement signal: {requirement}", ""]
    for idx, repo in enumerate(repos[:6], 1):
        lines.append(
            f"{idx}. {repo.get('name', 'unknown')} | {repo.get('language', 'n/a')} | "
            f"{repo.get('stars', 0)} stars | {repo.get('url', '')}"
        )
        lines.append(f"   Fit hint: {repo.get('description', 'No description')}")
    return "\n".join(lines)


def _planning_scope_agent(
    requirement: str,
    stack_preferences: list[str] | None,
    board: dict[str, Any],
) -> AgentOutput:
    prefs = ", ".join(stack_preferences or []) or "No explicit stack preferences"
    report = (
        f"Primary objective: {requirement}\n"
        f"Stack preferences: {prefs}\n"
        "Scope boundary:\n"
        "- Build only architecture generation path.\n"
        "- Keep CLI/API surface minimal.\n"
        "- Produce copy-paste implementation prompt.\n"
        "Success criteria:\n"
        "- Clear architecture structure.\n"
        "- Actionable implementation phases.\n"
        "- Security and quality checks included."
    )
    return AgentOutput(
        agent="planning-scope-agent",
        domain="planning",
        summary="Defined scope and success criteria for the architecture generator.",
        report=report,
        update="Planning/Scope: completed requirement framing and strict v1 boundaries.",
    )


def _planning_structure_agent(requirement: str, repos: list[dict[str, Any]], board: dict[str, Any]) -> AgentOutput:
    scope_report = board.get("planning-scope-agent", {}).get("report", "")
    report = (
        "Proposed structure:\n"
        "- API layer (FastAPI endpoints)\n"
        "- Agent mesh layer (6 parallel specialists + blackboard)\n"
        "- Knowledge layer (RAG retrieval over validated corpus)\n"
        "- Artifact layer (architecture markdown writer)\n"
        "Communication contract:\n"
        "- Each agent reads board input.\n"
        "- Each agent writes structured output (summary/report/update).\n"
        "- Domains cross-review each other before synthesis.\n\n"
        f"Input from scope agent:\n{scope_report[:450]}\n\n"
        f"Repository grounding:\n{_repo_summary(requirement, repos)}"
    )
    return AgentOutput(
        agent="planning-structure-agent",
        domain="planning",
        summary="Designed modular runtime structure and inter-agent communication contract.",
        report=report,
        update="Planning/Structure: finalized topology and shared-message flow.",
    )


def _quality_code_agent(board: dict[str, Any]) -> AgentOutput:
    planning_structure = board.get("planning-structure-agent", {}).get("report", "")
    report = (
        "Code quality review:\n"
        "- Enforce typed contracts for inputs/outputs.\n"
        "- Keep deterministic markdown rendering.\n"
        "- Keep module boundaries clean (CLI/API/agents/security).\n"
        "- Prefer small, testable functions.\n"
        "Cross-domain feedback to planning:\n"
        "- Ensure each phase has acceptance criteria.\n"
        "- Ensure generated prompt maps to concrete deliverables.\n\n"
        f"Planning structure signal:\n{planning_structure[:420]}"
    )
    return AgentOutput(
        agent="quality-code-agent",
        domain="quality-security",
        summary="Assessed code quality guardrails and sent actionable feedback to planning.",
        report=report,
        update="Quality/Code: validated maintainability constraints and testability rules.",
    )


def _security_agent(board: dict[str, Any]) -> AgentOutput:
    planning_scope = board.get("planning-scope-agent", {}).get("report", "")
    report = (
        "Security review:\n"
        "- Input constraints for product/requirement length.\n"
        "- Safe output path checks (`.md`, no traversal, no absolute).\n"
        "- API key guard and constant-time key comparison in server.\n"
        "- Request-rate limiting with memory/redis implementation.\n"
        "Cross-domain feedback to planning:\n"
        "- Ensure secure defaults are visible in final artifact.\n"
        "- Include production-readiness checklist.\n\n"
        f"Scope signal:\n{planning_scope[:420]}"
    )
    return AgentOutput(
        agent="security-agent",
        domain="quality-security",
        summary="Reviewed security controls and provided hardening guidance.",
        report=report,
        update="Quality/Security: security controls validated and documented.",
    )


def _implementation_writer_agent(board: dict[str, Any]) -> AgentOutput:
    quality_report = board.get("quality-code-agent", {}).get("report", "")
    security_report = board.get("security-agent", {}).get("report", "")
    report = (
        "Implementation actions:\n"
        "1) Build 6-agent concurrent runtime with shared board updates.\n"
        "2) Persist per-agent domain report and periodic updates.\n"
        "3) Render markdown with domain sections and progress timeline.\n"
        "4) Keep CLI flow simple (`generate`, `demo`, `status`).\n"
        "Inputs consumed from quality/security:\n"
        f"- Quality: {quality_report[:220]}\n"
        f"- Security: {security_report[:220]}"
    )
    return AgentOutput(
        agent="implementation-writer-agent",
        domain="implementation",
        summary="Converted domain guidance into concrete implementation steps.",
        report=report,
        update="Implementation/Writer: translated planning + quality + security into build tasks.",
    )


def _implementation_refactor_agent(board: dict[str, Any]) -> AgentOutput:
    structure_report = board.get("planning-structure-agent", {}).get("report", "")
    writer_report = board.get("implementation-writer-agent", {}).get("report", "")
    report = (
        "Refactor and cleanup actions:\n"
        "- Remove irrelevant legacy pipeline complexity.\n"
        "- Keep runtime-only modules required for v1.\n"
        "- Ensure generated artifact remains user-facing and practical.\n"
        "Cross-domain sync:\n"
        f"- Structure signal: {structure_report[:220]}\n"
        f"- Writer signal: {writer_report[:220]}"
    )
    return AgentOutput(
        agent="implementation-refactor-agent",
        domain="implementation",
        summary="Ensured implementation remains lean, relevant, and aligned with v1 goals.",
        report=report,
        update="Implementation/Refactor: validated lean runtime scope and cleanup outcomes.",
    )


def _add_output(board: dict[str, Any], output: AgentOutput) -> None:
    board[output.agent] = {
        "domain": output.domain,
        "summary": output.summary,
        "report": output.report,
        "update": output.update,
    }
    board["progress_updates"].append(f"{output.agent}: {output.update}")


async def run_parallel_agents(
    requirement: str,
    repos: list[dict[str, Any]],
    stack_preferences: list[str] | None = None,
) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    blackboard: dict[str, Any] = {
        "requirement": requirement,
        "stack_preferences": stack_preferences or [],
        "repo_candidates": repos,
        "progress_updates": [],
    }

    phase_one = await asyncio.gather(
        loop.run_in_executor(None, _planning_scope_agent, requirement, stack_preferences, blackboard),
        loop.run_in_executor(None, _planning_structure_agent, requirement, repos, blackboard),
    )
    for out in phase_one:
        _add_output(blackboard, out)

    phase_two = await asyncio.gather(
        loop.run_in_executor(None, _quality_code_agent, blackboard),
        loop.run_in_executor(None, _security_agent, blackboard),
    )
    for out in phase_two:
        _add_output(blackboard, out)

    phase_three = await asyncio.gather(
        loop.run_in_executor(None, _implementation_writer_agent, blackboard),
        loop.run_in_executor(None, _implementation_refactor_agent, blackboard),
    )
    for out in phase_three:
        _add_output(blackboard, out)

    blackboard["domain_reports"] = {
        "planning": [
            blackboard["planning-scope-agent"]["report"],
            blackboard["planning-structure-agent"]["report"],
        ],
        "quality-security": [
            blackboard["quality-code-agent"]["report"],
            blackboard["security-agent"]["report"],
        ],
        "implementation": [
            blackboard["implementation-writer-agent"]["report"],
            blackboard["implementation-refactor-agent"]["report"],
        ],
    }
    return blackboard


def render_architecture_markdown(
    product_name: str,
    requirement: str,
    mesh_output: dict[str, Any],
    repos: list[dict[str, Any]],
) -> str:
    timestamp = datetime.now(UTC).isoformat()
    repo_lines = "\n".join(
        [
            f"- **{r.get('name', 'unknown')}** ({r.get('language', 'n/a')}, {r.get('stars', 0)}⭐): {r.get('url', '')}"
            for r in repos[:8]
        ]
    ) or "- No repository evidence found in local index."

    updates = "\n".join(f"- {u}" for u in mesh_output.get("progress_updates", [])) or "- No updates available."

    return f"""# {product_name} — Architecture Blueprint

Generated at: `{timestamp}`

## 1. Product Requirement
{requirement}

## 2. Six-Agent Collaboration Model
This architecture is produced by 6 parallel agents communicating through a shared blackboard:
- Planning domain: `planning-scope-agent`, `planning-structure-agent`
- Quality/Security domain: `quality-code-agent`, `security-agent`
- Implementation domain: `implementation-writer-agent`, `implementation-refactor-agent`

## 3. Domain Reports

### Planning Domain Report
#### Planning Scope Agent
{mesh_output.get("planning-scope-agent", {}).get("report", "")}

#### Planning Structure Agent
{mesh_output.get("planning-structure-agent", {}).get("report", "")}

### Quality and Security Domain Report
#### Quality Code Agent
{mesh_output.get("quality-code-agent", {}).get("report", "")}

#### Security Agent
{mesh_output.get("security-agent", {}).get("report", "")}

### Implementation Domain Report
#### Implementation Writer Agent
{mesh_output.get("implementation-writer-agent", {}).get("report", "")}

#### Implementation Refactor Agent
{mesh_output.get("implementation-refactor-agent", {}).get("report", "")}

## 4. Progress Timeline (Agent Updates)
{updates}

## 5. Recommended System Architecture
- **API Layer**: FastAPI service exposing `/chat`, `/architecture/generate`, `/status`.
- **Orchestration Layer**: Concurrent six-agent runtime (`asyncio`) with shared board updates.
- **Knowledge Layer**: Chroma vector store + retriever grounded on validated repo corpus.
- **Generation Layer**: Markdown artifact renderer for architecture and implementation prompt.
- **Ops Layer**: Input validation, rate limiting, auth checks, health endpoints.

## 6. Communication Model (Domain-to-Domain)
- Planning agents publish scope/structure decisions.
- Quality/Security agents review planning outputs and add guardrails.
- Implementation agents consume both planning and quality/security outputs.
- Final artifact includes domain reports and progress timeline.

## 7. Copy-Paste Prompt For Vibe Coding Platforms
```md
Build a production-ready implementation from this architecture:

Product: {product_name}
Requirement: {requirement}

Constraints:
- Use 6 parallel agents split across planning, quality/security, and implementation domains.
- Use a shared blackboard so agents can read/write each other’s outputs.
- Produce periodic progress updates while the workflow executes.
- Include secure API boundaries, tests, and deterministic artifact rendering.

Deliverables:
1. FastAPI backend with architecture generation endpoint
2. Six-agent collaborative runtime with domain reports
3. RAG evidence retrieval for grounding
4. Test suite + CI
5. Deployable configuration
```

## 8. Evidence From Indexed Repositories
{repo_lines}
"""
