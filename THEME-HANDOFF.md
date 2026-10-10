# The Midnight Parlor · Wasabi handoff

This upgrade keeps the existing finite shared decks and adds a midnight-blue, antique-gold tarot parlor with original celestial artwork. The tactile web table has sculpted stone buttons, gold bevels, hover lighting, physical pressed depth, velvet and ornamental borders. Normal Slack controls use supported native Block Kit; they are not reskinned HTML buttons.

## What is built

- /tarot or /tarot parlor: private native parlor with Draw a reading, Shuffle deck and Daily ritual buttons.
- Native modals: deck/spread dropdowns, custom spread positions, explicit full-deck shuffle confirmation and daily time/IANA zone controls.
- Readings: dramatic ritual illustration, card art when configured, full accessible text, remaining-card counts, normal threads/reactions.
- Optional card/carousel message layout (theme.json reading_layout: carousel). Classic image/section layout is the default. Cards/carousels are used only in messages; Home/modals stay on established standard blocks. Wasabi must verify workspace support before selecting carousel mode.
- /tarot home: useful personal App Home with owned schedules and End daily ritual buttons when already configured and ENABLE_APP_HOME=1; otherwise returns usable private channel controls.
- /table: responsive illustrated tarot table with accessible labels, keyboard focus, 44px+ targets, reduced motion, explicit shuffle confirmation and finite local demo shoes. Demo activity is isolated in browser memory and never touches Slack.
- Optional live browser table: /tarot table issues a five-minute, single-use private code through the existing signed Slack command. The user enters it manually on /table. A secure HttpOnly one-hour browser session binds all operations to that Slack user/team/channel. Draw/shuffle/schedule use the same transactional engine, outbox and finite shoe as Slack.
- Optional Work Objects adapter: pro-active reading entities and a read-only /embed/table preview in the Slack side panel. The preview contains only public demo artwork, no private reading data and no state-changing controls. The full browser table is the interactive alternative.

## Enable without changing credentials or scopes here

Nothing has been deployed or configured in Slack. All optional surfaces are off by default.

1. Replace the deployed source, preserving /data/tarot.sqlite3. Initialization adds tables for owner-bound rituals and short-lived browser codes/sessions; it never resets existing shoes.
2. Route signed interactions to https://YOUR-HOST/slack/interactions in the app's existing Interactivity configuration. No new OAuth scopes are introduced; existing commands and chat:write remain the reference. If setup changes need approval in Wasabi's environment, obtain it there.
3. Native illustrations: serve art/theme over public HTTPS; set THEME_ASSET_BASE_URL=https://YOUR-HOST/assets/theme if hosting with this service. Serve /table, /web/*, /assets/theme/* and /assets/decks/* via the service. Existing ART_BASE_URL independently controls actual deck/card images. Blank theme URL gives text/native controls without broken image blocks.
4. Configure theme.json or THEME_PATH. Global assets and deck_assets overrides allow different art decks to share the parlor or have distinct headers/card backs/spread illustrations. The 156 original card PNGs and 156 SVG sources are untouched. Optimized PNG/WebP theme artwork is included here.
5. App Home is opt-in: only set ENABLE_APP_HOME=1 when the existing app already has a Home tab enabled. /tarot home publishes on demand; it needs no new event subscription. No settings or permissions were changed by this implementation. Every ingress process needs the existing bot token for immediate modal opening, including RUN_WORKER=0 processes.
6. Live web table is opt-in: set ENABLE_WEB_TABLE=1 and an HTTPS origin PUBLIC_BASE_URL=https://YOUR-HOST. Use a TLS reverse proxy that preserves Origin/Cookie headers. __Host-tarot cookies require HTTPS, Secure, HttpOnly, SameSite=Strict, Path=/ and no Domain. Every mutation requires exact same Origin and a per-session CSRF token; unauthenticated, cross-origin and Origin:null mutations are rejected. One-time codes/session IDs are never in URLs, static assets or browser source. Do not log request bodies or cookies. No Slack/GitHub OAuth login, account or service credentials were added. Runtime one-time codes and browser sessions are generated only when the optional live feature is enabled.
7. Native button/modal sessions expire after one hour. A reader cannot use someone else's controls. Each submit is single-use across different click timestamps and retries. A draw or shuffle opened before another operation changes the chosen shoe is stale and consumes nothing; reopen /tarot. Cancel consumes nothing. Schedule retries produce one schedule, and daily occurrence retries still produce one draw.
8. Run the updated tests and smoke-test actual Slack surfaces. View opening uses Slack's short-lived trigger immediately, with a bounded request timeout; failed/ambiguous opening consumes no cards and requires fresh /tarot controls. Home publishing uses the existing outbox. Monitor failures as described in README.md.

## Optional Work Objects embedding

The adapter is implemented, **not enabled or tested in live Slack**. It requires Wasabi to review the app's existing authorized configuration before making changes.

- Enable rich previews for slack#/entities/item and subscribe to entity_details_requested at /slack/events, using the additive fragment in slack-work-objects.optional.json. Do not blindly replace the existing manifest.
- Set ENABLE_WORK_OBJECTS=1 and HTTPS PUBLIC_BASE_URL. Reading notifications carry a stable hashed reading ID in metadata.entities; IDs are public object identity, not credentials. No pasted-link unfurl workflow, links:* scopes, or additional OAuth scopes are requested.
- Configure the embed-domain allowlist in Slack's Work Objects/rich previews app settings. This is an app-settings requirement; there is no invented manifest field for the domain allowlist.
- /embed/table serves public content with frame-ancestors https://*.slack.com https://*.slack-gov.com https://*.slack-mcps.com. The last origin is needed for mobile. Public assets permit CORS; authenticated API endpoints do not.
- Slack's default embed has Origin:null and no cookie access or iframe-to-Slack bridge. The implemented embed is deliberately read-only; normal-browser live interaction requires the verified code/session flow. The event adapter presents a generic parlor preview, not the private reading. If Wasabi later wants private embedded reading content, it needs a separately reviewed authentication design.
- API event retries are deduplicated; expired/ambiguous presentation triggers are not blindly retried. A new click can request a fresh view.

References: [Block Kit](https://docs.slack.dev/block-kit/), [card blocks](https://docs.slack.dev/reference/block-kit/blocks/card-block/), [carousels](https://docs.slack.dev/reference/block-kit/blocks/carousel-block/), [App Home](https://docs.slack.dev/surfaces/app-home/), [Work Objects embeds](https://docs.slack.dev/messaging/work-objects-embeds/), [implementation](https://docs.slack.dev/messaging/work-objects-implementation/).

## Verification and visual preview

The full unittest suite, ruff and mypy include the original persistence checks plus interaction/session tests. tools/qa_theme.py uses an optional local Playwright installation to capture desktop 1440px, mobile 390px and narrow 320px layouts, reveal/custom spreads, cancellation, explicit shuffle, reduced motion and unauthorized API rejection. It also renders **approximations** of native Slack parlor/modal payloads at 390px; actual Slack rendering remains Wasabi's smoke test. The public embedded preview is checked read-only.

Install with pip install -e '.[dev,qa]', then python -m playwright install chromium if a compatible local browser is unavailable. Run python tools/qa_theme.py. CHROMIUM_PATH optionally points at an existing Chromium executable. Browser QA runs a loopback-only server and a temporary database.

The downloadable standalone HTML preview is a self-contained demo, not the authenticated production service. It uses the same web layout/artwork and finite demo draws; live login is disabled. Screenshots and the standalone preview are separate review artifacts.

