#!/usr/bin/env bash
# Build Sky Islands for the iOS Simulator, install it on a booted iPhone and
# take a screenshot. Run on a Mac with Xcode. No signing needed.
#
#   scripts/build-sim.sh               # picks the newest available iPhone
#   scripts/build-sim.sh "iPhone 16"   # or name one
set -euo pipefail
cd "$(dirname "$0")/.."

DEVICE="${1:-}"
if [ -z "$DEVICE" ]; then
  DEVICE=$(xcrun simctl list devices available | grep -oE "iPhone [0-9]+( Pro| Plus| Pro Max)?" | sort -V | tail -1)
fi
echo "==> simulator: $DEVICE"

npm install --no-audit --no-fund
npx cap sync ios

DERIVED=build/DerivedData
xcodebuild \
  -project ios/App/App.xcodeproj -scheme App -configuration Debug \
  -sdk iphonesimulator -destination "platform=iOS Simulator,name=$DEVICE" \
  -derivedDataPath "$DERIVED" \
  CODE_SIGNING_ALLOWED=NO build | tail -3

APP="$DERIVED/Build/Products/Debug-iphonesimulator/App.app"
UDID=$(xcrun simctl list devices available | grep "$DEVICE (" | head -1 | grep -oE "[0-9A-F-]{36}")
xcrun simctl boot "$UDID" 2>/dev/null || true
open -a Simulator --args -CurrentDeviceUDID "$UDID" || true
xcrun simctl bootstatus "$UDID" -b
xcrun simctl install "$UDID" "$APP"
xcrun simctl launch "$UDID" uk.co.lumatechsolutions.skyislands
sleep 4
xcrun simctl io "$UDID" screenshot build/sim.png
echo "==> screenshot at build/sim.png"
