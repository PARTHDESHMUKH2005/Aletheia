import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { rememberStream } from "../lib/recent.js";
import { api, resizeImageToJpeg } from "../api.js";
import { useSession } from "../components/Session.jsx";

export default function Upload() {
  const navigate = useNavigate();
  const { orgs: ORGS } = useSession();
  const [orgId, setOrgId] = useState(ORGS[0].id);
  const [file, setFile] = useState(null);
  const [note, setNote] = useState("");
  const [quantity, setQuantity] = useState("");
  const [pincode, setPincode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const submittingRef = useRef(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (submittingRef.current) return;
    if (!file) {
      setError("Pick a photo first.");
      return;
    }
    submittingRef.current = true;
    setBusy(true);
    setError(null);
    try {
      const resized = await resizeImageToJpeg(file);
      const [target] = await api.createUploadTargets(1, orgId, [resized.size]);
      await api.putUpload(target.url, resized);

      const { stream_id } = await api.createStream({
        org_id: orgId,
        note,
        quantity_kg: quantity ? parseFloat(quantity) : null,
        photo_keys: [target.key],
        pincode: pincode || null,
      });
      rememberStream(stream_id);
      navigate(`/streams/${stream_id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      submittingRef.current = false;
      setBusy(false);
    }
  }

  return (
    <div className="max-w-md">
      <h1 className="text-lg font-semibold mb-1">Submit a waste stream</h1>
      <p className="text-sm text-gray-500 mb-4">Photo, note, quantity, and a pickup pincode.</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs text-gray-600 mb-1">Organization</label>
          <select
            className="w-full border rounded-md px-3 py-2 text-sm"
            value={orgId}
            onChange={(e) => setOrgId(e.target.value)}
          >
            {ORGS.map((o) => (
              <option key={o.id} value={o.id}>{o.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-gray-600 mb-1">Photo</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="w-full text-sm"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-600 mb-1">Note</label>
          <textarea
            className="w-full border rounded-md px-3 py-2 text-sm"
            rows={2}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="optional note about the item"
          />
        </div>

        <div className="flex gap-3">
          <div className="flex-1">
            <label className="block text-xs text-gray-600 mb-1">Quantity (kg, optional)</label>
            <input
              type="number"
              min="0.1"
              step="0.1"
              className="w-full border rounded-md px-3 py-2 text-sm"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs text-gray-600 mb-1">Pincode</label>
            <input
              type="text"
              placeholder="e.g. 147001"
              className="w-full border rounded-md px-3 py-2 text-sm"
              value={pincode}
              onChange={(e) => setPincode(e.target.value)}
            />
          </div>
        </div>

        {error && <div className="text-sm text-red-600">{error}</div>}

        <button
          type="submit"
          disabled={busy}
          className="bg-gray-900 text-white text-sm px-4 py-2 rounded-md disabled:opacity-40"
        >
          {busy ? "Submitting..." : "Submit stream"}
        </button>
      </form>
    </div>
  );
}
