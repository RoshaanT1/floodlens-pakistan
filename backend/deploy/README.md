# Running the hourly flow as a service (Linux, systemd user units)

```bash
cd backend
mkdir -p ~/.config/systemd/user
ln -sf "$PWD/deploy/systemd/floodlens-prefect.service" "$PWD/deploy/systemd/floodlens-flow.service" ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now floodlens-prefect floodlens-flow
loginctl enable-linger "$USER"     # optional: keep running when logged out / after reboot without login
```

- Status: `systemctl --user status floodlens-flow`, logs: `journalctl --user -u floodlens-flow -f`
- Stop: `systemctl --user stop floodlens-flow floodlens-prefect` (also releases the sleep inhibitor)
- Both restart on failure. While `floodlens-flow` runs, idle suspend is blocked (`systemd-inhibit --list`
  shows "FloodLens"); closing the lid still suspends.
- The unit files contain absolute paths to this checkout; edit `WorkingDirectory`/`ExecStart`
  if the repo lives elsewhere.
