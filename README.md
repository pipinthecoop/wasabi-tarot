# Wasabi Tarot

A Slack tarot bot with finite shared decks, durable draw history, and daily schedules. Deployment owner: **Wasabi**.

Python 3.12+; zero third-party runtime dependencies. HTTP slash-command ingress verifies Slack HMAC signatures and workspace identity, and commits each request plus outgoing reading in a single SQLite transaction before acknowledging. A background worker runs daily schedules and posts normal `chat.postMessage` messages. People can reply in threads and add reactions using Slack itself; the bot does not ingest their replies or reactions.

## Midnight Parlor upgrade

See [THEME-HANDOFF.md](THEME-HANDOFF.md) for native Slack controls, the stone-and-gold web table, optional authenticated access and read-only Work Objects embedding. /tarot now opens a graphical private parlor; all existing text commands and finite deck state remain available.

## Commands

- `/tarot decks` and `/tarot spreads`
- `/tarot draw crt single`
- `/tarot draw crt three`
- `/tarot draw crt "Situation|Obstacle|Next step"`
- `/tarot status crt`
- `/tarot shuffle crt`
- `/tarot schedule 08:00 America/New_York crt single`
- `/tarot schedules`
- `/tarot unschedule SCHEDULE-ID` (creator only)

Deck and spread selection is available through native modals or command arguments. **Phosphor Arcana (`crt`) is the default and the only selectable deck.** The starter decks are hidden with `selectable: false`; their IDs, artwork, saved readings and shoes remain compatible through explicit legacy commands. Hiding a deck never moves or resets cards. `dawn` and `midnight` contain the same 78 standard card identities with different original geometric placeholder art. Meanings are brief prompts, not a full tarot guide. New cards may be added freely to the registry; no fixed 78-card assumption exists in the engine. Cards are upright only.

## State and scheduling guarantees

Each workspace/channel/deck has a shared finite shoe. The first operation creates a cryptographically shuffled shoe. Drawn cards immediately enter discard. A spread is all-or-nothing. Insufficient cards produce an error without consuming any cards; **there is no automatic reshuffle**. `shuffle` returns every card to draw, clears discard and increments the cycle. Any channel user can shuffle the shared shoe; coordinate with other readers.

SQLite `BEGIN IMMEDIATE`, a two-second busy timeout, primary keys, and WAL protect concurrent draw requests and restarts. A slash `trigger_id` is the idempotency key. The same logical request returns the stored result and cannot draw twice. Rejected draw results are also persisted, so an exhaustion retry cannot turn into a new draw after someone shuffles. A scheduled occurrence uses schedule ID plus local calendar date, so concurrent scheduler ticks or the repeated fall DST hour cannot draw twice.

Schedules use IANA time zones. On a spring DST gap they run at the first tick after the missing time. The repeated fall hour runs once. Downtime catches up only today's occurrence after its configured time; previous dates are skipped. Creating a schedule after its time runs today's occurrence immediately. Exhaustion posts one notice for that date. Disable and recreate a schedule to change it. The runtime host must have current time-zone data and synchronized time.

**Slack delivery is not an atomic transaction with SQLite.** Card draws are exactly once per idempotency key; external message delivery cannot promise exactly once. Outbox rows move `pending → sending → sent`. 429 responses safely return to pending after Retry-After. Network timeouts, 5xx and interrupted sending rows are quarantined as `uncertain`/`sending`, not blindly retried. A stable `client_msg_id` is provided but is not relied upon as an exactly-once guarantee. Explicit Slack API failures are `failed`. Wasabi must reconcile these rows against Slack before deciding to retry; never redraw a reading to retry delivery. Keep request/outbox history to preserve deduplication.

## Develop and verify

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/ruff check .
.venv/bin/mypy tarot
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m build
```

Tests cover concurrent independent/duplicate draws, exhaustion, spread rollback, deck/workspace isolation, custom cards, scheduling retries/DST, cancellation, request signatures and ambiguous delivery quarantine. No Slack credentials or network calls are needed for tests.

## Art and custom registry

`registry.json` defines cards, deck membership, art URLs by deck ID, and named spread positions. `art/dawn` and `art/midnight` contain 156 original PNG placeholders plus 156 SVG sources under the repository MIT license. Only original placeholder artwork is included. Wasabi can host the `art` directory over publicly accessible HTTPS and set `ART_BASE_URL=https://YOUR-ASSET-HOST/art` to populate deck-specific PNG URLs automatically. Individual `art.dawn`/`art.midnight` registry URLs override the base URL. `tools/generate_art.py` reproducibly rebuilds the raster geometry using only the standard library. Without URLs, readings are text-only. Do not put secrets or authenticated URLs into the registry. Slack receives PNG URLs; SVGs are editable source references.

