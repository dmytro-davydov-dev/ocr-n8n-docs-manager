"""Export the FastAPI app's OpenAPI schema to a versioned JSON file.

`packages/api-client` is written by hand against this contract today; once
it is generated, this file is what the generator and the CI drift check
(`make verify-openapi`) both read. Run via `make export-openapi`.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATH = REPO_ROOT / "packages" / "api-client" / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUTPUT_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"Wrote OpenAPI schema to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
