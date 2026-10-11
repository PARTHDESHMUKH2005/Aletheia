// Remembers the streams this browser has uploaded so the Passport page can open the latest one.
const KEY = "lb:recentStreams";

export function recentStreams() {
  try {
    const list = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

export function rememberStream(id) {
  try {
    localStorage.setItem(KEY, JSON.stringify([id, ...recentStreams().filter((x) => x !== id)].slice(0, 20)));
  } catch {
    /* storage unavailable: the passport falls back to its sample view */
  }
}
