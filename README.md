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
npx cap sync ios      # copies www/ into the Xcode project and resolves plugins
npx cap open ios      # opens ios/App/App.xcodeproj
```

Then pick your team under Signing & Capabilities and run on a device. Test on a real
phone for frame rate, haptics and the silent switch. The simulator has no haptics.

## TestFlight via Xcode Cloud

The project is wired for Xcode Cloud: the App scheme is shared, automatic signing uses
team TV3LZKGB46, and `ios/App/ci_scripts/ci_post_clone.sh` installs Node, runs
`npm ci` and `cap sync`, repoints the Capacitor runtime at the vendored
`ios/App/capacitor-swift-pm` (Xcode Cloud will not start a workflow while a dependency
lives in a GitHub org you cannot install its app into), and stamps the build number into
`CFBundleVersion`. Every push to `main` can produce a TestFlight build once a workflow
exists. Creating the workflow is a one-time step in Xcode: open
`ios/App/App.xcodeproj`, Product > Xcode Cloud > Create Workflow, grant GitHub access to
`Comm4nd0/sky-islands`, and add a TestFlight (Internal Testing) post-action.

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

## Native hooks inside the HTML

The game is unchanged apart from two additive edits:

- The Google Fonts `<link>` is replaced with a local `@font-face`.
- A `haptic()` helper (a no-op outside Capacitor) fires a light impact on jump pads,
  bounce clouds, touchdown and shield/god hits, and a medium impact on real damage.

Save data lives in `localStorage` under `skyIslandsSave`, which now also holds the pilot
name and a random player id used by the leaderboard. Posting a score is opt-in from the
game-over card, times out after 6 s, and fails quietly, so the game works fully offline.
When served from localhost the client talks to `http://127.0.0.1:8000` instead of
production.

See `HANDOFF.md` for the full design notes and the acceptance checklist.
