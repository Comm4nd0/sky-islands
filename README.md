# Sky Islands

A landscape arcade game (Canvas 2D, single HTML file) wrapped as a native iPhone app with
[Capacitor](https://capacitorjs.com). iOS 16+, landscape only, fully offline.

## Layout

| Path | What |
| --- | --- |
| `www/index.html` | The whole game. The only web asset. |
| `www/fonts/` | Luckiest Guy woff2, bundled so the app never touches the network. |
| `capacitor.config.ts` | App id, name, iOS webview settings. |
| `ios/` | Generated Xcode project (Swift Package Manager, no CocoaPods). Committed. |
| `assets/` | Icon and splash sources. `icon.svg` / `splash.svg` are the editable originals. |
| `server/` | Leaderboard API (FastAPI + SQLite). Deployed on Luma001 at https://skyislands.lumatechsolutions.co.uk. See `server/README.md`. |

## Building (needs a Mac with Xcode 15+)

```sh
npm install
npm run sync          # cap sync, then repoints the SPM manifests at the vendored package
npx cap open ios      # opens ios/App/App.xcodeproj
```

Then pick your team under Signing & Capabilities and run on a device. Test on a real
phone for frame rate, haptics and the silent switch. The simulator has no haptics.

## TestFlight via Xcode Cloud

The project is wired for Xcode Cloud: the `Sky Islands` scheme is shared, automatic signing uses
team TV3LZKGB46, and `ios/App/ci_scripts/ci_post_clone.sh` installs Node, runs
`npm ci`, `npm test` and `npm run sync`, repoints the Capacitor runtime at the vendored
`ios/App/capacitor-swift-pm` (Xcode Cloud will not start a workflow while a dependency
lives in a GitHub org you cannot install its app into), and stamps the build number into
`CFBundleVersion`. Every push to `main` can produce a TestFlight build once a workflow
exists. Creating the workflow is a one-time step in Xcode: open
`ios/App/App.xcodeproj`, Product > Xcode Cloud > Create Workflow, grant GitHub access to
`Comm4nd0/sky-islands`, and add a TestFlight (Internal Testing) post-action. The Archive
action's Distribution Preparation must be **App Store Connect**: builds archived as
"TestFlight (Internal Testing Only)" cannot be attached to an App Store version (builds 3–7
were). The workflow can be edited in the browser under App Store Connect › Xcode Cloud.

The App Store listing text, privacy answers and screenshots are in `store/`.

Note: archiving over SSH on the Mac mini fails at codesign with
`errSecInternalComponent` because the login keychain is locked without a GUI session.
Archive from Xcode itself, or let Xcode Cloud do it.

## Iterating on the game

Edit `www/index.html`, then `npm run sync` and rebuild in Xcode. To try it in a desktop
browser without Xcode, `npm run serve` and open http://localhost:8080. Keyboard controls
work on desktop (arrow keys).

## Regenerating the icon and splash

```sh
# edit assets/icon.svg / assets/splash.svg, then:
rsvg-convert -w 1024 -h 1024 assets/icon.svg   -o assets/icon-only.png
rsvg-convert -w 2732 -h 2732 assets/splash.svg -o assets/splash.png
cp assets/splash.png assets/splash-dark.png
npm run assets
```

## Flight Club (1.1.0)

The single-file Canvas game now includes a three-step flight school, pause/resume,
per-pointer touch controls, saved sound/haptic/motion/control settings, daily missions,
runway deliveries, ring/bounce/low-pass combos and a discovery logbook. Five aircraft
have distinct shapes; five biomes have their own scenery, landmarks and cached island
art. All game code and procedural visuals remain in `www/index.html`.

Free Flight uses owned aircraft and permits the existing free cheat codes. Daily Race
uses a fixed Bluebird, shared theme and course, and a 180-second limit. Invincibility is
disabled in races. Physics run at fixed 60 Hz, world height and pilot position are shared
across viewports, and ghosts record at 10 Hz using normalized altitude. New races use a
separate `/api/v2` leaderboard and ruleset, preserving the old API for previous builds.
Mission rewards never increase ranked scores. Personal ghosts also work offline.

Save data remains under `skyIslandsSave`; old gold, planes, themes, codes and player IDs
are retained. Settings, missions, discoveries, badges and recent personal ghosts are
added to that save. Native haptics remain guarded Capacitor calls. Audio starts only
following a flight-start gesture; all local play works offline.

## Validation

```sh
npm test       # saved progress, touch input, pause, features, determinism and ghost races
npm run sync   # includes the mandatory Swift package patch
```

The logic suite executes the real inline script with a small DOM/Canvas stub. It does
not replace visual or native-device checks. API test instructions are in
`server/README.md`; the device acceptance checklist and reviewer notes are in
`store/testflight-1.1.0.md`. See `HANDOFF.md` for the original wrapper brief.
