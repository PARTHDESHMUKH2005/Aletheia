"""Orchestrator tests. The Strands Agent is stubbed so these run offline; they check
the tool wiring, the call cap, the guardrails inside tools, and that the pipeline
completes correctly whether the agent behaves, misbehaves, or fails outright.
"""
import json
import tempfile
from pathlib import Path

import pytest

from app import agent as agent_mod
from app import pipeline
from app.config import get_settings
from app.storage.local import LocalStorage
from tests.test_pipeline import make_characterization, seed_stream


@pytest.fixture
def storage():
    with tempfile.TemporaryDirectory() as tmp:
        yield LocalStorage(db_path=Path(tmp) / "t.db")


def make_ctx(storage, characterization):
    storage.save_upload("p.jpg", b"x")
    storage.create_stream("s1", {"org_id": "o", "photo_keys": ["p.jpg"], "status": "SUBMITTED"})
    ctx = agent_mod.RunContext(
        storage=storage, stream_id="s1", stream=storage.get_stream("s1"),
        org_location={"lat": 30.34, "lng": 76.39, "pincode": "147001"}, slider_w=0.5,
        characterize_fn=lambda *a, **k: characterization,
    )
    return ctx


class FakeAgent:
    """Stands in for strands.Agent: runs a scripted function over the real tools."""
    script = None
    def __init__(self, tools, **kw):
        self.tools = {t.tool_name: t for t in tools}
    def __call__(self, prompt):
        class R:
            metrics = type("M", (), {"accumulated_usage": {"totalTokens": 1}})()
            def __str__(self): return "summary text"
        FakeAgent.script(self.tools)
        return R()


@pytest.fixture
def fake_agent(monkeypatch):
    import strands
    monkeypatch.setattr(strands, "Agent", FakeAgent)
    monkeypatch.setattr("app.config.get_model", lambda tier: None)
    return FakeAgent


def call(tools, name, **kw):
    return json.loads(tools[name](**kw))


def test_well_behaved_agent_routes_and_records_one_handoff(storage, fake_agent):
    ctx = make_ctx(storage, make_characterization())
    def script(t):
        items = call(t, "characterize_waste_tool")["items"]
        r = call(t, "find_processors_tool", item_index=items[0]["index"])
        out = call(t, "record_handoff_tool", item_index=0, processor_id=r["picked_processor_id"])
        assert out["recorded"]
    fake_agent.script = script
    out = agent_mod.run_orchestrator(ctx)
    assert out["summary"] == "summary text" and "error" not in out
    assert ctx.tool_calls == 3
    assert len(storage.get_ledger_chain("s1")) == 1


def test_tools_return_compact_json_without_image_bytes(storage, fake_agent):
    ctx = make_ctx(storage, make_characterization())
    seen = {}
    fake_agent.script = lambda t: seen.update(out=t["characterize_waste_tool"]())
    agent_mod.run_orchestrator(ctx)
    assert "bytes" not in seen["out"] and len(seen["out"]) < 800


def test_handoff_rejects_a_processor_the_agent_made_up(storage, fake_agent):
    ctx = make_ctx(storage, make_characterization())
    res = {}
    def script(t):
        t["characterize_waste_tool"]()
        call(t, "find_processors_tool", item_index=0)
        res.update(call(t, "record_handoff_tool", item_index=0, processor_id="proc_does_not_exist"))
    fake_agent.script = script
    agent_mod.run_orchestrator(ctx)
    assert "error" in res
    assert storage.get_ledger_chain("s1") == []


def test_handoff_before_routing_is_refused(storage, fake_agent):
    ctx = make_ctx(storage, make_characterization())
    res = {}
    def script(t):
        t["characterize_waste_tool"]()
        res.update(call(t, "record_handoff_tool", item_index=0, processor_id="x"))
    fake_agent.script = script
    agent_mod.run_orchestrator(ctx)
    assert "error" in res


def test_bad_item_index_is_an_error_not_a_crash(storage, fake_agent):
    ctx = make_ctx(storage, make_characterization())
    res = {}
    def script(t):
        t["characterize_waste_tool"]()
        res.update(call(t, "find_processors_tool", item_index=7))
    fake_agent.script = script
    agent_mod.run_orchestrator(ctx)
    assert "error" in res


