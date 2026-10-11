"""One-command local demo (no AWS): upload a photo, run the pipeline, show the
routing decision, move the slider, show the counterfactual receipt, verify the
ledger, tamper a row, and show verify turn red.

Usage: python scripts/run_demo.py [path/to/photo.jpg]
"""
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


from app.storage.local import LocalStorage  # noqa: E402
from app.pipeline import run_pipeline  # noqa: E402
from app.tools import ledger, matching  # noqa: E402
from app.models import Item  # noqa: E402
from app.uploads import validate_image  # noqa: E402


def section(title: str) -> None:
    print(f"\n{'=' * 10} {title} {'=' * 10}")


def main() -> None:
    photo_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "eval" / "test_photos" / "metal1.jpg"
    if not photo_path.exists():
        print(f"No such file: {photo_path}", file=sys.stderr)
        sys.exit(1)

    storage = LocalStorage(db_path=ROOT / ".local_data" / "demo.db")
    stream_id = f"demo-{uuid.uuid4().hex[:8]}"

    photo_bytes = photo_path.read_bytes()
    mime = validate_image(photo_bytes)
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[mime]
    photo_key = f"org_campus_workshop/{uuid.uuid4().hex}.{extension}"
    storage.save_upload(photo_key, photo_bytes)
    storage.create_stream(stream_id, {
        "org_id": "org_campus_workshop",
        "pincode": "147001",
        "note": "demo run via scripts/run_demo.py",
        "quantity_kg": None,
        "photo_keys": [photo_key],
        "slider_w": 0.5,
        "status": "SUBMITTED",
    })

    section("1. Running the pipeline (real Gemini vision call)")
    result = run_pipeline(stream_id, storage=storage)
    print(f"stream_id={stream_id} status={result['status']} timings={result['timings']}")

    section("2. Characterization")
    print(json.dumps(result["characterization"], indent=2))

    section("3. Routing decision (slider_w=0.5)")
    print(json.dumps(result["routing"], indent=2))

    section("4. Counterfactual receipt")
    print(json.dumps(result["receipts"], indent=2))

    section("5. Moving the slider (w=0.0 vs w=1.0) on the characterized item")
    item = Item.model_validate(result["characterization"]["items"][0])
    org_location = {"lat": 30.3398, "lng": 76.3869}
    pick_money = matching.find_processors(item, org_location, w=0.0)
    pick_carbon = matching.find_processors(item, org_location, w=1.0)
    print(f"w=0.0 (max money) picks: {pick_money['picked_processor_id']}")
    print(f"w=1.0 (max carbon) picks: {pick_carbon['picked_processor_id']}")
    if pick_money["picked_processor_id"] == pick_carbon["picked_processor_id"]:
        print(
            "Same pick at both extremes -- this material currently has only one "
            "seeded processor with both a sourced price AND a sourced CO2e factor "
            "(see data/processors.json / data/prices.json / data/co2.json), so "
            "there's nothing to trade off against yet. tests/test_matching.py "
            "proves the slider mechanism itself works, with two synthetic processors."
        )

    section("6. Ledger verify (should be ok)")
    print(json.dumps(ledger.verify(storage, stream_id), indent=2))

    section("7. Tampering one ledger row directly in the DB")
    storage._conn.execute(
        "UPDATE ledger SET payload_json = ? WHERE chain_id = ? AND link_no = 1",
        ('{"tampered":true}', stream_id),
    )
    storage._conn.commit()
    print("Tampered link_no=1's payload_json directly.")

    section("8. Ledger verify (should now be red)")
    print(json.dumps(ledger.verify(storage, stream_id), indent=2))


if __name__ == "__main__":
    main()
