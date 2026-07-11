# Plan: `track sync` — Deployable Remote Dashboard

Status: **Proposed** — pending approval.
Last updated: 2026-07-12

## 0. Context & Decisions (locked)

- **Goal:** View "how my days went" from *anywhere* — a personal, glanceable day-in-review, not a data-export tool.
- **Architecture:** Generate a **self-contained static HTML file** and **deploy it to a static host** (no live server, no backend). The HTML is a *derived, disposable artifact* regenerated from local JSON; it is never the source of truth.
- **Host:** **Vercel** is the primary backend. Reason: the user's domain is already managed by Vercel, so attaching a custom domain (`track.yourdomain.com`) is a one-line step with no DNS migration. Cloudflare Pages / Netlify are secondary backends for later (abstracted behind a `DeployBackend` interface).
- **Domain:** User owns a domain, currently on Vercel. If configured, the dashboard serves there; otherwise it serves on the default `*.vercel.app` URL.
- **Stable URL model:** First `track sync` creates a fixed project and deploys (stable URL). Every later `track sync` re-deploys to the *same project* -> **same URL, updated in place**. No new links, no drift.
- **Privacy:** **Optional, user's choice in the sync menu** (not mandatory). If enabled, the dashboard data is encrypted **client-side** (AES-GCM) before being written into the HTML; the host only ever serves ciphertext, and the viewer types a passphrase to decrypt in-browser. If not enabled, data is plaintext (protected only by URL obscurity). Passphrase is stored in local `config.json` so cron stays non-interactive.
- **Scope:** This is a **public PyPI tool** (`track-cli`), not just a personal script. Therefore `track sync` must be a **general, interactive, first-run wizard** ("do you have a domain? -> then x/y/z"), storing config — not hardcoded to one setup. The author is the first test subject / dogfooder.
- **Design:** The actual HTML is designed later with the **`/frontend-design` skill** (installed globally). Phase 1 ships a functional placeholder; Phase 4 applies real design.

## 1. Architecture

```
~/.timetrack/timelog.json   (source of truth — local, private)
        |  track dashboard / track sync
        v
build/  index.html   (SELF-CONTAINED: inline CSS+JS; data embedded as
        |             plaintext JSON, or as an AES-GCM blob if passphrase set)
        |  track sync -> DeployBackend.deploy(prod=True)
        v
Vercel project "track-dash"  --->  stable URL
   . 1st run: create project + deploy        -> track-dash.vercel.app
   . if domain configured: attach custom NS   -> track.yourdomain.com
   . Nth run: re-deploy same project           -> SAME URL, updated
        ^
        |-- cron (daily) -> non-interactive `track sync`
```

Properties:
- Zero 24/7 process, near-zero cost.
- Privacy by construction (data born local; deploy is opt-in).
- "From anywhere" = open the URL on any device/browser.

## 2. Config schema (`config.json` additions)

```json
{
  "aliases": { "old": "new" },
  "sync": {
    "configured": false,
    "host": "vercel",
    "project": "track-dash",
    "domain": "track.yourdomain.com",   // optional; null = use *.vercel.app
    "token": null,                       // VERCEL_TOKEN env or stored here (local only)
    "passphrase_protected": false,
    "passphrase": null,                  // stored locally so cron can re-encrypt
    "cron_installed": false
  }
}
```

- `configured` flips to `true` after the first-run wizard completes.
- `token` and `passphrase` live in already-private `~/.timetrack/config.json` (plaintext, local only). Wizard warns about this.

## 3. CLI commands

### `track dashboard [--days N] [--out DIR]`
Generate the self-contained `index.html` **locally only** (no deploy). Useful for previewing and for the design phase. Defaults: `days=30`, `out=~/.timetrack/dashboard`.

### `track sync [--install-cron]`
- If `sync.configured` is false -> run the **interactive setup wizard** (Section 4), then save config.
- Generate `index.html` into the dashboard build dir.
- Deploy via the configured backend -> print the resulting URL.
- Must be **non-interactive / idempotent** so cron never hangs.
- `--install-cron` writes the scheduled job (once) — see Section 5.

## 4. Interactive first-run wizard (`track sync`)

```
Set up remote dashboard? [Y/n]
  Host: vercel            (only backend in v1; others later)
  Vercel token:
      . run `vercel login` once, or
      . paste a VERCEL_TOKEN  -> stored in config (local only)
  Project name [track-dash]:
  Custom domain? (optional, e.g. track.yourdomain.com):
  Protect with a passphrase? [y/N]   <-- OPTIONAL choice, not mandatory
      . if yes -> prompt for passphrase (stored locally; used to encrypt each deploy)
Saving config...
Deploying...
OK Live at: https://track.yourdomain.com   (stable — re-run `track sync` to update)
```

