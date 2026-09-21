# Sky Islands — notes for Claude

Capacitor wrapper around a single-file Canvas game. Read `HANDOFF.md` first; it is the
design brief and acceptance checklist.

## Ground rules

- `www/index.html` is the game and the only web asset. Do not split it into modules or
  add a bundler. Edit it in place.
- Anything native goes through Capacitor plugins called from the HTML via
  `window.Capacitor.Plugins.*`, guarded so the file still runs in a plain browser.
- After editing `www/` or `capacitor.config.ts`, run `npx cap sync ios`. The copy under
  `ios/App/App/public/` is generated and gitignored.
- `ios/App/CapApp-SPM/Package.swift` is managed by the Capacitor CLI. Do not hand-edit.
  `cap sync` points it at `github.com/ionic-team/capacitor-swift-pm`, which Xcode Cloud
  cannot clone (its GitHub App can only be installed by an ionic-team owner), so
  `scripts/patch-capacitor-spm.mjs` rewrites that dependency to the vendored manifest in
  `ios/App/capacitor-swift-pm/` after every sync. It patches the plugin manifests under
  `node_modules/@capacitor/*` too — leaving those on the remote package makes SwiftPM
  clone it anyway and warn about a conflicting identity. Run it via `npm run sync`, never
  bare `cap sync`; `ci_post_clone.sh` runs it after `npm ci`.
- `ios/App/capacitor-swift-pm/Package.swift` is a copy of the upstream tag, and upstream
  is only a manifest — the code arrives as notarized xcframework zips from GitHub
  Releases, which are plain HTTPS downloads Xcode Cloud can fetch. When bumping
  `@capacitor/ios`, replace it with the matching tag's file; the patch script refuses to
  run if the pinned version and `@capacitor/ios` disagree.
- `server/` is the leaderboard API. It runs as compose project `/root/sky-islands` on the
  Hetzner box (root@178.104.29.66), host port 8020, fronted by the Caddy block for
  skyislands.lumatechsolutions.co.uk in `/root/caddy/Caddyfile`. Deploy steps are in
  `server/README.md`. Reloading Caddy touches every site on that box; validate first.

## Things that are easy to break

- Audio: `AudioContext` must be created lazily on the first "Take off" tap (iOS gesture
  requirement). Do not move it earlier.
- Orientation: `Info.plist` allows landscape only and `UIRequiresFullScreen` is true.
  The HTML also has its own stage-rotation fallback; leave both.
- Status bar: hidden via the plist with `UIViewControllerBasedStatusBarAppearance` false.
- Device family is iPhone only (`TARGETED_DEVICE_FAMILY = 1`), deployment target 16.0.
- Xcode Cloud depends on the shared `App` scheme and `ios/App/ci_scripts/ci_post_clone.sh`.
  Keep `CURRENT_PROJECT_VERSION` at 1 in git; CI overwrites it with `CI_BUILD_NUMBER`.
  Bump `MARKETING_VERSION` by hand for a new user-facing version.

## Verifying without a Mac

This machine is Linux, so Xcode builds are not possible here. What can be checked locally:

- `node --check` on the inline script (extract between the `<script>` tags).
- Headless Chromium at 852×393 (iPhone 15 landscape CSS px) to see the start screen and
  confirm no console errors or external network requests.
- `npx cap sync ios` completes cleanly.
- Leaderboard end to end: run `server/` locally with `SKY_DB=/tmp/x.db uvicorn app:app`,
  make a scratch copy of `www/` with `const API = 'http://127.0.0.1:8000'`, expose
  `start`/`gameOver`/`G` on `window` before the closing `})();`, and drive it with a
  few `setTimeout`s under headless Chromium `--virtual-time-budget=6000`.
