#!/usr/bin/env node
/**
 * check-portability.mjs — hard gate for the morechat.co-Assistant content catalog.
 *
 * Checks (any failure => exit 1):
 *   G1 token scan      : catalog/** must contain ZERO hits of the legacy runtime bindings
 *                        WorkBuddy|CodeBuddy|workbuddy|codebuddy|\.workbuddy|
 *                        WORKBUDDY_CONFIG_DIR|expert-manager|package_expert|present_files
 *   G2 avatar policy   : no `avatars` directory and no image files anywhere under catalog/
 *   G3 Multica limits  : single file <= 1 MiB, single skill <= 8 MiB / 512 files,
 *                        single package (archive equivalent) <= 16 MiB
 *   G4 index integrity : index.json exists, schemaVersion 1, every package/skill sha256 and
 *                        size recomputes, every indexed package path and skill ns is present
 *
 * Node built-ins only. Run: node scripts/check-portability.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const ROOT = path.resolve(process.argv[2] || '.');
const CAT = path.join(ROOT, 'catalog');
const INDEX = path.join(ROOT, 'index.json');

const MIB = 1024 * 1024;
const LIMITS = { file: 1 * MIB, skill: 8 * MIB, skillFiles: 512, pkg: 16 * MIB };
const BANNED =
  /workbuddy|codebuddy|\bexpert-manager\b|package_expert|present_files|skill_track|skill-provider|SKILL_PROVIDER_|120\.77\.156\.6/gi;
// A hardcoded *public* bare-IP http(s) endpoint is never acceptable content: it is
// either vendor telemetry or a dead host. Loopback is allowed — several skills run
// their own local helper service on 127.0.0.1 and that is exactly right.
const BARE_IP_URL = /https?:\/\/(?!127\.0\.0\.1|localhost|0\.0\.0\.0|\[::1\])(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?/g;
const IMAGE_EXT = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.ico']);

const failures = [];
const fail = (gate, msg) => failures.push(`[${gate}] ${msg}`);

function walk(dir, base = dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(abs, base, out);
    else if (ent.isFile()) out.push({ abs, rel: path.relative(base, abs).split(path.sep).join('/') });
  }
  return out;
}
const sha256 = (buf) => crypto.createHash('sha256').update(buf).digest('hex');
function treeSha256(files, base) {
  const h = crypto.createHash('sha256');
  for (const f of [...files].sort((a, b) => (a.rel < b.rel ? -1 : a.rel > b.rel ? 1 : 0))) {
    const buf = fs.readFileSync(path.isAbsolute(f.abs) ? f.abs : path.join(base, f.abs));
    h.update(Buffer.from(f.rel, 'utf8'));
    h.update(Buffer.from([0]));
    h.update(buf);
    h.update(Buffer.from([0]));
  }
  return h.digest('hex');
}

// ------------------------------------------------------------------ G1 token scan
const all = walk(CAT);
const hitRows = [];
const ipRows = [];
for (const f of all) {
  const text = fs.readFileSync(f.abs).toString('latin1');
  const m = text.match(BANNED);
  if (m) hitRows.push({ file: `catalog/${f.rel}`, hits: m.length, tokens: [...new Set(m)].join(',') });
  const ips = text.match(BARE_IP_URL);
  if (ips) ipRows.push({ file: `catalog/${f.rel}`, hits: ips.length, tokens: [...new Set(ips)].join(',') });
}
if (!all.length) fail('G1', 'catalog/ is empty or missing');
if (hitRows.length) {
  for (const r of hitRows) fail('G1', `${r.file}: ${r.hits} hit(s) -> ${r.tokens}`);
}
if (ipRows.length) {
  for (const r of ipRows) fail('G6', `${r.file}: hardcoded IP endpoint ${r.tokens}`);
}

// ------------------------------------------------------------------ G2 avatars / images
for (const f of all) {
  const segs = f.rel.split('/');
  if (segs.includes('avatars')) fail('G2', `avatar path present: catalog/${f.rel}`);
  if (IMAGE_EXT.has(path.extname(f.rel).toLowerCase())) fail('G2', `image file present: catalog/${f.rel}`);
}

// ------------------------------------------------------------------ G3 size / count limits
const pkgsDir = path.join(CAT, 'packages');
const pkgRows = [];
const skillRows = [];
for (const kind of ['agent', 'team']) {
  const kdir = path.join(pkgsDir, kind);
  if (!fs.existsSync(kdir)) continue;
  for (const id of fs.readdirSync(kdir)) {
    const pdir = path.join(kdir, id);
    if (!fs.statSync(pdir).isDirectory()) continue;
    const pfiles = walk(pdir);
    const pbytes = pfiles.reduce((a, f) => a + fs.statSync(f.abs).size, 0);
    pkgRows.push({ pkg: `${kind}/${id}`, files: pfiles.length, bytes: pbytes });
    if (pbytes > LIMITS.pkg) fail('G3', `package ${kind}/${id} is ${(pbytes / MIB).toFixed(2)} MiB > 16 MiB`);
    const sdir = path.join(pdir, 'skills');
    if (!fs.existsSync(sdir)) continue;
    for (const ns of fs.readdirSync(sdir)) {
      const dir = path.join(sdir, ns);
      if (!fs.statSync(dir).isDirectory()) continue;
      const sfiles = walk(dir);
      const sbytes = sfiles.reduce((a, f) => a + fs.statSync(f.abs).size, 0);
      const maxFile = Math.max(0, ...sfiles.map((f) => fs.statSync(f.abs).size));
      skillRows.push({ ns, files: sfiles.length, bytes: sbytes, maxFile });
      if (sbytes > LIMITS.skill) fail('G3', `skill ${ns} is ${(sbytes / MIB).toFixed(2)} MiB > 8 MiB`);
      if (sfiles.length > LIMITS.skillFiles) fail('G3', `skill ${ns} has ${sfiles.length} files > 512`);
      for (const f of sfiles) {
        const sz = fs.statSync(f.abs).size;
        if (sz > LIMITS.file) fail('G3', `skill ${ns} file ${f.rel} is ${(sz / MIB).toFixed(2)} MiB > 1 MiB`);
      }
    }
    for (const f of pfiles) {
      const sz = fs.statSync(f.abs).size;
      if (sz > LIMITS.file) fail('G3', `${kind}/${id} file ${f.rel} is ${(sz / MIB).toFixed(2)} MiB > 1 MiB`);
    }
  }
}

// ------------------------------------------------------------------ G4 index integrity
let index = null;
if (!fs.existsSync(INDEX)) fail('G4', 'index.json missing');
else {
  try {
    index = JSON.parse(fs.readFileSync(INDEX, 'utf8'));
  } catch (e) {
    fail('G4', `index.json is not valid JSON: ${e.message}`);
  }
}
if (index) {
  if (index.schemaVersion !== 1) fail('G4', `schemaVersion is ${index.schemaVersion}, expected 1`);
  if (!Array.isArray(index.packages) || !index.packages.length) fail('G4', 'index.packages empty');
  let nSkills = 0;
  for (const p of index.packages || []) {
    const abs = path.join(CAT, p.path);
    if (!fs.existsSync(abs)) {
      fail('G4', `index path missing: catalog/${p.path}`);
      continue;
    }
    const files = walk(abs);
    const bytes = files.reduce((a, f) => a + fs.statSync(f.abs).size, 0);
    const hash = treeSha256(files);
    if (hash !== p.sha256) fail('G4', `${p.path}: sha256 mismatch (index ${p.sha256.slice(0, 12)} vs tree ${hash.slice(0, 12)})`);
    if (bytes !== p.bytes) fail('G4', `${p.path}: bytes mismatch (index ${p.bytes} vs tree ${bytes})`);
    if (files.length !== p.files) fail('G4', `${p.path}: file count mismatch (index ${p.files} vs tree ${files.length})`);
    for (const s of p.skills || []) {
      nSkills++;
      const sabs = path.join(abs, s.path);
      if (!fs.existsSync(sabs)) {
        fail('G4', `${p.path}/${s.path}: skill directory missing`);
        continue;
      }
      const sfiles = walk(sabs);
      const sbytes = sfiles.reduce((a, f) => a + fs.statSync(f.abs).size, 0);
      const shash = treeSha256(sfiles);
      if (shash !== s.sha256) fail('G4', `${p.path}/${s.path}: sha256 mismatch`);
      if (sbytes !== s.bytes) fail('G4', `${p.path}/${s.path}: bytes mismatch`);
      if (sfiles.length !== s.files) fail('G4', `${p.path}/${s.path}: file count mismatch`);
      if (s.ns !== path.basename(s.path)) fail('G4', `${p.path}: ns ${s.ns} != directory ${path.basename(s.path)}`);
    }
  }
  if (index.stats && index.stats.packages !== index.packages.length) fail('G4', 'stats.packages mismatch');
  if (index.stats && index.stats.skills !== nSkills) fail('G4', `stats.skills mismatch (${index.stats.skills} vs ${nSkills})`);
  if (index.stats && index.stats.files !== pkgRows.reduce((a, r) => a + r.files, 0)) fail('G4', 'stats.files mismatch with catalog tree');
}

// ------------------------------------------------------------------ G5 text integrity
const DEC = new TextDecoder('utf-8', { fatal: true });
let textFiles = 0;
let preexisting = 0;
for (const f of all) {
  const buf = fs.readFileSync(f.abs);
  if (buf.includes(0)) continue; // binary asset
  textFiles++;
  try {
    const s = DEC.decode(buf);
    preexisting += (s.match(/\uFFFD/g) || []).length;
  } catch {
    fail('G5', `invalid UTF-8 in catalog/${f.rel}`);
  }
  if (f.rel.endsWith('.json')) {
    try {
      JSON.parse(buf.toString('utf8'));
    } catch (e) {
      fail('G5', `catalog/${f.rel} is not valid JSON: ${e.message}`);
    }
  }
}

// ------------------------------------------------------------------ report
const maxSkill = skillRows.reduce((a, r) => (r.bytes > a.bytes ? r : a), { ns: '-', bytes: 0, files: 0, maxFile: 0 });
const maxPkg = pkgRows.reduce((a, r) => (r.bytes > a.bytes ? r : a), { pkg: '-', bytes: 0, files: 0 });
const maxFileAny = all.reduce((a, f) => Math.max(a, fs.statSync(f.abs).size), 0);

console.log('== portability gate ==');
console.log(`catalog files        : ${all.length}`);
console.log(`catalog bytes        : ${(all.reduce((a, f) => a + fs.statSync(f.abs).size, 0) / MIB).toFixed(2)} MiB`);
console.log(`packages             : ${pkgRows.length} (${index ? index.packages.filter((p) => p.kind === 'agent').length : '-'} agents / ${index ? index.packages.filter((p) => p.kind === 'team').length : '-'} teams)`);
console.log(`skills               : ${skillRows.length}`);
console.log(`G1 banned tokens     : ${hitRows.length === 0 ? 'PASS (0 hits)' : `FAIL (${hitRows.reduce((a, r) => a + r.hits, 0)} hits in ${hitRows.length} files)`}`);
console.log(`G2 avatars/images    : ${failures.some((f) => f.startsWith('[G2]')) ? 'FAIL' : 'PASS (none)'}`);
console.log(`G3 limits            : max file ${(maxFileAny / 1024).toFixed(0)} KiB (<=1 MiB) | max skill ${maxSkill.ns} ${maxSkill.files} files ${(maxSkill.bytes / MIB).toFixed(2)} MiB (<=8 MiB) | max pkg ${maxPkg.pkg} ${(maxPkg.bytes / MIB).toFixed(2)} MiB (<=16 MiB)`);
console.log(`G4 index integrity   : ${!index ? 'FAIL (no index)' : failures.some((f) => f.startsWith('[G4]')) ? 'FAIL' : 'PASS'}`);
console.log(`G5 text integrity    : ${failures.some((f) => f.startsWith('[G5]')) ? 'FAIL' : `PASS (${textFiles} text files strict UTF-8, all JSON parses; ${preexisting} pre-existing U+FFFD preserved from upstream)`}`);
if (index) console.log(`index.json sha256    : ${sha256(fs.readFileSync(INDEX))}`);

if (failures.length) {
  console.error(`\n${failures.length} failure(s):`);
  for (const f of failures.slice(0, 60)) console.error(`  ${f}`);
  if (failures.length > 60) console.error(`  ... ${failures.length - 60} more`);
  process.exit(1);
}
console.log('\nALL GATES PASS');