- Wizard is **CLI-layer** (uses `click.prompt`); the facade only stores/returns config, no prompts.
- Subsequent runs skip the wizard (config present) and just deploy silently.

## 5. Cron installer (`track sync --install-cron`)

- **macOS:** write `~/Library/LaunchAgents/com.timetrack.sync.plist` running `track sync` daily (e.g. 23:55). Load it with `launchctl load`.
- **Linux:** append a `crontab` line `55 23 * * * /path/to/track sync`.
- Sets `sync.cron_installed = true` after writing. `track sync` itself stays prompt-free.

## 6. Component breakdown

| File | Add | Responsibility |
|------|-----|----------------|
| `timetrack/models.py` | `SyncConfig` (+ `passphrase` field); extend `Config.sync` | pydantic model for the `sync` block |
| `timetrack/core/constants.py` | `DASHBOARD_DIR` | build path for `index.html` |
| `timetrack/core/dashboard.py` | `DashboardManager` | build day/activity payload from log; render self-contained `index.html` (plaintext or AES-GCM encrypted) |
| `timetrack/core/deploy.py` | `DeployBackend` (ABC) + `VercelBackend` | `deploy(dir, prod=True) -> (ok, url)`; shells out to `vercel` CLI |
| `timetrack/core/facade.py` | `generate_dashboard`, `sync`, `get_sync_config`, `configure_sync`, `install_cron` | orchestration |
| `timetrack/cli.py` | `dashboard`, `sync` commands (+ wizard) | CLI wiring |

### `DashboardManager`
- `build_payload(days) -> dict`: read log, group by date (`daily`) and activity (`activities`), compute summary (total hours, avg/day, days tracked, activities), include recent entries.
- `generate(out_dir, days=30, passphrase=None) -> (ok, path)`:
  - plaintext mode: embed `DATA` JSON inline.
  - passphrase mode: AES-GCM encrypt payload (lazy-import `cryptography`; friendly error if missing), embed `ENC` (b64 salt+iv+ciphertext) + in-browser decrypt+prompt script.
  - Output: **one file**, inline `<style>` + inline `<script>`, **no CDN**, no external requests.

### `VercelBackend`
- Requires `vercel` CLI on PATH + `VERCEL_TOKEN` (env or config).
- `deploy(dir, prod=True)`: runs `vercel deploy --prod --yes --name <project> <dir>`, captures the deployment URL from stdout.
- Custom domain: best-effort `vercel domains add <domain>` on first run (idempotent; reports manual-verify step if needed).
- Returns `(ok, url_or_error)`.

## 7. Build sequence (phases)

1. **Phase 1 — Pipeline (plaintext):** `SyncConfig`, `DashboardManager` (plaintext self-contained HTML), `VercelBackend`, `track dashboard` + `track sync` wizard, `generate_dashboard`/`sync`/`configure_sync`. Validate end-to-end deploy (author dogfoods).
2. **Phase 2 — Privacy:** optional passphrase (AES-GCM) + in-browser decrypt prompt; stored locally for cron. Lazy-import `cryptography` (added to deps).
3. **Phase 3 — Cron:** `--install-cron` for macOS (launchd) + Linux (crontab); non-interactive `sync`.
4. **Phase 4 — Design:** invoke **`/frontend-design` skill** to design the actual page (palette, type, layout, signature). Applied to what `DashboardManager` emits. Dogfood deployed result.
5. **Phase 5 — Tests + docs:** unit tests (dashboard HTML self-contained / no CDN / encrypted blob present; deploy backend mocked subprocess; wizard flow via `CliRunner` + fake input; cron file contents) + README & `TEST_SPECIFICATION.md` updates.

## 8. Testing strategy
- **Dashboard:** assert `index.html` contains no `http(s)://cdn` references and embeds data; with passphrase, assert ciphertext blob + decrypt script present and plaintext absent.
- **Deploy:** mock `subprocess.run` to assert correct `vercel` args and URL parsing; assert failure handling.
- **Wizard:** `click.CliRunner` with `input=` simulating answers; assert config written.
- **Cron:** assert plist / crontab line contents and idempotency.

## 9. Open questions resolved / pending
- Done Host = Vercel (domain already there). Cloudflare/Netlify = later backends.
- Done Passphrase = optional choice in menu, not mandatory.
- Done `track dashboard` separate from `track sync` (local preview vs deploy).
- Pending approval to start Phase 1 implementation.
