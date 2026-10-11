import { createContext, useContext, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, getToken, setToken } from "../api.js";

const SessionContext = createContext(null);
export const useSession = () => useContext(SessionContext);

export default function Session({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [principal, setPrincipal] = useState(null);
  const [checking, setChecking] = useState(Boolean(getToken()));
  const [credential, setCredential] = useState("");
  const [error, setError] = useState(null);
  const publicPage = location.pathname.startsWith("/verify");

  useEffect(() => {
    if (!getToken()) return;
    let cancelled = false;
    api.getSession().then((value) => !cancelled && setPrincipal(value))
      .catch((err) => { if (!cancelled) { setToken(""); setError(err.message); } })
      .finally(() => !cancelled && setChecking(false));
    return () => { cancelled = true; };
  }, []);

  async function signIn(event) {
    event.preventDefault();
    setChecking(true); setError(null);
    try {
      const value = await api.getSession(credential.trim());
      setToken(credential.trim());
      localStorage.removeItem("lb:recentStreams");
      setCredential(""); setPrincipal(value);
      navigate("/dashboard");
    } catch (err) { setError(err.message.startsWith("401") ? "That access credential isn't valid. Check it and try again." : err.message); }
    finally { setChecking(false); }
  }

  function signOut() {
    setToken(""); setPrincipal(null);
  }

  const context = { principal, orgs: principal?.orgs || [], signOut };
  if (principal || publicPage) return <SessionContext.Provider value={context}>{children}</SessionContext.Provider>;
  return <div className="max-w-md mx-auto mt-20 p-6 border rounded-lg bg-white">
    <h1 className="text-xl font-semibold">Sign in to LoopBack</h1>
    <p className="text-sm text-gray-600 mt-2">Enter the access credential supplied by your organization administrator.</p>
    <form className="space-y-3 mt-4" onSubmit={signIn}>
      <label className="block text-sm">Access credential
        <input type="password" autoComplete="off" value={credential} onChange={(event) => setCredential(event.target.value)}
          className="block w-full border rounded p-2 mt-1" required />
      </label>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <button disabled={checking} className="bg-gray-900 text-white px-4 py-2 rounded disabled:opacity-50">
        {checking ? "Checking…" : "Sign in"}
      </button>
    </form>
  </div>;
}
