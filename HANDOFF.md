# Sky Islands — iOS app handoff

## What this is

`sky-islands.html` is a complete, self-contained landscape arcade game: one file, no
build step, no dependencies. Canvas 2D with its own `requestAnimationFrame` loop,
DOM overlays for the touch buttons, start/game-over cards and the shop. The only
external request is a Google Fonts stylesheet for "Luckiest Guy", which falls back
to Impact / Arial Black if it fails.

Do not rewrite the game. The job is to wrap it in a native iOS shell.

## How it works (the parts that matter for the wrapper)

- **Stage rotation.** Everything lives inside `#stage`. If the viewport is taller
  than it is wide, `layoutStage()` rotates the stage 90° so the game is always
  played in landscape. If iOS is locked to landscape this simply never triggers.
- **Safe areas.** `--st/--sb/--sl/--sr` are set from `env(safe-area-inset-*)` and
  used by the controls; the canvas is full-bleed with
  `viewport-fit=cover`. A `#safeProbe` element measures the top inset for the HUD.
- **Saved data.** `localStorage` key `skyIslandsSave`, a JSON blob:
  `{ bank, best, planes:{}, themes:{}, plane, theme, codes:{}, god }`. Legacy key
  `skyIslandsBest` is read once if the new key is missing. All reads/writes are
  already wrapped in try/catch.
- **Audio.** A single `AudioContext` created lazily inside `blip()` and resumed if
  suspended. The first blip fires from the "Take off" tap, so the gesture
  requirement is satisfied — don't move audio creation earlier.
- **Input.** Pointer events on `.rb` buttons with `setPointerCapture`, plus a
  window-level `pointerup` that clears every key. Keyboard handlers exist for
  desktop testing and can stay.

## Target

iOS only, iPhone, landscape only, iOS 16+. Capacitor, not a rewrite.

## Steps

1. Scaffold a Capacitor app (`@capacitor/core`, `@capacitor/cli`, `@capacitor/ios`),
   app id something like `uk.co.lumatechsolutions.skyislands`, app name "Sky Islands".
2. Put `sky-islands.html` in `www/index.html` unchanged. Keep it as the only web asset.
3. `capacitor.config.ts`:
   - `webDir: 'www'`
   - `backgroundColor: '#12356b'`
   - `ios: { contentInset: 'never', scrollEnabled: false, limitsNavigationsToAppBoundDomains: false }`
4. `npx cap add ios && npx cap sync`.
5. In `Info.plist`: `UISupportedInterfaceOrientations` = landscape left + right only,
   `UIRequiresFullScreen` = true, `UIStatusBarHidden` = true,
   `UIViewControllerBasedStatusBarAppearance` = false.
6. Add `@capacitor/status-bar` and hide the bar on launch, or rely on the plist.
   Add `@capacitor/haptics` and fire a light impact on jump pads, bounce clouds and
   touchdown — hook it into `hit()`, the pad bounce and `touchdown()`.
7. App icon and splash: generate from the flame-cat emblem (orange radial flame with
   two dark eyes and a smile) on a deep blue `#12356b` field. Use
   `@capacitor/assets` from a single 1024×1024 source.
8. Offline: bundle the Luckiest Guy woff2 locally and swap the Google Fonts `<link>`
   for an `@font-face`, so the app never touches the network. This is the only edit
   to the HTML that should be needed.

## Acceptance checks

- Launches straight into landscape on an iPhone 15/16 with a notch; HUD, LAND button
  and the three control circles all clear of the notch and the home indicator.
- No rubber-band scroll, no text selection, no double-tap zoom, no browser chrome.
- Gold, unlocked planes, island skins and codes survive a force-quit and relaunch.
- Sound plays after the first tap on "Take off" and respects the silent switch.
- Runs at 60fps; check on a real device, not just the simulator.

## Later, if it's worth it

- Move save data to `@capacitor/preferences` so it can't be evicted by the system.
- Game Center leaderboard on `best`.
- StoreKit for the shop if it ever goes beyond in-game gold.
