import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.persona_review import build_packet, read_brief, route_personas


VALID_BRIEF = """# Review Brief

## Audience

Engineering leadership.

## Goal

Approve an architecture decision.

## Requested Decision or Action

Approve the migration plan.
"""


class PersonaReviewTest(unittest.TestCase):
    def test_read_brief_requires_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            brief_path = Path(directory) / "brief.md"
            brief_path.write_text(
                "# Review Brief\n\n## Audience\n\nTeam\n\n## Goal\n\n"
                "## Requested Decision or Action\n\nApprove it.\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Goal"):
                read_brief(brief_path)

    def test_routes_technical_architecture_to_principal_engineer(self) -> None:
        roles = route_personas(VALID_BRIEF, [Path("architecture.md")])
        self.assertIn("principal_software_engineer", roles)

    def test_packet_embeds_text_artifacts_and_local_only_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "proposal.md"
            artifact.write_text("Use a versioned data contract.", encoding="utf-8")
            packet = build_packet(VALID_BRIEF, [artifact], ["data_engineer"])
        self.assertIn("does not invoke a model", packet)
        self.assertIn("Use a versioned data contract.", packet)
        self.assertIn("# Data Engineer", packet)


if __name__ == "__main__":
    unittest.main()
