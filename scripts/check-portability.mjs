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
 *   G5 text integrity  : catalog/** decodes as strict UTF-8, every catalog/**\/*.json parses
 *   G6 endpoint scan   : no hardcoded public bare-IP http(s) endpoint in catalog/**
 *   G7 preset layer    : every index package has presets/<kind>/<id>.preset.json and a matching
 *                        .cordis.yml; preset fields stay on the whitelist and never mention
 *                        model|provider|apiKey|api_key|secret|token|permission|role;
 *                        conversationStarters <= 3; contentSha256 equals index.json sha256;
 *                        the DSH side keeps the timed ask_user_question and pins no model
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

// ------------------------------------------------------------------ G7 preset layer
/**
 * presets/<kind>/<id>.preset.json is the Multica-facing description of a package, and
 * presets/<kind>/<id>.cordis.yml is the DSH-facing patch fragment. Both are generated by
 * scripts/build-presets.mjs. A preset may only describe content and composition: it must
 * not pin a model, a provider, a credential, or an authorization surface, because those
 * belong to the host profile the preset is composed into.
 */
const PRESET_DIR = path.join(ROOT, 'presets');
const PRESET_ALLOWED = new Set([
  'schemaVersion',
  'id',
  'kind',
  'name',
  'description',
  'personaPath',
  'skills',
  'conversationStarters',
  'team',
  'requires',
  'sourcePackage',
  'packageVersion',
  'contentSha256',
]);
const PRESET_TEAM_ALLOWED = new Set(['workflow', 'handoffs', 'doneWhen', 'routeHints', 'leadAgent', 'members']);
const PRESET_TEAM_MEMBER_ALLOWED = new Set(['id', 'skills', 'harness']);
const PRESET_WORKFLOWS = new Set(['pipeline', 'hub-and-spoke']);
const PRESET_FORBIDDEN_KEY = /model|provider|api[_-]?key|secret|token|permission|role/i;
// Model identifiers and credential shapes have no business in a preset file, in either half.
const PRESET_MODEL_NAME =
  /\b(?:gpt-[0-9][0-9a-z.-]*|o[13]-(?:mini|preview)[0-9a-z.-]*|claude-[0-9][0-9a-z.-]*|gemini-[0-9][0-9a-z.-]*|deepseek-(?:chat|reasoner|coder)[0-9a-z.-]*|qwen[0-9][0-9a-z.-]*|llama-?[0-9][0-9a-z.-]*|mistral-[0-9a-z.-]+)\b/i;
const PRESET_SECRET =
  /\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16})\b|-----BEGIN [A-Z ]*PRIVATE KEY-----/;

const MAX_STARTERS = 3;
const CORDIS_REQUIRED_ROWS = [
  "@deepseek-ai/dsh-agent-preset",
  "@deepseek-ai/dsh-persona",
  "@deepseek-ai/dsh-agent-instructions",
  "@deepseek-ai/dsh-skill-filesystem",
  "@deepseek-ai/dsh-tool-skill",
  "@deepseek-ai/dsh-tool-ask-user",
];
const presetIds = new Set();
const presetExpected = new Set();
let presetJsonCount = 0;
let presetCordisCount = 0;

function presetKeys(value, trail = '', out = []) {
  if (Array.isArray(value)) {
    value.forEach((v, i) => presetKeys(v, `${trail}[${i}]`, out));
    return out;
  }
  if (value && typeof value === 'object') {
    for (const [k, v] of Object.entries(value)) {
      out.push({ key: k, trail: `${trail}${k}` });
      presetKeys(v, `${trail}${k}.`, out);
    }
  }
  return out;
}

