"""Prepare local review packets for the repository's persona panel."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REVIEW_DIR = ROOT / "reviews"
PERSONA_DIR = REVIEW_DIR / "personas"
REQUIRED_BRIEF_SECTIONS = ("Audience", "Goal", "Requested Decision or Action")
PERSONAS = {
    "ceo": {
        "path": PERSONA_DIR / "ceo.md",
        "terms": ("strategy", "business", "decision", "roadmap", "investment", "executive"),
    },
    "marketing_leader": {
        "path": PERSONA_DIR / "marketing_leader.md",
        "terms": ("audience", "positioning", "message", "customer", "launch", "presentation"),
    },
    "data_engineer": {
        "path": PERSONA_DIR / "data_engineer.md",
        "terms": ("data", "metric", "analytics", "schema", "dbt", "pipeline", "warehouse"),
    },
    "platform_engineer": {
        "path": PERSONA_DIR / "platform_engineer.md",
        "terms": ("platform", "infrastructure", "deploy", "security", "reliability", "kubernetes", "operat"),
    },
    "principal_software_engineer": {
        "path": PERSONA_DIR / "principal_software_engineer.md",
        "terms": ("architecture", "code", "software", "api", "interface", "migration", "design"),
    },
}
TEXT_EXTENSIONS = {".md", ".txt", ".rst", ".py", ".sql", ".yaml", ".yml", ".json", ".toml"}


def read_brief(path: Path) -> str:
    """Load a brief and ensure it supplies the minimum review context."""
    brief = path.read_text(encoding="utf-8")
    missing = [
        section
        for section in REQUIRED_BRIEF_SECTIONS
        if not (match := re.search(
            rf"^## {re.escape(section)}\s*\n(.*?)(?=^## |\Z)",
            brief,
            re.MULTILINE | re.DOTALL,
        )) or not match.group(1).strip()
    ]
    if missing:
        raise ValueError("Review brief is missing content for: " + ", ".join(missing))
    return brief


def route_personas(brief: str, artifacts: list[Path]) -> list[str]:
    """Route roles by transparent keyword matching; use the full panel as a safe fallback."""
    corpus = brief.lower() + " " + " ".join(path.name.lower() for path in artifacts)
    selected = [
        name for name, persona in PERSONAS.items() if any(term in corpus for term in persona["terms"])
    ]
    return selected or list(PERSONAS)


def artifact_section(path: Path) -> str:
    """Embed text artifacts; retain binary artifact references without extracting them."""
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return f"## Artifact: {path}\n\nBinary artifact. Inspect the file locally: `{path}`.\n"
    return f"## Artifact: {path}\n\n```\n{path.read_text(encoding='utf-8')}\n```\n"


def build_packet(brief: str, artifacts: list[Path], roles: list[str]) -> str:
    contract = (REVIEW_DIR / "review_contract.md").read_text(encoding="utf-8")
    artifact_text = "\n".join(artifact_section(path) for path in artifacts)
    role_text = "\n\n".join(PERSONAS[role]["path"].read_text(encoding="utf-8") for role in roles)
    selected = ", ".join(roles)
    return (
        "# Persona Review Packet\n\n"
        "This packet is generated locally. It does not invoke a model or transmit artifact content. "
        "If you submit it to a model, you are responsible for that provider's data handling.\n\n"
        f"## Routed Personas\n\n{selected}\n\n"
        f"{contract}\n\n# Review Brief\n\n{brief}\n\n# Submitted Artifacts\n\n"
        f"{artifact_text}\n# Persona Instructions\n\n{role_text}\n\n"
        "# Synthesis Instructions\n\n"
        "After collecting independent persona reports, synthesize only the reported findings. "
        "List the highest-priority changes, consensus findings, material disagreements and tradeoffs, "
        "rehearsal questions when relevant, and decisions retained for the author.\n"
    )


def parse_roles(value: str) -> list[str]:
    roles = [role.strip() for role in value.split(",") if role.strip()]
    unknown = [role for role in roles if role not in PERSONAS]
    if unknown:
        raise ValueError("Unknown persona(s): " + ", ".join(unknown))
    return roles


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a local persona review packet.")
    parser.add_argument("--brief", type=Path, required=True, help="Markdown review brief.")
    parser.add_argument("--artifact", type=Path, action="append", required=True, help="Artifact path; repeat as needed.")
    parser.add_argument("--roles", help="Comma-separated override, for example ceo,marketing_leader.")
    parser.add_argument("--output", type=Path, required=True, help="New Markdown packet path.")
    args = parser.parse_args()

    if args.output.exists():
        parser.error(f"Refusing to overwrite existing output: {args.output}")
    missing = [path for path in [args.brief, *args.artifact] if not path.is_file()]
    if missing:
        parser.error("File not found: " + ", ".join(str(path) for path in missing))

    try:
        brief = read_brief(args.brief)
        roles = parse_roles(args.roles) if args.roles else route_personas(brief, args.artifact)
    except ValueError as exc:
        parser.error(str(exc))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_packet(brief, args.artifact, roles), encoding="utf-8")
    print(f"Prepared local review packet: {args.output}")
    print("Routed personas: " + ", ".join(roles))


if __name__ == "__main__":
    main()
