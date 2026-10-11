"""build_orchestrator(): the Strands Agent with the tools, the hierarchy system prompt, and the tool-call cap.

The agent decides the order of tool calls and writes a short summary. It never sees
image bytes (characterize_waste returns compact JSON) and it cannot alter items: tools
take an item index, and every number comes from deterministic code. All guardrails run
inside the tools, and the pipeline re-checks the run afterwards (see pipeline.py), so a
confused or stalled agent can only make a run slower, never unsafe.
"""
import json
import logging
import threading
import time
from dataclasses import dataclass, field

from app.models import Characterization
from app.tools.characterize import PhotoBlock, characterize_waste
from app.tools.guardrails import out_of_scope_flag
from app.tools.ledger import record_handoff
from app.tools.matching import find_processors
from app.tools.rules import lookup_rules

logger = logging.getLogger("loopback.agent")

MAX_TOOL_CALLS = 12

SYSTEM_PROMPT = """You are LoopBack's routing orchestrator for an organization's waste stream.

Work in this order:
1. Call characterize_waste_tool once. It returns the items (by index) with material, quantity, hazard flags and confidence.
2. For each item call find_processors_tool with its index. Optionally call lookup_rules_tool for a material whose rule you want to cite.
3. For each item that find_processors_tool says has a picked_processor_id and is not refused, call record_handoff_tool with that item's index and the picked processor id.
4. Finish with a summary of at most 4 sentences.

Waste hierarchy, best first: reuse, refurbish, recycle, recovery, disposal. Prefer the highest tier a processor can honestly serve.

Rules:
- Route and flag only. Never give handling, safety, repair or disposal advice.
- Never invent processors, prices, quantities or rules. Use only what tools return.
- If an item is refused or review_required, say it needs human review. Do not try to route it another way.
- Do not call any tool twice with the same arguments. Stop as soon as every item is handled."""


class ToolCallCapExceeded(RuntimeError):
    pass


@dataclass
class RunContext:
    """Everything one pipeline run shares with its tools. Tools return compact JSON;
    full results stay here for the pipeline to persist.
    """
    storage: object
    stream_id: str
    stream: dict
    org_location: dict
    slider_w: float
    characterization: Characterization | None = None
    characterize_ms: int = 0
    routings: dict = field(default_factory=dict)       # item index -> routing result or refusal
    handed_off: set = field(default_factory=set)        # item indexes with a ledger 'requested' entry
    tool_calls: int = 0
    lock: threading.RLock = field(default_factory=threading.RLock)  # tools may be run in parallel threads
    characterize_fn: object = None                      # overridable so tests/pipeline can inject

    def count_call(self) -> None:
        self.tool_calls += 1
        if self.tool_calls > MAX_TOOL_CALLS:
            raise ToolCallCapExceeded(f"tool-call cap of {MAX_TOOL_CALLS} exceeded")


def _guess_format(key: str) -> str:
    ext = key.rsplit(".", 1)[-1].lower() if "." in key else "jpeg"
    return "jpeg" if ext == "jpg" else ext


def run_characterize(ctx: RunContext) -> Characterization:
    """Idempotent within a run: the images enter a model exactly once."""
    if ctx.characterization is None:
        t0 = time.monotonic()
        photos: list[PhotoBlock] = [
            {"format": _guess_format(key), "bytes": ctx.storage.read_upload(key)}
            for key in ctx.stream["photo_keys"]
        ]
        ctx.characterization = (ctx.characterize_fn or characterize_waste)(
            photos, note=ctx.stream.get("note", ""), quantity_kg=ctx.stream.get("quantity_kg"), storage=ctx.storage,
        )
        ctx.characterize_ms = int((time.monotonic() - t0) * 1000)
    return ctx.characterization


def route_item(ctx: RunContext, index: int) -> dict:
    """Routes one item (guardrails included) and caches the result. Shared by the
    agent's tool and the pipeline's fallback, so both paths give identical answers.
    """
    if index in ctx.routings:
        return ctx.routings[index]
    item = ctx.characterization.items[index]
    flag = out_of_scope_flag(item)
    if flag:
        result = {"refused": True, "out_of_scope_category": flag}
    else:
        result = find_processors(item, ctx.org_location, w=ctx.slider_w)
    ctx.routings[index] = result
    return result


def hand_off(ctx: RunContext, index: int, processor_id: str) -> dict:
    """Records the 'requested' ledger entry once per item."""
    if index in ctx.handed_off:
        return {"already_recorded": True}
    item = ctx.characterization.items[index]
    entry = record_handoff(ctx.storage, ctx.stream_id, processor_id, "requested", item)
    ctx.handed_off.add(index)
    return entry


def routed_processor_id(routing: dict) -> str | None:
    if routing.get("refused"):
        return None
    return routing.get("picked_processor_id") or routing.get("reuse_recommended_processor_id")


