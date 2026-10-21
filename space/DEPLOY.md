# Deploying the FloodLens Space (task P2)

This folder only adds files. It changes nothing in backend/ or frontend/.

## One-time, by the team lead (Hugging Face account owner)
1. Create a Hugging Face account, then create a new Space:
   SDK = Docker, template = Blank, visibility = Public, name = floodlens-pakistan.
2. Create a write access token: Settings > Access Tokens > New token > Write.

## Every time we publish (by whoever has the repo)
1. From the repo root run:  space\prepare.bat
   It builds the dashboard and makes the folder D:\floodlens-space-out (outside the repo).
2. In that folder:
   git init -b main
   git add .
   git commit -m "FloodLens Space"
   git remote add space https://huggingface.co/spaces/HF_USERNAME/floodlens-pakistan
   git push --force space main
   When asked, the username is the Hugging Face username and the password is the write token.
3. Wait for the Space to show "Running", then open its URL in a private window to confirm
   it opens without a login.

## What the Space shows
A snapshot of public/data/status.json from the moment of the build. To refresh it after a
newer hourly run, run `make export` on the pipeline machine, then repeat the steps above.
The Ask page shows "not running" on the Space because the Insight Agent runs locally.
