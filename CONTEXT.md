# CONTEXT: handoff for the next agent

FloodLens Pakistan, HackInsight 2026, team Spark H. District heavy-rain risk 1–3 days ahead (Model A), a weekly food-price watch (PBS SPI), and an Insight Agent that answers from NDMA documents with citations. Read `README.md` first for results and links; this file covers how things run and what to watch for.

## Links
- Live Space (static build): https://huggingface.co/spaces/RoshaanT1/floodlens-pakistan
- Demo video: https://roshaant1-floodlens-pakistan.static.hf.space/demo.mp4
- Repo: https://github.com/RoshaanT1/floodlens-pakistan (`main` is the only remote branch)
- Submission form closes **Thu 22 Oct 2026, 12:00 AM PKT**.

## Layout
- `backend/`: Python (venv at `backend/.venv`; the Insight API uses `backend/.venv-insight`)
  - `src/`: ingestion (Open-Meteo, IMERG, SPI, documents), `build.py` (`make data`), quality agent, `model_a.py`, `analysis_a.py`, `insight.py` / `insight_api.py`, `export_frontend.py` (writes `frontend/public/data/status.json`)
  - `flows/hourly.py`: Prefect flow (fetch → rebuild in a scratch DB → atomic swap → export → publish to the Space), cron `5 * * * *`
  - `flows/export_runs.py`: writes `docs/prefect_runs.csv` (done: 15 runs, 14 ok, 1 failed)
  - `data/`: raw/clean/gold, `manifest.csv` (SHA-256 per raw file), `floodlens.duckdb`
  - `models/model_a/current.json` points to the frozen artifact `20261021T0446Z_gbm`
  - `deploy/`: systemd user units and `tunnel.sh` (see `deploy/README.md`)
  - `docs/`: results JSON (`model_a_test.json`, `model_a_validation.json`, `model_a_groups.json`), sources, quality decisions, reports
- `frontend/`: React + Vite (Base44 template). Real data comes from `status.json`; `src/data/backend.ts` maps it onto the template's data shapes (`realSituation` flag).
- Root deliverables: `README.md`, `Summary.pdf` (from `backend/docs/summary.html`), `datasetproposal.pdf`, `HackInsight_Guide_SparkH.pdf` (filled by `backend/tools/fill_guide.py` from `GUIDE_ANSWERS.md`), `AI_Use_Log.md`, `DATASET_DECLARATION.md`, `TASKS.md`.

## Services (on the user's laptop)
`systemctl --user status|restart floodlens-prefect floodlens-flow floodlens-insight floodlens-tunnel`
- `floodlens-prefect`: Prefect server
- `floodlens-flow`: serves the hourly flow (wrapped in `systemd-inhibit` so the laptop doesn't idle-sleep)
- `floodlens-insight`: uvicorn `src.insight_api:app` on :8001 (`GET /api/ask`)
- `floodlens-tunnel`: Cloudflare quick tunnel to :8001. The URL changes on every restart; it's written to `backend/data/insight_url.txt` and exported as `insight_url` in `status.json`, and the Ask page reads it at question time. After a tunnel restart, run an export and a Space publish, or wait for the next hourly run.

## Common commands (from `backend/`)
- `make data`: rebuild everything from the frozen raw snapshot; refuses files whose hash changed
- `make export`: regenerate `frontend/public/data/status.json`
- `make test`: run the tests (they must stay green)
- `.venv/bin/python -m src.model_a train`: train the model and write validation results
- **Do not run** `src.model_a test`. The test set was evaluated once, it's guarded by `FLOODLENS_RUN_TEST=1`, and it refuses a second run.

## Deploying the Space by hand
1. `cd frontend && VITE_STATIC_SPACE=1 npm run build` (HashRouter for static hosting)
2. Copy `public/data/status.json` (and `replay.json`) into `dist/data/`
3. Download the Space's existing `README.md` into `dist/` (it holds the Space config)
4. `HfApi().upload_folder(repo_id="RoshaanT1/floodlens-pakistan", repo_type="space", folder_path="dist", delete_patterns=["assets/*"])`

The hourly flow's `publish_space` task only uploads the data files, so JS/CSS changes need this manual deploy.

## Secrets
`backend/.env` (gitignored, mode 600) holds `EARTHDATA_TOKEN` and `HF_TOKEN`. Never commit them and never put them in the frontend. Both appeared in chat, so the user should rotate them after the event.

## Fixed decisions (do not change)
- Splits: train to 30 Jun 2025, validate 1 Jul–31 Dec 2025, test 1 Jan–30 Sep 2026; UTC days
- Baselines: climatology (declared) and the raw forecast cut at the threshold
- No test data in training, no fabricated data, and every raw file goes in the manifest

## Results (already final)
- Test, Brier at 24 h: 0.0177 [0.0146, 0.0213] vs climatology 0.0192 [0.0156, 0.0231]; paired difference −0.0014 [−0.0022, −0.0008]
- Weakest group: Azad Kashmir. Buner (15 Aug 2025) was missed by the satellite label.
- Model B did not beat "no change" (MAE 1.667 vs 1.665), so the dashboard shows it honestly as a baseline.

## User preferences
- **Ask before any `git push` or Space upload.**
- No `Co-Authored-By: Claude` trailers in commits or PRs.
- Keep the Base44 styling; map real data onto the existing components rather than redesigning them.
- No mock or fake numbers shown as real; label limits honestly. Light mode is the default.
- Don't tag `v1.0-final` until the user says so.

## Gotchas
- Prefect 3.8.8 needs `fastapi==0.153.0` and `sqlalchemy<2.1`.
- `npm run lint` misses undefined names, so also run `npx tsc --noEmit -p jsconfig.json`.
- CARTO tiles now require a key; use the Esri light-gray tiles.
- `gpm1.gesdisc` blocks this IP; IMERG comes through Earthdata Cloud OPeNDAP.
- Open-Meteo budget: 9,000 calls per UTC day, counted from the manifest.
- `save_raw` never overwrites a raw file (a refetch once clobbered 21 files).
- Don't `pkill -f` with a pattern that matches your own shell; use `pgrep` with a `[b]racket` pattern.

## Git state
- `main` was history-rewritten twice (trailer removal, then a squash). Teammates need `git fetch origin && git reset --hard origin/main`.
- Local backup branches: `backup/main-before-rewrite`, `backup/main-before-squash`, `backup/overnight-before-rewrite`, `backup/pre-merge-local`.
- Untracked and deliberately not committed: `hackathonguide (1).pdf` and `HackInsight2026_Template.pptx`.

## Open items
- Tag `v1.0-final` when the user asks.
- Optional: a narrated version of the video.
- The user should rotate the Earthdata and HF tokens after the event.
