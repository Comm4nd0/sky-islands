# Sky Islands — notes for Claude

Capacitor wrapper around a single-file Canvas game. Read `HANDOFF.md` first; it is the
design brief and acceptance checklist.

## Ground rules

- `www/index.html` is the game and the only web asset. Do not split it into modules or
  add a bundler. Edit it in place.
- `sky-islands.html` at the root is the untouched original. Do not edit it; the two
  files are expected to diverge as the app evolves.
- Anything native goes through Capacitor plugins called from the HTML via
  `window.Capacitor.Plugins.*`, guarded so the file still runs in a plain browser.
- After editing `www/` or `capacitor.config.ts`, run `npx cap sync ios`. The copy under
  `ios/App/App/public/` is generated and gitignored.
- `ios/App/CapApp-SPM/Package.swift` is managed by the Capacitor CLI. Do not hand-edit.

## Things that are easy to break

- Audio: `AudioContext` must be created lazily on the first "Take off" tap (iOS gesture
  requirement). Do not move it earlier.
- Orientation: `Info.plist` allows landscape only and `UIRequiresFullScreen` is true.
  The HTML also has its own stage-rotation fallback; leave both.
- Status bar: hidden via the plist with `UIViewControllerBasedStatusBarAppearance` false.
- Device family is iPhone only (`TARGETED_DEVICE_FAMILY = 1`), deployment target 16.0.

## Verifying without a Mac

This machine is Linux, so Xcode builds are not possible here. What can be checked locally:

- `node --check` on the inline script (extract between the `<script>` tags).
- Headless Chromium at 852×393 (iPhone 15 landscape CSS px) to see the start screen and
  confirm no console errors or external network requests.
- `npx cap sync ios` completes cleanly.
