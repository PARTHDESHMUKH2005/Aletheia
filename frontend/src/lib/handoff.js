export const HANDOFF_ORDER = ["requested", "matched", "collected", "weighed", "verified"];

export function handoffStatus(ledger = [], itemIndex = 0, itemCount = 1) {
  let reached = -1;
  for (const entry of ledger) {
    if (!entry.event?.startsWith("handoff_")) continue;
    try {
      const payload = JSON.parse(entry.payload_json);
      const index = payload.item_index ?? (itemCount === 1 ? 0 : null);
      if (index !== itemIndex) continue;
      reached = Math.max(reached, HANDOFF_ORDER.indexOf(entry.event.slice("handoff_".length)));
    } catch {
      // A malformed ledger payload cannot supply a handoff state.
    }
  }
  return HANDOFF_ORDER[reached] ?? null;
}

export function canAdvanceHandoff(current, target) {
  return HANDOFF_ORDER.includes(target) && HANDOFF_ORDER.indexOf(target) > HANDOFF_ORDER.indexOf(current);
}
