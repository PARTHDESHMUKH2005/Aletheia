export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  if (res.status === 204) return null;
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
        canvas.toBlob((blob) => resolve(blob), "image/jpeg", quality);
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

export const api = {
  createUploadTargets: (count) =>
    request("/uploads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count }),
    }),

  putUpload: (url, blob) => fetch(`${API_URL}${url}`, { method: "PUT", body: blob }),

  createStream: (body) =>
    request("/streams", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  getStream: (streamId) => request(`/streams/${streamId}`),

  getRoute: (streamId, w, itemIndex = 0, evidenceWeight = 0) =>
    request(`/streams/${streamId}/route?w=${w}&item_index=${itemIndex}&evidence_weight=${evidenceWeight}`),

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

  confirmWipe: (streamId) => request(`/streams/${streamId}/wipe`, { method: "POST" }),

  draftPickupMessage: (streamId, processorId, itemIndex = 0) =>
    request(`/streams/${streamId}/draft-message?processor_id=${processorId}&item_index=${itemIndex}`, {
      method: "POST",
    }),

  getReport: (streamId) => request(`/streams/${streamId}/report`),

  getDashboard: (orgId) => request(`/orgs/${orgId}/dashboard`),

  listProcessors: () => request("/processors"),

  verifyChain: (chainId) => request(`/verify/${chainId}`),

  devTamper: (chainId, linkNo = 1) => request(`/dev/tamper/${chainId}?link_no=${linkNo}`, { method: "POST" }),
};
