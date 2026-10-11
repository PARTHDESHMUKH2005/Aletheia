import { useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";
import { useSession } from "../components/Session.jsx";

export default function Verify() {
  const { principal } = useSession();
  const { chainId: chainIdFromUrl } = useParams();
  const [chainId, setChainId] = useState(chainIdFromUrl || "");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function doVerify() {
    if (!chainId) return;
    setError(null);
    try {
      setResult(await api.verifyChain(chainId));
    } catch (err) {
      setError(err.message);
    }
  }

  async function doTamper() {
    if (!chainId) return;
    try {
      await api.devTamper(chainId, 1);
      await doVerify();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="max-w-md">
      <h1 className="text-lg font-semibold mb-1">Verify ledger</h1>
      <p className="text-sm text-gray-500 mb-4">
        Public page. Recomputes the hash chain for a stream and reports the first broken link, if any.
      </p>

      <div className="flex gap-2 mb-3">
        <input
          type="text"
          placeholder="paste a stream_id (= chain_id)"
          className="flex-1 border rounded-md px-3 py-2 text-sm"
          value={chainId}
          onChange={(e) => setChainId(e.target.value)}
        />
        <button onClick={doVerify} className="bg-gray-900 text-white text-sm px-4 py-2 rounded-md">
          Verify
        </button>
      </div>

      {principal?.role === "admin" && <button onClick={doTamper} className="text-xs underline text-gray-500 mb-4">
        Tamper link 1 (demo tool -- disabled when ENV=production)
      </button>}

      {error && <div className="text-sm text-red-600">{error}</div>}

      {result && (
        <div className={`border rounded-lg p-4 ${result.ok ? "bg-green-50 border-green-400" : "bg-red-50 border-red-400"}`}>
          {result.ok ? (
            <div className="text-green-700 font-semibold">OK -- {result.links} link(s), chain intact.</div>
          ) : (
            <div className="text-red-700 font-semibold">
              {result.links === 0 ? "No ledger entries recorded." : `Unverified at link ${result.first_broken} of ${result.links} (damaged or legacy format).`}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