def _compact_item(index: int, item) -> dict:
    return {
        "index": index, "material": item.material, "quantity_kg": item.quantity_kg,
        "quantity_basis": item.quantity_basis, "purity": item.purity, "hazardous": item.hazardous,
        "is_storage_device": item.is_storage_device, "confidence": item.confidence,
        "contaminants": item.contaminants, "note": item.composition_note[:160],
    }


def _compact_routing(index: int, routing: dict) -> dict:
    if routing.get("refused"):
        return {"index": index, "refused": True, "out_of_scope_category": routing["out_of_scope_category"],
                "next": "needs human review"}
    return {
        "index": index,
        "picked_processor_id": routed_processor_id(routing),
        "review_required": routing["review_required"],
        "rule_name": routing["rule_name"],
        "explanation": routing["explanation"],
        "top_candidates": [
            {"processor_id": c["processor_id"], "name": c["name"], "tier": c["tier"],
             "distance_km": c["distance_km"], "score": c["score"]}
            for c in routing["candidates"][:3]
        ],
    }


def build_orchestrator(ctx: RunContext):
    """Returns a Strands Agent whose tools are bound to ctx. Built per run because
    the tools close over the run's stream; the model object itself is cheap.
    """
    from strands import Agent, tool

    from app.config import get_model, get_retry_strategy

    def guarded(name, fn):
        with ctx.lock:
            return _guarded(name, fn)

    def _guarded(name, fn):
        ctx.count_call()
        start = time.monotonic()
        try:
            return fn()
        finally:
            logger.info(json.dumps({"step": "tool", "tool": name, "stream_id": ctx.stream_id,
                                    "ms": int((time.monotonic() - start) * 1000), "n": ctx.tool_calls}))

    @tool
    def characterize_waste_tool() -> str:
        """Characterize the stream's photos. Returns the items (each with an index) as compact JSON. Call once."""
        def run():
            c = run_characterize(ctx)
            return json.dumps({"overall_confidence": c.overall_confidence,
                               "items": [_compact_item(i, it) for i, it in enumerate(c.items)]})
        return guarded("characterize_waste", run)

    @tool
    def lookup_rules_tool(material: str, hazardous: bool = False) -> str:
        """Look up the rule that governs a material (rule name, handler requirement, paperwork, whether review is required)."""
        return guarded("lookup_rules", lambda: json.dumps(lookup_rules(material, hazardous)))

    @tool
    def find_processors_tool(item_index: int) -> str:
        """Find and rank authorized processors for one item by its index. Guardrails (rules, hazardous authorization, out-of-scope) are applied inside."""
        def run():
            items = run_characterize(ctx).items
            if not 0 <= item_index < len(items):
                return json.dumps({"error": f"item_index must be 0 to {len(items) - 1}"})
            return json.dumps(_compact_routing(item_index, route_item(ctx, item_index)))
        return guarded("find_processors", run)

    @tool
    def record_handoff_tool(item_index: int, processor_id: str) -> str:
        """Record the 'requested' handoff for one item with the processor find_processors_tool picked for it."""
        def run():
            if item_index not in ctx.routings:
                return json.dumps({"error": "call find_processors_tool for this item first"})
            expected = routed_processor_id(ctx.routings[item_index])
            if expected is None:
                return json.dumps({"error": "this item has no processor to hand off to; it needs review"})
            if processor_id != expected:
                return json.dumps({"error": f"processor_id must be the picked processor: {expected}"})
            entry = hand_off(ctx, item_index, processor_id)
            return json.dumps({"recorded": True, "link_no": entry.get("link_no")})
        return guarded("record_handoff", run)

    return Agent(
        model=get_model("orch"),
        tools=[characterize_waste_tool, lookup_rules_tool, find_processors_tool, record_handoff_tool],
        system_prompt=SYSTEM_PROMPT,
        callback_handler=None,
        retry_strategy=get_retry_strategy(),
    )


def run_orchestrator(ctx: RunContext) -> dict:
    """Runs the agent for one stream. Returns {'summary', 'tool_calls', 'ms', 'usage'} or
    {'error', ...}; never raises, so the pipeline can always fall back to deterministic routing.
    """
    start = time.monotonic()
    try:
        agent = build_orchestrator(ctx)
        result = agent("Process this waste stream: characterize it, route every item, and record the handoffs.")
        usage = dict(result.metrics.accumulated_usage) if result.metrics.accumulated_usage else {}
        out = {"summary": str(result).strip(), "tool_calls": ctx.tool_calls, "usage": usage}
    except Exception as exc:  # includes ToolCallCapExceeded and provider errors
        logger.warning(json.dumps({"step": "agent", "stream_id": ctx.stream_id, "error": f"{type(exc).__name__}: {exc}"}))
        out = {"error": f"{type(exc).__name__}: {exc}", "tool_calls": ctx.tool_calls}
    out["ms"] = int((time.monotonic() - start) * 1000)
    logger.info(json.dumps({"step": "agent", "stream_id": ctx.stream_id, **{k: v for k, v in out.items() if k != "summary"}}))
    return out
