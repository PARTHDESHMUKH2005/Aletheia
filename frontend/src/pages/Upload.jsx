import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { rememberStream } from "../lib/recent.js";
import { api, resizeImageToJpeg } from "../api.js";
import { useSession } from "../components/Session.jsx";

export default function Upload() {
  const navigate = useNavigate();
  const { orgs: ORGS } = useSession();
  const [orgId, setOrgId] = useState(ORGS[0].id);
  const [files, setFiles] = useState([]);
  const [note, setNote] = useState("");
  const [quantity, setQuantity] = useState("");
  const [pincode, setPincode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const submittingRef = useRef(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (submittingRef.current) return;
    if (!files.length) {
      setError("Pick at least one photo.");
      return;
    }
    if (files.length > 4) {
      setError("Choose no more than four photos.");
      return;
    }
    submittingRef.current = true;
    setBusy(true);
    setError(null);
    try {
      const resizedPhotos = await Promise.all(files.map((file) => resizeImageToJpeg(file)));
      const targets = await api.createUploadTargets(
        resizedPhotos.length,
        orgId,
        resizedPhotos.map((photo) => photo.size),
      );
      await Promise.all(targets.map((target, index) => api.putUpload(target.url, resizedPhotos[index])));

      const { stream_id } = await api.createStream({
        org_id: orgId,
        note,
        quantity_kg: quantity ? parseFloat(quantity) : null,
        photo_keys: targets.map((target) => target.key),
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
          <label className="block text-xs text-gray-600 mb-1">Photos (up to 4)</label>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
            className="w-full text-sm"
          />
          <p className="mt-1 text-xs text-gray-500">
            {files.length ? `${files.length} photo${files.length === 1 ? "" : "s"} selected` : "Select one to four photos."}
          </p>
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
