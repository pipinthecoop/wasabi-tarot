# Loopback Mac host and Wasabi tunnel handoff

The app can serve its public card assets and web demo from the same Mac as the bot. Use a stable application checkout and a local persistent state directory. Wasabi owns HTTPS tunnel configuration. Never expose the Python HTTP listener directly to the LAN or internet.

## No-secret asset/demo stage

    BIND_HOST=127.0.0.1 PORT=8765 python3 -m tarot.preview_server

This standard-library service is deliberately read-only: no credentials, database, Slack ingress, or worker. `/health` reports `asset-demo-only`, with those components disabled. `/table`, `/web/*`, `/assets/theme/*` and the public Dawn/Midnight/CRT PNG/GIF directories work. POSTs are rejected. Files outside the public allowlist are never served. There are no request-body or query-string logs.

A user LaunchAgent can restart this process automatically with RunAtLoad, KeepAlive and a restart throttle. Use absolute interpreter/working-directory paths, and private log/state directory permissions. A LaunchAgent requires that user's GUI login after reboot; it is not a boot-time daemon. Sleep/reboot and tunnel availability still affect reachability. Do not change power, login, firewall or FileVault settings without separate authorization.

Wasabi's proposed tunnel origin is `http://127.0.0.1:8765`, at the separately authorized public hostname `tarot.chrypnotoad.com`. Test `/health` before routing. This stage hosts images and a demo only: it cannot receive `/tarot` requests.

## Live activation gate

1. Coordinate with the existing deployment owner before enabling a worker. Identify the authoritative database and stop/quiesce its old worker. Back up using SQLite's backup API; never overwrite an existing destination database. Preserve shoes, request history, outbox and schedules so draws and delivery retries cannot duplicate.
2. Supply the existing Slack bot token, signing secret and team ID through the approved protected runtime environment mechanism. Never put values in source, a public artifact, shell arguments, or LaunchAgent plist. Provisioning is a separate protected operator step. No new scopes or credentials are required by this hosting change.
3. Set `BIND_HOST=127.0.0.1`, `PORT=8765`, an explicit absolute `DATABASE_PATH`, `REGISTRY_PATH` and `THEME_PATH`, and designate one `RUN_WORKER=1` process. `python3 -m tarot.server` is the live entry point. It requires credentials; the preview entry point never becomes live automatically. The existing container default bind remains `0.0.0.0` internally for compatibility, so native hosting must explicitly set loopback.
4. Set `ART_BASE_URL=https://tarot.chrypnotoad.com/assets/decks`, `THEME_ASSET_BASE_URL=https://tarot.chrypnotoad.com/assets/theme`, `PUBLIC_BASE_URL=https://tarot.chrypnotoad.com`, and `ANIMATED_ART=1`. Browser live-table access remains off unless explicitly enabled with its verified Slack-code login flow. Use `ANIMATED_ART=0` for future PNG-only Slack readings.
5. Only after state/credentials are coordinated, replace the preview LaunchAgent command with the live entry point and verify ingress signatures, restart persistence, worker count, scheduled retry behavior and a real Slack reading. Do not consume live cards for a hosting health check.

The public publication bundle contains this generic runbook and tested code only. Machine-specific LaunchAgent files, paths, logs, state and protected runtime configuration belong outside the repository.
