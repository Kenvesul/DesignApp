/**
 * hooks/useSoilLibrary.js
 *
 * Custom React hook: fetches soil library once from /api/soils and caches
 * the result in React state for the lifetime of the component tree.
 *
 * Usage:
 *   const { soils, loading, error } = useSoilLibrary();
 *
 * Returns:
 *   soils   — array of soil objects [{name, gamma, phi_k, c_k, ...}, ...]
 *   loading — true while fetching
 *   error   — error message string or null
 */

import { useState, useEffect } from "react";

let _cache = null; // module-level cache — shared across hook instances

export function useSoilLibrary() {
  const [soils,   setSoils]   = useState(_cache || []);
  const [loading, setLoading] = useState(!_cache);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    if (_cache) return; // already fetched

    let cancelled = false;
    setLoading(true);

    fetch("/api/soils")
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        if (cancelled) return;
        _cache = data;
        setSoils(data);
        setLoading(false);
      })
      .catch(err => {
        if (cancelled) return;
        setError(err.message);
        setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  return { soils, loading, error };
}
