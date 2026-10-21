#!/bin/sh
# Cloudflare quick tunnel to the Insight API (127.0.0.1:8001). No account needed; the
# *.trycloudflare.com URL lasts while this process runs. The current URL is written to
# data/insight_url.txt, which export_frontend puts into status.json for the dashboard.
cd "$(dirname "$0")/.." || exit 1
OUT=data/insight_url.txt
exec ~/.local/bin/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8001 2>&1 | while IFS= read -r line; do
  echo "$line"
  url=$(echo "$line" | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | head -1)
  [ -n "$url" ] && printf '%s\n' "$url" > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"
done
