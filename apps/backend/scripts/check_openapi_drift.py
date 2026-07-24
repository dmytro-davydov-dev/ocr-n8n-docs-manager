"""CI drift check: fail if the committed OpenAPI schema is stale.

Regenerates the schema in memory and diffs it against
`packages/api-client/openapi.json`. Run via `make verify-openapi`.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
COMMITTED_PATH = REPO_ROOT / "packages" / "api-client" / "openapi.json"


def main() -> int:
    if not COMMITTED_PATH.exists():
        print(f"{COMMITTED_PATH} does not exist. Run `make export-openapi` and commit it.")
        return 1

    current = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    committed = COMMITTED_PATH.read_text()

    if current != committed:
        print(
            "OpenAPI schema is out of date with packages/api-client/openapi.json.\n"
            "Run `make export-openapi` and commit the result."
        )
        return 1

    print("OpenAPI schema matches packages/api-client/openapi.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
