import os
import json
from pathlib import Path
import pytest

# Unit tests never call a live model; agent behaviour is tested in test_agent.py with a stub.
os.environ["USE_AGENT"] = "false"


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    from app.config import get_settings
    from app.storage.local import LocalStorage
    orgs = ["org_campus_workshop", "org_campus_lab", "org_data_center"]
    monkeypatch.setenv("API_TOKENS_JSON", json.dumps([
        {"token": "test-administrator-credential-only", "subject": "Test admin", "role": "admin", "org_ids": orgs},
        {"token": "test-workshop-operator-credential", "subject": "Workshop operator", "role": "operator", "org_ids": [orgs[0]]},
        {"token": "test-lab-reviewer-credential", "subject": "Lab reviewer", "role": "reviewer", "org_ids": [orgs[1]]},
    ]))
    monkeypatch.setenv("USE_AGENT", "false")
    monkeypatch.setenv("STORAGE", "local")
    monkeypatch.setattr(LocalStorage.__init__, "__defaults__", (Path(tmp_path) / "loopback.db", None))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
