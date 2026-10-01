# App Store listing — Sky Islands 1.0.1

Source of truth for what is entered in App Store Connect. Submitted 2026-09-27 with build 8.
This app's media slot is the 6.5" display, so `screenshots/iphone-6.5/` (2778×1284) is what was
uploaded; `screenshots/iphone-6.9/` (2868×1320) is the same set at the newer size. No alpha. They were captured from the real game under
headless Chromium at 956×440 CSS px ×3, with the ghosts and leaderboard served from a mock API.

## App information

| Field | Value |
| --- | --- |
| Name | Sky Islands |
| Subtitle (30) | Fly, find islands, race ghosts |
| Bundle ID | uk.co.lumatechsolutions.skyislands |
| Primary category | Games (subcategories Action, Casual; App Store Connect has no Arcade) |
| Secondary category | Entertainment |
| Content rights | No third-party content (the Luckiest Guy font is Apache 2.0 and bundled) |
| Copyright | © 2026 Luma Tech Solutions |
| Price | Free, all territories |
| Support URL | https://skyislands.lumatechsolutions.co.uk/support |
| Marketing URL | (none) |
| Privacy policy URL | https://skyislands.lumatechsolutions.co.uk/privacy |
| Contact email | hello@lumatechsolutions.co.uk |

## Promotional text (170)

A new course every day. Fly it, post your score, and the day's best pilots race beside
everyone as ghosts.

## Description

Take the controls of a little jet and hop across an endless sea of floating islands.

Sky Islands is a bright, one-thumb-friendly arcade flyer. Climb, dive and skim the waves,
find new islands, and keep an eye on your petrol: grab drums in mid-air or land on a runway
to fill up. Rocks, hills and the sea all cost a flame, and you only have three.

DAILY COURSE, GHOST RACES
Every pilot flies the same course each day. Post your score and the day's best runs fly
beside everyone as ghosts, so you can see exactly where the leaders went.

REACH THE THIN AIR
Bounce off red jump pads and sparkly clouds into the stratosphere, where every kilometre
pays double gold.

POWER UPS
Sky Wings to climb like a rocket, speed boosts, shields, repairs, treasure and petrol drums.

HANGAR
Spend your gold on new planes, each with its own speed, lift and fuel economy, and new
island skins.

• Simple touch controls: climb, speed up, slow down
• Plays fully offline; the leaderboard is optional
• No ads, no accounts, no in-app purchases, no tracking

## Keywords (100)

plane,jet,arcade,flying,pilot,island,ghost,race,daily,leaderboard,casual,sky,clouds,flight

## Release

Automatic release after approval. Also on Apple silicon Macs (App Store Connect default).

## Age rating questionnaire

Result: 4+. Korea shows "Add RCN" (a GRAC rating number); none has been added.


Everything "None" / "No", except:
- User-generated content: Yes (pilot nicknames on the public leaderboard, filtered
  server-side; reports via the support page).
- Web access, messaging, gambling, contests, ads: No.

## App Privacy (nutrition label)

Data is collected. Not used for tracking. Purpose for every type: App Functionality.

| Type | Collected | Linked to user | Notes |
| --- | --- | --- | --- |
| Identifiers › User ID | Yes | Yes | Random ID the app generates; sent with scores and ghost requests |
| User Content › Gameplay Content | Yes | Yes | Score, islands, distance and flight path when a score is posted |
| User Content › Other User Content | Yes | Yes | The pilot nickname typed before posting |

Nothing else (no contact info, location, diagnostics, usage data or purchases).

## App Review information

- Sign-in required: No
- Contact: Marco Baldanza, hello@lumatechsolutions.co.uk
- Notes:

  > No account or login. Tap Take off; hold ▲ to climb, ▶/◀ for speed. After a run that earns
  > gold, the game-over card offers an optional "Post score" with a nickname, which shows the
  > daily and all-time leaderboard from our server. The day's top runs replay as translucent
  > "ghost" planes on the next take-off. Nicknames are filtered server-side for offensive
  > words; players can report a name at https://skyislands.lumatechsolutions.co.uk/support.
  > The game is landscape only and fully playable offline.

  > SECRET CODE (Guideline 2.1 clarification)
  > From the start screen, tap Shop. In Hangar & Shop, enter a code in the Secret code
  > field and tap Enter. These are all three built-in, optional, free gameplay cheat
  > codes in version 1.0.1 (8):
  >
  > FLAMECAT - Unlocks every plane and island skin and enables invincibility. Can be
  > redeemed once per local saved game.
  > IRONWING - Toggles invincibility on or off and can be used repeatedly. After testing
  > FLAMECAT, enter IRONWING to return to normal damage.
  > FULLTANK - Adds 2,500 in-game gold to the local bank. Can be redeemed once per local
  > saved game.
  >
  > All three codes are included in the app and work offline for every player. No
  > account, payment, purchase, subscription, external website or external code service
  > is required. Gold has no monetary value and cannot be bought for real money. Planes
  > and island skins can also be unlocked through normal gameplay using earned gold.
  > Codes and their effects are saved locally on the device; reusing a one-time code
  > displays "Already used that one."
  >
  > No sign-in is required to review any feature.

### Review clarification — 2026-09-30

Apple requested information about "Secret Code" under Guideline 2.1 for version 1.0.1
(8), submission `c34cb846-d475-4f0c-96e6-2e5822911c8f`. The review notes above were
expanded in App Store Connect to document all codes and their free, offline behaviour.
The existing game implementation already provides the described functionality; no new
binary is needed for this clarification. Chrome verification covered all three codes,
the invincibility toggle in both directions, saved rewards after reload, and the
one-time redemption message.

## Export compliance

`ITSAppUsesNonExemptEncryption` is `false` in Info.plist, so no question on submission.