if (!index) {
  fail('G7', 'no index.json — preset layer cannot be verified');
} else {
  for (const p of index.packages || []) {
    const kind = p.kind;
    const id = p.id;
    const jsonRel = `presets/${kind}/${id}.preset.json`;
    const ymlRel = `presets/${kind}/${id}.cordis.yml`;
    presetExpected.add(jsonRel);
    presetExpected.add(ymlRel);

    // (1) every package must have a preset.json, plus its DSH twin
    const jsonAbs = path.join(ROOT, jsonRel);
    const ymlAbs = path.join(ROOT, ymlRel);
    if (!fs.existsSync(jsonAbs)) {
      fail('G7', `${jsonRel}: missing preset for package ${kind}/${id}`);
      continue;
    }
    let preset = null;
    try {
      preset = JSON.parse(fs.readFileSync(jsonAbs, 'utf8'));
    } catch (e) {
      fail('G7', `${jsonRel}: not valid JSON (${e.message})`);
      continue;
    }
    presetJsonCount++;
    presetIds.add(`${kind}/${id}`);

    // (2) no forbidden field name, anywhere, and no field outside the whitelist
    for (const { key, trail } of presetKeys(preset)) {
      if (PRESET_FORBIDDEN_KEY.test(key)) fail('G7', `${jsonRel}: forbidden field "${trail}"`);
    }
    for (const key of Object.keys(preset)) {
      if (!PRESET_ALLOWED.has(key)) fail('G7', `${jsonRel}: field "${key}" is not on the preset whitelist`);
    }
    for (const key of Object.keys(preset.team && typeof preset.team === 'object' ? preset.team : {})) {
      if (!PRESET_TEAM_ALLOWED.has(key)) fail('G7', `${jsonRel}: field "team.${key}" is not on the preset whitelist`);
    }
    const rawText = fs.readFileSync(jsonAbs, 'utf8');
    if (PRESET_SECRET.test(rawText)) fail('G7', `${jsonRel}: contains a credential-shaped literal`);

    // identity must match the index, not drift from it
    if (preset.schemaVersion !== 1) fail('G7', `${jsonRel}: schemaVersion is ${preset.schemaVersion}, expected 1`);
    if (preset.id !== id) fail('G7', `${jsonRel}: id ${preset.id} != index id ${id}`);
    if (preset.kind !== kind) fail('G7', `${jsonRel}: kind ${preset.kind} != index kind ${kind}`);
    if (!preset.name || typeof preset.name.zh !== 'string' || typeof preset.name.en !== 'string') {
      fail('G7', `${jsonRel}: name must be {zh,en} strings`);
    }
    if (typeof preset.description !== 'string') fail('G7', `${jsonRel}: description must be a string`);
    if (typeof preset.personaPath !== 'string' || !preset.personaPath) {
      fail('G7', `${jsonRel}: personaPath is empty`);
    } else if (!fs.existsSync(path.join(ROOT, preset.personaPath))) {
      fail('G7', `${jsonRel}: personaPath does not exist: ${preset.personaPath}`);
    }
    if (preset.sourcePackage !== `catalog/${p.path}`) {
      fail('G7', `${jsonRel}: sourcePackage ${preset.sourcePackage} != catalog/${p.path}`);
    }
    if (preset.packageVersion !== p.version) {
      fail('G7', `${jsonRel}: packageVersion ${preset.packageVersion} != index ${p.version}`);
    }
    if (!Array.isArray(preset.skills) || preset.skills.length !== (p.skills || []).length) {
      fail('G7', `${jsonRel}: skills ${Array.isArray(preset.skills) ? preset.skills.length : 'non-array'} != index ${(p.skills || []).length}`);
    } else {
      for (const ns of preset.skills) {
        if (!(p.skills || []).some((s) => s.ns === ns)) fail('G7', `${jsonRel}: skill ns ${ns} not in index`);
      }
    }
    if (!Array.isArray(preset.requires)) fail('G7', `${jsonRel}: requires must be an array`);
    if (!preset.team || typeof preset.team.leadAgent !== 'string' || !Array.isArray(preset.team.members)) {
      fail('G7', `${jsonRel}: team must be {leadAgent:string, members:[]}`);
    }
    if (preset.team && typeof preset.team === 'object') {
      const team = preset.team;
      // workflow shape: a pipeline or a hub; both must name real roster members
      if (team.workflow !== undefined && !PRESET_WORKFLOWS.has(team.workflow)) {
        fail('G7', `${jsonRel}: team.workflow ${JSON.stringify(team.workflow)} is not pipeline|hub-and-spoke`);
      }
      if (team.handoffs !== undefined) {
        if (!Array.isArray(team.handoffs) || team.handoffs.some((s) => typeof s !== 'string' || !s.trim())) {
          fail('G7', `${jsonRel}: team.handoffs must be a non-empty string array`);
        }
      }
      if (team.doneWhen !== undefined && (typeof team.doneWhen !== 'string' || !team.doneWhen.trim())) {
        fail('G7', `${jsonRel}: team.doneWhen must be a non-empty string`);
      }
      const rosterIds = new Set(
        (Array.isArray(team.members) ? team.members : []).map((m) => (m && typeof m === 'object' ? m.id : m)),
      );
      for (const hint of Array.isArray(team.routeHints) ? team.routeHints : []) {
        if (!hint || typeof hint.match !== 'string' || typeof hint.member !== 'string') {
          fail('G7', `${jsonRel}: team.routeHints entries must be {match:string, member:string}`);
          continue;
        }
        if (!rosterIds.has(hint.member)) fail('G7', `${jsonRel}: routeHint member ${hint.member} is not on the roster`);
        for (const k of Object.keys(hint)) {
          if (!['match', 'member'].includes(k)) fail('G7', `${jsonRel}: field "team.routeHints[].${k}" is not on the whitelist`);
        }
      }
      for (const m of Array.isArray(team.members) ? team.members : []) {
        if (typeof m === 'string') continue; // bare roster id, no per-member detail
        if (!m || typeof m !== 'object' || Array.isArray(m)) {
          fail('G7', `${jsonRel}: team.members entries must be ids or {id, skills, harness}`);
          continue;
        }
        for (const k of Object.keys(m)) {
          if (!PRESET_TEAM_MEMBER_ALLOWED.has(k)) fail('G7', `${jsonRel}: field "team.members[].${k}" is not on the whitelist`);
        }
        if (typeof m.id !== 'string' || !m.id.trim()) fail('G7', `${jsonRel}: team.members[] entry without id`);
        if (!Array.isArray(m.skills) || m.skills.some((s) => typeof s !== 'string')) {
          fail('G7', `${jsonRel}: team.members[].skills must be a string array`);
        } else {
          for (const ns of m.skills) {
            if (!preset.skills.includes(ns)) fail('G7', `${jsonRel}: member ${m.id} names skill ${ns} outside the package skills`);
          }
        }
        if (m.harness !== undefined && m.harness !== 'codex') {
          fail('G7', `${jsonRel}: team.members[].harness only accepts "codex"`);
        }
      }
    }

    // (3) conversationStarters <= 3
    if (!Array.isArray(preset.conversationStarters)) {
      fail('G7', `${jsonRel}: conversationStarters must be an array`);
    } else {
      if (preset.conversationStarters.length > MAX_STARTERS) {
        fail('G7', `${jsonRel}: conversationStarters has ${preset.conversationStarters.length} items > ${MAX_STARTERS}`);
      }
      if (preset.conversationStarters.some((s) => typeof s !== 'string' || !s.trim())) {
        fail('G7', `${jsonRel}: conversationStarters entries must be non-empty strings`);
      }
    }

    // (4) contentSha256 must equal the tree hash recorded in index.json
    if (preset.contentSha256 !== p.sha256) {
      fail('G7', `${jsonRel}: contentSha256 ${String(preset.contentSha256).slice(0, 12)} != index sha256 ${p.sha256.slice(0, 12)}`);
    }

    // DSH twin: structure, no model pin, no credential
    if (!fs.existsSync(ymlAbs)) {
      fail('G7', `${ymlRel}: missing DSH preset for package ${kind}/${id}`);
      continue;
    }
    presetCordisCount++;
    const yml = fs.readFileSync(ymlAbs, 'utf8');
    const firstLine = yml.split('\n', 1)[0];
    if (!/^#.*build-presets\.mjs.*勿手改/.test(firstLine)) {
      fail('G7', `${ymlRel}: first line must be the "generated by build-presets.mjs, do not edit" comment`);
    }
    for (const row of CORDIS_REQUIRED_ROWS) {
      if (!yml.includes(`name: '${row}'`)) fail('G7', `${ymlRel}: missing plugin row ${row}`);
    }
    if (!/mode:\s*timed/.test(yml)) fail('G7', `${ymlRel}: tool-ask-user mode: timed missing`);
    if (!/timeout:\s*120/.test(yml)) fail('G7', `${ymlRel}: tool-ask-user timeout: 120 missing`);
    if (PRESET_MODEL_NAME.test(yml)) fail('G7', `${ymlRel}: pins a model identifier (${yml.match(PRESET_MODEL_NAME)[0]})`);
    if (PRESET_SECRET.test(yml)) fail('G7', `${ymlRel}: contains a credential-shaped literal`);
    if (/api[_-]?key\s*:/i.test(yml)) fail('G7', `${ymlRel}: contains an api key field`);
    if (preset.personaPath && !yml.includes(preset.personaPath)) {
      fail('G7', `${ymlRel}: persona row does not reference ${preset.personaPath}`);
    }
  }

  // no orphan preset is allowed to linger after a package is dropped
  for (const kind of ['agent', 'team']) {
    const dir = path.join(PRESET_DIR, kind);
    if (!fs.existsSync(dir)) continue;
    for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!ent.isFile() || !/\.(preset\.json|cordis\.yml)$/.test(ent.name)) continue;
      const rel = `presets/${kind}/${ent.name}`;
      if (!presetExpected.has(rel)) fail('G7', `${rel}: stale preset with no index.json package`);
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
console.log(`G6 endpoint scan     : ${failures.some((f) => f.startsWith('[G6]')) ? 'FAIL' : 'PASS (no hardcoded public IP endpoint)'}`);
console.log(`G7 preset layer      : ${failures.some((f) => f.startsWith('[G7]')) ? 'FAIL' : `PASS (${presetJsonCount} preset.json + ${presetCordisCount} cordis.yml; no model/provider/apiKey/secret/token/permission/role field; conversationStarters <= ${MAX_STARTERS}; contentSha256 == index sha256; ask_user_question timed 120)`}`);
if (index) console.log(`index.json sha256    : ${sha256(fs.readFileSync(INDEX))}`);

if (failures.length) {
  console.error(`\n${failures.length} failure(s):`);
  for (const f of failures.slice(0, 60)) console.error(`  ${f}`);
  if (failures.length > 60) console.error(`  ... ${failures.length - 60} more`);
  process.exit(1);
}
console.log('\nALL GATES PASS');
