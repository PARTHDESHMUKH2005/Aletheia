import { useEffect } from "react";
import { useLocation } from "react-router-dom";

// Sets the tab title while a marketing page is open (restores the app's title on leave)
// and lands at the top, or at the #section in the URL.
export function usePageSetup(title) {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    const previous = document.title;
    document.title = title;
    return () => { document.title = previous; };
  }, [title]);
  useEffect(() => {
    if (hash) {
      const el = document.getElementById(hash.slice(1));
      if (el) { el.scrollIntoView(); return; }
    }
    window.scrollTo(0, 0);
  }, [pathname, hash]);
}
