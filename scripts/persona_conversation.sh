#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <persona> <brief-path> <artifact-path>" >&2
  exit 2
fi

PERSONA="$1"
BRIEF="$2"
ARTIFACT="$3"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PERSONA_FILE="$ROOT_DIR/reviews/personas/$PERSONA.md"
CONTRACT_FILE="$ROOT_DIR/reviews/review_contract.md"

if ! command -v opencode >/dev/null 2>&1; then
  echo "OpenCode is required. Install it and configure a model before starting a persona conversation." >&2
  exit 1
fi

for path in "$PERSONA_FILE" "$CONTRACT_FILE" "$BRIEF" "$ARTIFACT"; do
  if [ ! -f "$path" ]; then
    echo "File not found: $path" >&2
    exit 1
  fi
done

PROMPT="Act as the attached persona for this review. Follow the attached review contract. The attached review brief and artifact are the only review inputs. Start pass one now: ask at most five targeted clarification questions. Do not critique or synthesize until I answer."

exec opencode run "$PROMPT" \
  --interactive \
  --title "Persona review: $PERSONA" \
  --file "$CONTRACT_FILE" \
  --file "$PERSONA_FILE" \
  --file "$BRIEF" \
  --file "$ARTIFACT"