def test_tool_call_cap_stops_a_looping_agent(storage, fake_agent):
    ctx = make_ctx(storage, make_characterization())
    def script(t):
        while True:
            t["lookup_rules_tool"](material="steel_scrap")
    fake_agent.script = script
    out = agent_mod.run_orchestrator(ctx)
    assert "ToolCallCapExceeded" in out["error"]
    assert ctx.tool_calls == agent_mod.MAX_TOOL_CALLS + 1


def test_repeated_handoff_calls_write_one_ledger_entry(storage, fake_agent):
    ctx = make_ctx(storage, make_characterization())
    def script(t):
        t["characterize_waste_tool"]()
        pid = call(t, "find_processors_tool", item_index=0)["picked_processor_id"]
        for _ in range(3):
            t["record_handoff_tool"](item_index=0, processor_id=pid)
    fake_agent.script = script
    agent_mod.run_orchestrator(ctx)
    assert len(storage.get_ledger_chain("s1")) == 1


# --- pipeline integration: the result must be right whatever the agent does ---

@pytest.fixture
def agent_on(monkeypatch):
    monkeypatch.setenv("USE_AGENT", "true")
    get_settings.cache_clear()
    yield
    monkeypatch.setenv("USE_AGENT", "false")
    get_settings.cache_clear()


def test_pipeline_matches_deterministic_result_when_agent_does_nothing(storage, fake_agent, agent_on, monkeypatch):
    monkeypatch.setattr(pipeline, "characterize_waste", lambda *a, **k: make_characterization())
    fake_agent.script = lambda t: None
    seed_stream(storage)
    result = pipeline.run_pipeline("s1", storage=storage)
    assert result["status"] == "ROUTED"
    assert result["routing"][0]["picked_processor_id"] is not None
    assert len(storage.get_ledger_chain("s1")) == 1
    assert result["agent"]["summary"] == "summary text"


def test_pipeline_survives_agent_crash(storage, agent_on, monkeypatch):
    monkeypatch.setattr(pipeline, "characterize_waste", lambda *a, **k: make_characterization())
    def boom(*a, **k): raise RuntimeError("provider down")
    monkeypatch.setattr(pipeline, "run_orchestrator", lambda ctx: {"error": "RuntimeError: provider down", "tool_calls": 0})
    seed_stream(storage)
    result = pipeline.run_pipeline("s1", storage=storage)
    assert result["status"] == "ROUTED"
    assert "error" in result["agent"]


def test_pipeline_does_not_double_record_handoff_after_agent(storage, fake_agent, agent_on, monkeypatch):
    monkeypatch.setattr(pipeline, "characterize_waste", lambda *a, **k: make_characterization())
    def script(t):
        t["characterize_waste_tool"]()
        pid = call(t, "find_processors_tool", item_index=0)["picked_processor_id"]
        t["record_handoff_tool"](item_index=0, processor_id=pid)
    fake_agent.script = script
    seed_stream(storage)
    pipeline.run_pipeline("s1", storage=storage)
    assert len(storage.get_ledger_chain("s1")) == 1


def test_hazardous_low_confidence_still_needs_review_with_agent(storage, fake_agent, agent_on, monkeypatch):
    monkeypatch.setattr(pipeline, "characterize_waste",
                        lambda *a, **k: make_characterization(material="battery_lead_acid", hazardous=True, confidence=0.8))
    fake_agent.script = lambda t: None
    seed_stream(storage)
    assert pipeline.run_pipeline("s1", storage=storage)["status"] == "NEEDS_REVIEW"


def test_model_failure_marks_stream_failed_not_stuck(storage, monkeypatch):
    def boom(*a, **k): raise RuntimeError("quota exceeded")
    monkeypatch.setattr(pipeline, "characterize_waste", boom)
    seed_stream(storage)
    with pytest.raises(RuntimeError):
        pipeline.run_pipeline("s1", storage=storage)
    stream = storage.get_stream("s1")
    assert stream["status"] == "FAILED" and "quota" in stream["error"]
