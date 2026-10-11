# Removing the Aletheia landing and About pages

Everything new lives in `frontend/src/marketing/`. Four existing files were edited (all one-line changes).
The working app was moved from `/` to `/app`; reverting puts it back at `/`.

## One step (from the repo root)

Only safe if these four files have no other uncommitted changes since the marketing work:

```bash
rm -rf frontend/src/marketing && git checkout 37fba2e -- frontend/src/main.jsx frontend/src/App.jsx frontend/src/components/AppLayout.jsx frontend/src/pages/Passport.jsx
```

`37fba2e` is the commit the marketing pages were built on (its frontend files are identical to `743d1b2`). If those files have changed since, use the manual steps instead.

## Manual steps (exact lines)

1. Delete the folder `frontend/src/marketing/`.

2. `frontend/src/main.jsx`
   - Line 3: `import { BrowserRouter, Route, Routes } from "react-router-dom";`
     back to `import { BrowserRouter } from "react-router-dom";`
   - Delete lines 6 and 7 (the two `React.lazy(... "./marketing/index.js" ...)` lines).
   - Line 12: `<React.Suspense fallback={null}><Routes>...<Route path="*" element={<App />} /></Routes></React.Suspense>`
     back to `<App />`

3. `frontend/src/App.jsx`
   - Line 17: `<Route path="/app" element={<Upload />} />` back to `<Route path="/" element={<Upload />} />`

4. `frontend/src/components/AppLayout.jsx`
   - Line 9: `to: "/app"` back to `to: "/"` (the "Upload Waste" item).
   - Line 18: remove `app: "Upload Waste", ` from the start of the `names` object.
   - Line 77: delete `<Link to="/about" className="lb-button lb-button-secondary">About</Link>`

5. `frontend/src/pages/Passport.jsx`
   - Lines 101 and 109: `to="/app"` back to `to="/"` (the "Upload a photo" and "Upload waste" links).

## Check

```bash
cd frontend && npm run build && npm test && git status --short
```

`git status` should show nothing under `frontend/src/`.
