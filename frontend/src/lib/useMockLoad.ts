import { useCallback, useEffect, useState } from "react";

export type LoadState = "loading" | "ready" | "error";

/**
 * Simulates the first fetch of a live dataset so the loading, empty and error
 * states are real code paths. Replace with a query hook when data is wired in.
 */
export function useMockLoad(delay = 650, fail = false) {
  const [state, setState] = useState<LoadState>("loading");
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    setState("loading");
    const t = setTimeout(() => setState(fail ? "error" : "ready"), delay);
    return () => clearTimeout(t);
  }, [delay, fail, nonce]);

  return { state, retry: useCallback(() => setNonce((n) => n + 1), []) };
}