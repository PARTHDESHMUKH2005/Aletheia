import { test } from "node:test";
import assert from "node:assert/strict";
import { HANDOFF_ORDER, handoffStatus, canAdvanceHandoff } from "../src/lib/handoff.js";

const event = (status, payload = {}) => ({ event: `handoff_${status}`, payload_json: JSON.stringify(payload) });

test("each item's handoff state ignores unrelated and ambiguous legacy entries", () => {
  const ledger = [event("verified", { item_index: 0 }), event("matched", { item_index: 1 }), event("verified")];
  assert.equal(handoffStatus(ledger, 0, 2), "verified");
  assert.equal(handoffStatus(ledger, 1, 2), "matched");
  assert.equal(handoffStatus([event("weighed")], 0, 1), "weighed");
});

test("verified is terminal and completed or backward steps cannot be selected", () => {
  for (const status of HANDOFF_ORDER) assert.equal(canAdvanceHandoff("verified", status), false);
  assert.equal(canAdvanceHandoff("weighed", "matched"), false);
  assert.equal(canAdvanceHandoff("weighed", "weighed"), false);
  assert.equal(canAdvanceHandoff("weighed", "verified"), true);
  assert.equal(canAdvanceHandoff(null, "matched"), true);
  assert.equal(canAdvanceHandoff(null, "invalid"), false);
});

test("old backward events and malformed payloads do not reopen completed handoffs", () => {
  assert.equal(handoffStatus([event("verified"), event("matched"), { event: "handoff_weighed", payload_json: "bad json" }]), "verified");
});
