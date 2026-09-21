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

## Building (needs a Mac with Xcode 15+)

```sh
npm install
npx cap sync ios      # copies www/ into the Xcode project and resolves plugins
npx cap open ios      # opens ios/App/App.xcodeproj
```

Then pick your team under Signing & Capabilities and run on a device. Test on a real
phone for frame rate, haptics and the silent switch. The simulator has no haptics.

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

Save data lives in `localStorage` under `skyIslandsSave`. See `HANDOFF.md` for the full
design notes and the acceptance checklist.
