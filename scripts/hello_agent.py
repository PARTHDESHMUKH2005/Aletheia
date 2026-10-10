"""Phase 0 smoke test (BUILD.md section 9/10).

1. A Strands Agent with one tool, to prove the tool-calling path works.
2. One vision call on a single photo, structured into the Characterization
   schema from section 5, to prove the image -> structured-output path works.

Usage: python scripts/hello_agent.py eval/test_photos/<photo>.jpg
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(ROOT / ".env")

from strands import Agent, tool  # noqa: E402

from app.config import get_model  # noqa: E402
from app.models import Characterization  # noqa: E402


@tool
def ping() -> str:
    """Returns pong. Exists only to prove the agent can call a tool."""
    return "pong"


def run_tool_smoke_test() -> str:
    agent = Agent(model=get_model("orch"), tools=[ping])
    result = agent("Call the ping tool and tell me exactly what it returned.")
    return str(result)


def run_vision_smoke_test(photo_path: Path) -> Characterization:
    image_format = photo_path.suffix.lstrip(".").lower()
    if image_format == "jpg":
        image_format = "jpeg"

    prompt = [
        {
            "text": (
                "Characterize the waste item in this photo. Return every field "
                "in the schema. If quantity is not visible, estimate it and set "
                "quantity_basis to 'estimated'."
            )
        },
        {
            "image": {
                "format": image_format,
                "source": {"bytes": photo_path.read_bytes()},
            }
        },
    ]

    agent = Agent(model=get_model("fast"), tools=[])
    result = agent(prompt, structured_output_model=Characterization)
    return result.structured_output


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <photo path>", file=sys.stderr)
        sys.exit(1)

    photo_path = Path(sys.argv[1])
    if not photo_path.exists():
        print(f"No such file: {photo_path}", file=sys.stderr)
        sys.exit(1)

    print("--- tool smoke test ---")
    print(run_tool_smoke_test())

    print("\n--- vision smoke test ---")
    characterization = run_vision_smoke_test(photo_path)
    print(json.dumps(characterization.model_dump(), indent=2))


if __name__ == "__main__":
    main()