To add a deck, create a new `decks` entry with unique card IDs and assign the relevant art URLs on cards. To add a custom card, add its unique ID/name/meaning/art and include its ID in deck membership. Custom positions use quoted `|` separators; maximum ten positions. Supply private art through a separate, git-ignored private registry/art mount only after licensing and Slack-visible hosting are approved. `.dockerignore` excludes private files; do not change the build context to include them.

Card membership changes never reset an active shoe automatically. Status reports the change and draws are rejected while preserving draw/discard/cycle state. An explicit `shuffle` adopts the updated membership and increments the cycle, or use a versioned new deck ID to keep the original shoe. Art/text edits without membership changes do not reset state. Existing completed readings retain their committed content. Registry changes require process restart.

## Wasabi deployment handoff

1. Review this code and the permission reference in `slack-manifest.example.json`. Use an already authorized Slack app or obtain separate approval for any app/permission setup. This handoff does not authorize permission changes.
2. Provide existing `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_TEAM_ID` through the deployment secret manager. Never commit `.env`. The `/tarot` command points at `https://YOUR-HOST/slack/commands`. Bot requires `chat:write` and command access; invite it into each channel. No Events API subscriptions or reaction/history scopes are needed.
3. Run behind a TLS reverse proxy with request size/time limits, no request-body logging, and HTTPS. Route `/health` for a basic process liveness probe. Internal listener is plain HTTP and is not intended for direct public exposure.
4. Build: `docker build -t wasabi-tarot .`. Start a single container with persistent `/data` volume owned by UID 10001 and secrets supplied via environment. It runs ingress and one worker by default. `RUN_WORKER=0` disables that process's worker. **Use one host and a local durable filesystem for SQLite, not NFS or multi-host replicas.** Multiple ingress processes on the same local database are safe; designate one worker. Horizontal multi-host deployment requires replacing SQLite with a transactional server database.
5. Configure/host art if desired, then mount the approved registry at `REGISTRY_PATH`. Empty URLs intentionally produce usable text readings.
6. Smoke-test `/tarot draw`, threaded replies/reactions, explicit shuffle, restart persistence, and an actual local-time daily pull in a test channel. Check Slack app membership and scopes without changing them here.
7. Monitor worker logs, outbox `pending` age, `failed`/`uncertain`/`sending` rows, and disk usage. Outbox does not retry permanent API errors automatically. For a confirmed-undelivered row, set status back to `pending` by ID using an administrative SQLite session; preserve payload and request key. SQLite schema is in `tarot/core.py`.
8. Back up via SQLite backup API (or stop the service before copying all database/WAL files); restrict backups because readings contain user/channel identifiers and prompts. Restore and verify before starting the worker. Retention/deletion is an operator policy; deleting deduplication rows permits old logical requests to draw again.

The wheel packages the Python runtime; deploy with the registry alongside it, or use the Docker build which includes the example registry. Docker build and live Slack integration require Wasabi's deployment environment.

Slack protocol references: [request verification](https://docs.slack.dev/authentication/verifying-requests-from-slack/), [slash commands](https://docs.slack.dev/interactivity/implementing-slash-commands/), [posting normal messages](https://docs.slack.dev/reference/methods/chat.postMessage/).


Phosphor Arcana (`crt`) adds 78 original code-drawn ASCII green CRT scenes, distinct realistic CRT surface GIF loops, static PNG fallbacks, and a matching back. See [CRT-HANDOFF.md](CRT-HANDOFF.md) for public asset hosting, deck selection, regeneration, QA, and the Wasabi deployment checklist.

See [HOSTING-RUNBOOK.md](HOSTING-RUNBOOK.md) for loopback Mac hosting and the separate no-secret asset/demo stage.

## Public deck gallery

Visit `/decks` (also `/decks/crt`) to browse all 78 Phosphor Arcana cards. Search by name/meaning, filter Major Arcana or each suit, and tap a card to enlarge it. Use the arrows or keyboard left/right to explore the filtered selection; tap again, tap outside, or press Escape to dismiss. GIF glow has a static PNG choice and defaults off with reduced motion. Captions stay below the artwork. The gallery fetches public card definitions and assets only: it never opens a live table, fetches private readings, draws, discards, or schedules.

`default_deck` sets the registry default and must identify a selectable deck. New custom decks remain selectable unless marked `selectable: false`. Retired scheduled rituals are independent persisted records: hiding their deck does **not** stop them. Disable and reconcile legacy schedules explicitly before live migration; never transfer an enabled schedule or unresolved pending outbox into a running worker.
