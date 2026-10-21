import { useCallback, useEffect, useState } from "react";
import { realSituation } from "@/data/backend";

export type LoadState = "loading" | "ready" | "error";

/**
 * Simulates the first fetch of a live dataset so the loading, empty and error
 * states are real code paths. Replace with a query hook when data is wired in.
 */
export function useMockLoad(delay = 650, fail = false) {
  // with the pipeline's status.json already loaded there is nothing to wait for
  const [state, setState] = useState<LoadState>(realSituation ? "ready" : "loading");
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (realSituation) return;
    setState("loading");
    const t = setTimeout(() => setState(fail ? "error" : "ready"), delay);
    return () => clearTimeout(t);
  }, [delay, fail, nonce]);

  return { state, retry: useCallback(() => setNonce((n) => n + 1), []) };
}