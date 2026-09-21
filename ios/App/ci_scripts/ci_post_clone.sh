#!/bin/sh
# Xcode Cloud post-clone hook for Sky Islands.
#
# The Xcode project depends on things git does not carry:
#   - node_modules/, which the Swift package at ios/App/CapApp-SPM points at
#     for the Capacitor plugins, so SPM resolution fails without it;
#   - ios/App/App/public/, the copy of www/ that `cap sync` produces.
# Xcode Cloud runs this after cloning and before resolving packages, which is
# exactly the window we need. Same shape as the Flutter apps' scripts.
#
#   https://developer.apple.com/documentation/xcode/writing-custom-build-scripts

set -eu

echo "→ Xcode Cloud post-clone: Node + Capacitor"

if ! command -v node >/dev/null 2>&1; then
  echo "  Installing Node via Homebrew (one-time per builder)…"
  HOMEBREW_NO_AUTO_UPDATE=1 brew install node
fi
export PATH="/opt/homebrew/bin:$PATH"
node -v
npm -v

cd "$CI_PRIMARY_REPOSITORY_PATH"
npm ci --no-audit --no-fund
npx cap sync ios

# TestFlight rejects a build number it has already seen, and the project pins
# CURRENT_PROJECT_VERSION = 1. CI_BUILD_NUMBER increments per Xcode Cloud build
# and flows into CFBundleVersion through Info.plist's $(CURRENT_PROJECT_VERSION).
if [ -n "${CI_BUILD_NUMBER:-}" ]; then
  cd "$CI_PRIMARY_REPOSITORY_PATH/ios/App"
  xcrun agvtool new-version -all "$CI_BUILD_NUMBER" >/dev/null
  echo "  Build number set to $CI_BUILD_NUMBER"
fi

echo "→ post-clone complete"
