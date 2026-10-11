export const API_URL = import.meta.env?.VITE_API_URL || "http://127.0.0.1:8000";

export const getToken = () => sessionStorage.getItem("loopback-token") || "";
export const setToken = (token) => token ? sessionStorage.setItem("loopback-token", token) : sessionStorage.removeItem("loopback-token");

async function request(path, options = {}, asBlob = false) {
  const headers = new Headers(options.headers);
  if (!headers.has("Authorization") && getToken()) headers.set("Authorization", `Bearer ${getToken()}`);
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail || body);
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  if (res.status === 204) return null;
  if (asBlob) return res.blob();
  return res.json();
}

// BUILD.md section 2 / 9: resize each photo to at most 1280px on the long edge
// (JPEG) client-side before upload, to keep image tokens and latency down.
export function resizeImageToJpeg(file, maxEdge = 1280, quality = 0.85) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const reader = new FileReader();
    reader.onerror = reject;
    reader.onload = () => {
      img.onerror = reject;
      img.onload = () => {
        const scale = Math.min(1, maxEdge / Math.max(img.width, img.height));
        const w = Math.round(img.width * scale);
        const h = Math.round(img.height * scale);
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, w, h);
        canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("Could not resize image")), "image/jpeg", quality);
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

export const api = {
  getSession: (token = getToken()) => request("/session", { headers: { Authorization: `Bearer ${token}` } }),

  createUploadTargets: (count, orgId, sizes) =>
    request("/uploads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count, org_id: orgId, sizes }),
    }),

  putUpload: async (url, blob) => {
    if (!/^https?:\/\//.test(url)) return request(url, { method: "PUT", body: blob });
    // Presigned S3 uploads have their own authorization; never send the API credential.
    const response = await fetch(url, { method: "PUT", headers: { "Content-Type": "image/jpeg", "If-None-Match": "*" }, body: blob });
    if (!response.ok) throw new Error(`Upload failed (${response.status})`);
    return null;
  },

  getPhoto: (key) => request(`/local-uploads/${key}`, {}, true),

  createStream: (body) =>
    request("/streams", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  getStream: (streamId) => request(`/streams/${streamId}`),

  getRoute: (streamId, w, itemIndex = 0, evidenceWeight = 0) =>
    request(`/streams/${streamId}/route?w=${w}&item_index=${itemIndex}&evidence_weight=${evidenceWeight}`),

  saveRoute: (streamId, w, itemIndex = 0, evidenceWeight = 0) => request(`/streams/${streamId}/route`, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ w, item_index: itemIndex, evidence_weight: evidenceWeight }),
  }),

  getReviewQueue: () => request("/review-queue"),

  submitReview: (streamId, body) =>
    request(`/streams/${streamId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  advanceHandoff: (streamId, body) =>
    request(`/streams/${streamId}/handoff`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  registerEwaste: (streamId, devices) =>
    request(`/streams/${streamId}/ewaste`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ devices }),
    }),

  getEwaste: (streamId) => request(`/streams/${streamId}/ewaste`),

  wipeDrive: (streamId, driveId, body) =>
    request(`/streams/${streamId}/ewaste/drives/${driveId}/wipe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  confirmWipe: (streamId, body) => request(`/streams/${streamId}/wipe`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  }),

  draftPickupMessage: (streamId, processorId, itemIndex = 0) =>
    request(`/streams/${streamId}/draft-message?processor_id=${processorId}&item_index=${itemIndex}`, {
      method: "POST",
    }),

  getReport: (streamId) => request(`/streams/${streamId}/report`, {}, true),

  getDashboard: (orgId) => request(`/orgs/${orgId}/dashboard`),

  listProcessors: () => request("/processors"),

  verifyChain: (chainId) => request(`/verify/${chainId}`),

  devTamper: (chainId, linkNo = 1) => request(`/dev/tamper/${chainId}?link_no=${linkNo}`, { method: "POST" }),
};
