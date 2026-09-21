#!/usr/bin/env node
// Point every Capacitor SPM manifest at the vendored capacitor-swift-pm.
//
// Xcode Cloud refuses to start a workflow until every source-control dependency is
// "connected", and connecting ionic-team/capacitor-swift-pm needs the Xcode Cloud
// GitHub App installed by an ionic-team owner, which we will never have. Replacing
// the remote dependency with a local path package takes it out of the source-control
// graph altogether.
//
// Rewriting only ios/App/CapApp-SPM/Package.swift is not enough: the plugin manifests
// in node_modules declare the same remote package, so SwiftPM still clones it and warns
// about a conflicting identity ("will be escalated to an error in future versions").
// Every manifest has to agree on the local copy.
//
// Both sets of files are generated — CapApp-SPM by `cap sync`, node_modules by `npm ci` —
// so this runs after those, from `npm run sync` and from ci_post_clone.sh on Xcode Cloud.

import { readFileSync, writeFileSync, readdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const vendorDir = join(root, 'ios/App/capacitor-swift-pm');

// Matches both the `exact:` form cap sync writes and the `from:` form the plugins ship.
const REMOTE =
  /\.package\(url: "https:\/\/github\.com\/ionic-team\/capacitor-swift-pm\.git",\s*(?:exact|from): "[^"]+"\)/g;

// The vendored manifest pins the xcframework zips by version; it has to match the
// @capacitor/ios the plugins were built against, or the app ships a stale runtime.
const wanted = JSON.parse(
  readFileSync(join(root, 'node_modules/@capacitor/ios/package.json'), 'utf8')
).version;
const pinned = readFileSync(join(vendorDir, 'Package.swift'), 'utf8').match(
  /releases\/download\/([^/]+)\/Capacitor\.xcframework\.zip/
)?.[1];

if (pinned !== wanted) {
  console.error(
    `✗ ios/App/capacitor-swift-pm pins ${pinned}, but @capacitor/ios is ${wanted}.\n` +
      `  Refresh it from https://github.com/ionic-team/capacitor-swift-pm/blob/${wanted}/Package.swift`
  );
  process.exit(1);
}

const manifests = [join(root, 'ios/App/CapApp-SPM/Package.swift')];
const capacitorModules = join(root, 'node_modules/@capacitor');
for (const entry of readdirSync(capacitorModules)) {
  const candidate = join(capacitorModules, entry, 'Package.swift');
  if (existsSync(candidate)) manifests.push(candidate);
}

let patched = 0;
let alreadyLocal = 0;

for (const manifest of manifests) {
  const before = readFileSync(manifest, 'utf8');
  if (!REMOTE.test(before)) {
    if (before.includes('name: "capacitor-swift-pm", path:')) alreadyLocal++;
    continue;
  }
  REMOTE.lastIndex = 0;
  // SwiftPM resolves a path dependency relative to the manifest that declares it.
  const path = relative(dirname(manifest), vendorDir);
  writeFileSync(
    manifest,
    before.replace(REMOTE, `.package(name: "capacitor-swift-pm", path: "${path}")`)
  );
  console.log(`  ${relative(root, manifest)} → ${path}`);
  patched++;
}

if (patched === 0 && alreadyLocal === 0) {
  console.error('✗ No manifest declared capacitor-swift-pm; has the Capacitor layout changed?');
  process.exit(1);
}

console.log(`→ capacitor-swift-pm ${pinned}: ${patched} manifest(s) patched, ${alreadyLocal} already local`);
