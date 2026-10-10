# Phosphor Arcana — Wasabi handoff

An original, programmatically illustrated and animated 78-card ASCII green CRT tarot deck, selectable as **Phosphor Arcana** (`crt`). Every card has a distinct authored scene: 22 major arcana, 40 ace–ten scenes, and 16 suit-specific courts. The modeled tonal compositions are translated into dense ASCII character cells with phosphor bloom, scanlines, vignette and curved screen geometry. Editable SVG masters, 600×900 static PNGs and 320×480 looping GIFs are public MIT artwork. No private deck artwork, external illustrations, generated-image service, credentials, or licensed fonts are included.

## Integrate and deploy

Wasabi owns deployment. Apply this change over `f820935bb22531c6bea048c0deec31af60bdbff2` in `pipinthecoop/wasabi-tarot`. The changed-file ZIP includes a manifest with base-file and new-file SHA-256 hashes. Compare base hashes before applying; preserve any newer upstream changes. No database migration, reset, OAuth change, or Slack account setup is required for this deck.

1. Publish all 78 `art/crt/{canonical-id}.gif` animations, all 78 PNG fallbacks, plus `art/crt/back.png` to the public card-art host. Existing Dawn and Midnight artwork must remain available.
2. Set `ART_BASE_URL=https://YOUR_PUBLIC_HOST/assets/decks` if using this service's public static routes. Animated card fronts resolve as `${ART_BASE_URL}/crt/major-0.gif`, etc.; PNGs use the same path with `.png`. `ANIMATED_ART=1` is the default. Set `ANIMATED_ART=0` to use PNGs in future Slack readings if animation is disabled or unsupported by the target Slack client. Existing cached reading payloads remain immutable. This base is independent of the theme asset base. Without a public HTTPS art base, Slack can show the reading text but cannot fetch these card fronts.
3. Publish `art/theme/crt-back.png` and `crt-back.webp` alongside the existing theme bundle. Set `THEME_ASSET_BASE_URL=https://YOUR_PUBLIC_HOST/assets/theme`. The new deck override changes only the CRT back; the existing parlor theme remains intact.
4. Use the existing deployment procedure in README and THEME-HANDOFF. Keep the existing persistent SQLite volume and registry configuration. Restart the service with the new registry/art. Do not run artwork generators against a private-art checkout or replace the database.
5. In Slack, choose Phosphor Arcana in the art-deck selector, or use `/tarot draw crt three`. A custom spread works as `/tarot draw crt "Question|What helps|Next step"`. Daily pulls use `/tarot schedule 08:00 America/New_York crt single` (replace with the reader's IANA zone). Use `/tarot status crt` and `/tarot shuffle crt` explicitly.

The new shoe initializes on first use and is independent of Dawn/Midnight. Existing canonical card IDs, meanings, memberships, assets, and defaults are unchanged. Draws share the channel's finite shoe, retries return the original reading, exhaustion requires an explicit shuffle, and scheduled occurrences retain the existing time-zone-aware idempotency. Normal reading messages continue to support threads and reactions. Adding the new deck does not shuffle any existing shoe.

The browser `/table` and offline preview now populate deck choices from the demo registry. The service deliberately serves PNG/GIF files only from the three public deck directories; an arbitrary custom/private art folder is not exposed. Custom private deck hosting remains a separate licensed integration.

## Reproduce and verify

Install the pinned `dev,qa` extras, and install Chromium with Playwright or provide `--executable` / `CHROMIUM_PATH` for an existing browser. Runtime still uses only the Python standard library; image/QA tools are developer extras.

    python tools/generate_crt.py
    python tools/render_crt.py
    python tools/animate_crt.py
    python tools/export_preview.py preview/phosphor-arcana-demo.html
    python tools/gif_gallery.py
    python tools/qa_crt.py
    ruff check .
    mypy tarot
    python -m unittest discover -s tests -v
    python -m build --no-isolation

Scene SVGs are deterministic from the source; raster font rendering can vary across operating systems. The committed PNGs and GIFs are the delivery masters. Menlo/monospace and Georgia/serif are system font requests; no font files are bundled. The catalogue records each distinct illustration's hash independently of the shared glass frame. QA validates all 79 PNGs and decodes every frame of all 78 GIFs; checks dimensions, per-card frame counts, endless loops, immutable title regions, distinct frame hashes, unique refresh/glow/phase, and the under-2-MB file budget; captures desktop, 390px and 320px browser views; checks the CRT selector/back/fronts, animated/static toggle, reduced-motion defaults, failed-GIF PNG fallback, offline preview, finite draw counter, and a committed Slack Block Kit payload using an isolated temporary database. Slack screenshots are an approximation, not evidence of a live Slack deployment. Meaning text remains the established reflective placeholder copy.

Each GIF has 22–24 frames at 320×480, a 48-color palette, and a unique refresh phase, scan speed, gentle luminance harmonics and meaningful local bloom region. The artwork stays exactly fixed: no wobble, deformation, moving figures, or falling props. Approved realistic CRT light/refresh animation includes rolling scanlines, a broad refresh band, soft bloom and persistence. All GIFs stay below 2 MB; no harsh full-screen strobe is used. Motion recipes and file hashes are in `art/crt/animations.json`; scenes are in `tools/crt_ascii_deck.py` and the three approved studies in `tools/crt_ascii_studies.py`; approved GIF light effects are in `tools/crt_surface_samples.py` and `tools/animate_crt_surface.py`. The browser remembers the current reading while switching motion without consuming cards, starts static when reduced motion is requested, and uses PNG automatically on a GIF load error. Slack [image blocks officially support GIF](https://docs.slack.dev/reference/block-kit/blocks/image-block/). Playback behavior depends on the client, so Wasabi must check a real posted GIF; the server-wide PNG configuration remains available.

The full offline HTML includes all decks and GIF/PNG assets and is large because it embeds all animated and static assets. Use the compact twelve-card motion gallery for quick visual review; the hosted app loads only the chosen reading’s assets.

Contact sheets: `preview/crt-all-78.png`, `crt-major-arcana.png`, and one sheet per suit. These are review artifacts, excluded from the runtime build. `tools/package_crt.py` creates the public changed-file handoff without caches, local databases, `.env`, private art, or previews.

Native Mac hosting is described in [HOSTING-RUNBOOK.md](HOSTING-RUNBOOK.md). The no-secret preview entry point binds loopback only and has no Slack ingress, DB or worker; it is distinct from live activation.
