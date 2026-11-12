#!/usr/bin/env node
/**
 * fixup-catalog.mjs — mechanical cleanup of the *published* catalog surface.
 *
 * Scope (hard rules):
 *   - Writes only under catalog/ and index.json.
 *   - upstream/ is never read for repair and never written; it is the byte-accurate archive
 *     kept for a separate audit pass.
 *   - No persona prose is rewritten. Only the five mechanical classes below are touched.
 *
 * What is repaired (each one provable by re-scanning):
 *   1. avatar / members[].avatar -> removed from plugin.json. The repo ships zero raster
 *      images, so every such path was dangling; the product side generates avatars.
 *   2. dependencies.connectors / connectorIds -> removed from plugin.json; every connector
 *      name becomes the string `mcp:<name>` in index.json `requires[]`, which
 *      build-presets.mjs copies into presets/<kind>/<id>.preset.json `requires[]`.
 *      Strings, not `{kind,value}` objects: the read side (`packages/core/presets/types.ts`,
 *      `asStringArray(record.requires)`) keeps strings only and silently drops objects.
 *   3. bare skill names in agents/*.md -> the physically mounted skill directory name (`ns`,
 *      e.g. `opc-team--opc-orchestrator`) replaces the bare frontmatter name
 *      (`opc-orchestrator`). Identity fields (`name:`, `agentName:`, `subagent_type:`) and
 *      member roster rows name agents, not skills, and are left untouched. Declared names
 *      that resolve to no mounted `skills/<ns>/` go to `unmatched[]` instead of being guessed.
 *   4. brand words -> neutralized through the ordered rule table below;
 *      `references/...` paths that resolve from no legitimate anchor -> rewritten to the
 *      real relative path (unique basename inside the skill dir / package).
 *   5. SKILL.md without YAML frontmatter -> minimal `name:` (the ns directory) +
 *      `description:` (first sentence of the body, <=120 chars) is prepended.
 *
 * Pipeline: catalog/ is a build output of build-catalog.mjs, which re-copies upstream
 * verbatim, so this pass must run AFTER it:
 *   node scripts/build-catalog.mjs
 *   node scripts/fixup-catalog.mjs --apply
 *   node scripts/build-presets.mjs
 *   node scripts/build-presets.mjs --check
 *   node scripts/check-portability.mjs
 *   node scripts/fixup-catalog.mjs --verify
 *
 * Usage:
 *   node scripts/fixup-catalog.mjs --audit     # write fixup-audit.json, print counts
 *   node scripts/fixup-catalog.mjs --apply     # apply repairs, re-index (index.json)
 *   node scripts/fixup-catalog.mjs --verify    # re-audit, assert 1/2/3/4 are zero
 *   node scripts/fixup-catalog.mjs --audit --root <checkout>
 *
 * Node built-ins only.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

// ---------------------------------------------------------------- args / paths
const argv = process.argv.slice(2);
const argOf = (name, dflt) => {
  const i = argv.indexOf(name);
  return i >= 0 && argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : dflt;
};
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(argOf('--root', path.join(HERE, '..')));
const CAT = path.join(ROOT, 'catalog');
const PKG = path.join(CAT, 'packages');
const INDEX = path.join(ROOT, 'index.json');
const AUDIT_OUT = path.join(ROOT, 'fixup-audit.json');
const MODE = argv.find((a) => ['--audit', '--apply', '--verify'].includes(a)) || '--audit';

// Same skip set as build-catalog.mjs: index.json tree hashes are computed over exactly
// this file set, so re-indexing here must use the same filters.
const SKIP_DIRS = new Set(['avatars', '__pycache__', '.git', 'node_modules', '.venv']);
const SKIP_FILES = new Set(['.downloaded_at', '.DS_Store', 'Thumbs.db', 'skill_track.py']);
const SKIP_EXT = new Set(['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.ico', '.pyc', '.zip']);
const BIN_EXT = new Set(['.ttf', '.otf', '.woff', '.woff2', '.pdf', '.pyc']);

// ---------------------------------------------------------------- fs helpers
function walk(dir, base = dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      if (SKIP_DIRS.has(ent.name)) continue;
      walk(abs, base, out);
    } else if (ent.isFile()) {
      if (SKIP_FILES.has(ent.name)) continue;
      const ext = path.extname(ent.name).toLowerCase();
      if (SKIP_EXT.has(ext)) continue;
      out.push({ abs, rel: path.relative(base, abs).split(path.sep).join('/'), ext });
    }
  }
  return out;
}
function treeSha256(files) {
  const h = crypto.createHash('sha256');
  for (const f of [...files].sort((a, b) => (a.rel < b.rel ? -1 : a.rel > b.rel ? 1 : 0))) {
    h.update(Buffer.from(f.rel, 'utf8'));
    h.update(Buffer.from([0]));
    h.update(fs.readFileSync(f.abs));
    h.update(Buffer.from([0]));
  }
  return h.digest('hex');
}
const relOf = (abs) => path.relative(ROOT, abs).split(path.sep).join('/');
const posix = (p) => p.split(path.sep).join('/');
const lineOf = (text, pos) => text.slice(0, pos).split('\n').length;
const lineText = (text, pos) => {
  const s = text.lastIndexOf('\n', pos) + 1;
  const e = text.indexOf('\n', pos);
  return text.slice(s, e < 0 ? undefined : e).trim();
};
const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const writeJson = (p, obj) => fs.writeFileSync(p, `${JSON.stringify(obj, null, 2)}\n`, 'utf8');
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function isTextFile(abs, ext) {
  if (BIN_EXT.has(ext)) return false;
  const fd = fs.openSync(abs, 'r');
  const b = Buffer.alloc(8192);
  const n = fs.readSync(fd, b, 0, 8192, 0);
  fs.closeSync(fd);
  return !b.subarray(0, n).includes(0);
}

// ---------------------------------------------------------------- brand rules
/**
 * Ordered neutralization table. Targeted phrases run before the bare-token rule so the
 * result stays grammatical. No replacement introduces a newline, which keeps line numbers,
 * and therefore reporting, stable.
 */
const BRAND_RULES = [
  { id: 'R1', token: 'CodeBuddy', find: 'CodeBuddy Teams', to: 'morechat teams' },
  { id: 'R2', token: '.codebuddy', find: '~/.codebuddy', to: '.agents' },
  { id: 'R3', token: '.codebuddy', find: '.codebuddy-plugin', to: '.agents' },
  { id: 'R4', token: '.codebuddy', find: '.codebuddy', to: '.agents' },
  { id: 'R5', token: 'WorkBuddy', re: /\bworkbuddy\b/gi, to: 'morechat' },
  { id: 'R6', token: 'CodeBuddy', re: /\bcodebuddy\b/gi, to: 'morechat' },
  { id: 'R7', token: 'Codex', find: 'Use when Codex needs to', to: 'Use when the agent needs to' },
  { id: 'R8', token: 'Codex', find: '(Codex)', to: '(morechat)' },
  { id: 'R9', token: 'Codex', find: 'by Codex', to: 'by morechat' },
  { id: 'R10', token: 'Codex', find: 'for Codex', to: 'for morechat' },
  { id: 'R11', token: 'Codex', find: 'codex \u6d41\u7a0b', to: 'morechat \u6d41\u7a0b' },
  { id: 'R12', token: 'Codex', re: /\bcodex\b/gi, to: 'morechat' },
];
const BRAND_TOKENS = ['Codex', 'WorkBuddy', 'CodeBuddy', '.codebuddy'];
const BRAND_SCAN = /codex|workbuddy|codebuddy|\.codebuddy/i;

/** Apply the table line by line; return the new text plus one row per replacement. */
function brandPass(text, fileRel) {
  const hits = [];
  const out = text.split('\n').map((line, i) => {
    let cur = line;
    for (const rule of BRAND_RULES) {
      const re = rule.re ? new RegExp(rule.re.source, rule.re.flags) : new RegExp(escapeRe(rule.find), 'g');
      let m;
      re.lastIndex = 0;
      while ((m = re.exec(cur))) {
        hits.push({ file: fileRel, line: i + 1, token: rule.token, rule: rule.id, from: m[0], to: rule.to });
        cur = cur.slice(0, m.index) + rule.to + cur.slice(m.index + m[0].length);
        re.lastIndex = m.index + rule.to.length;
      }
    }
    return cur;
  });
  return { text: out.join('\n'), hits };
}

// ---------------------------------------------------------------- packages
function loadPackages() {
  const pkgs = [];
  for (const kind of ['agent', 'team']) {
    const kdir = path.join(PKG, kind);
    if (!fs.existsSync(kdir)) continue;
    for (const id of fs.readdirSync(kdir).sort()) {
      const dir = path.join(kdir, id);
      if (!fs.statSync(dir).isDirectory()) continue;
      const pluginPath = path.join(dir, 'plugin.json');
      const plugin = fs.existsSync(pluginPath) ? readJson(pluginPath) : {};
      const skillsRoot = path.join(dir, 'skills');
      const bareToNs = new Map();
      const nsSet = new Set();
      if (fs.existsSync(skillsRoot)) {
        for (const ns of fs.readdirSync(skillsRoot).sort()) {
          if (!fs.statSync(path.join(skillsRoot, ns)).isDirectory()) continue;
          nsSet.add(ns);
          const md = path.join(skillsRoot, ns, 'SKILL.md');
          if (!fs.existsSync(md)) continue;
          const fm = fs.readFileSync(md, 'utf8').match(/^---\r?\n([\s\S]*?)\r?\n---/);
          const m = fm && fm[1].match(/^name:\s*["']?([^"'\r\n]+?)["']?\s*$/m);
          if (m) bareToNs.set(m[1].trim(), ns);
        }
      }
      const memberIds = new Set(
        [
          ...(Array.isArray(plugin.teamInfo?.memberAgents) ? plugin.teamInfo.memberAgents : []),
          ...(Array.isArray(plugin.members) ? plugin.members.map((m) => (m && m.id) || m) : []),
          plugin.teamInfo?.leadAgent,
          plugin.agentName,
        ].filter((x) => typeof x === 'string' && x),
      );
      pkgs.push({ kind, id, dir, rel: `${kind}/${id}`, plugin, pluginPath, skillsRoot, bareToNs, nsSet, memberIds });
    }
  }
  return pkgs;
}

function packageOf(abs) {
  for (let d = path.dirname(abs); d.startsWith(PKG); d = path.dirname(d)) {
    if (fs.existsSync(path.join(d, 'plugin.json'))) return d;
    if (d === PKG) break;
  }
  return null;
}

// ---------------------------------------------------------------- items 1 / 2
function scanPluginFields(pkgs) {
  const avatar = { packages: 0, pluginFields: 0, memberFields: 0, dangling: 0, rows: [] };
  const connectors = { packages: 0, rows: [] };
  for (const p of pkgs) {
    const plug = p.plugin;
    let av = 0;
    if (Object.prototype.hasOwnProperty.call(plug, 'avatar')) {
      avatar.pluginFields++;
      av++;
      const exists = fs.existsSync(path.join(p.dir, String(plug.avatar)));
      if (!exists) avatar.dangling++;
      avatar.rows.push({ pkg: p.rel, field: 'avatar', value: String(plug.avatar), existsOnDisk: exists });
    }
    if (Array.isArray(plug.members)) {
      for (const m of plug.members) {
        if (!m || !Object.prototype.hasOwnProperty.call(m, 'avatar')) continue;
        avatar.memberFields++;
        av++;
        const exists = fs.existsSync(path.join(p.dir, String(m.avatar)));
        if (!exists) avatar.dangling++;
        avatar.rows.push({ pkg: p.rel, field: `members[${m.id}].avatar`, value: String(m.avatar), existsOnDisk: exists });
      }
    }
    if (av) avatar.packages++;

    const dpkg = plug.dependencies || {};
    if (Array.isArray(dpkg.connectors)) {
      for (const v of [...new Set(dpkg.connectors.map(String))]) {
        connectors.rows.push({ pkg: p.rel, field: 'dependencies.connectors', value: v, to: `mcp:${v}` });
      }
    }
    if (Array.isArray(plug.connectorIds) && plug.connectorIds.length) {
      for (const v of [...new Set(plug.connectorIds.map(String))]) {
        if (!connectors.rows.some((r) => r.pkg === p.rel && r.value === v)) {
          connectors.rows.push({ pkg: p.rel, field: 'connectorIds', value: v, to: `mcp:${v}` });
        }
      }
    }
  }
  connectors.packages = new Set(connectors.rows.map((r) => r.pkg)).size;
  return { avatar, connectors };
}

// ---------------------------------------------------------------- item 3
const IDENTITY_FIELD = /(subagent_type|agentName|agent_name|^\s*-?\s*name:|\bname:\s*")/;
const SKILL_WORD = /skill|\u6280\u80fd/i;

/** Top-level frontmatter key that owns `pos`; continuation lines inherit the previous key. */
function fmKeyAt(fmText, pos) {
  let cur = null;
  let offset = 0;
  for (const line of fmText.split('\n')) {
    const start = offset;
    offset += line.length + 1;
    const m = line.match(/^([A-Za-z_][\w-]*):/);
    if (pos >= start && pos < offset) return m ? m[1] : cur;
    if (m) cur = m[1];
  }
  return cur;
}

/**
 * One decision point shared by --audit and --apply, so the count and the rewrite can never
 * disagree. Returns 'replace' only when the token really is a skill reference.
 */
function bareDecision({ line, inFm, fmKey, bare, memberIds }) {
  if (IDENTITY_FIELD.test(line)) return 'keep-identity';
  if (inFm && fmKey === 'skills') return 'replace';
  if (memberIds.has(bare) && !SKILL_WORD.test(line)) return 'keep-member';
  return 'replace';
}

function scanBareRefs(pkgs) {
  const rows = [];
  for (const p of pkgs) {
    const adir = path.join(p.dir, 'agents');
    if (!fs.existsSync(adir)) continue;
    for (const f of fs.readdirSync(adir).filter((x) => x.endsWith('.md')).sort()) {
      const abs = path.join(adir, f);
      const text = fs.readFileSync(abs, 'utf8');
      const fmMatch = text.match(/^---\r?\n[\s\S]*?\r?\n---/);
      const fmText = fmMatch ? fmMatch[0] : '';
      const fmEnd = fmText.length;
      const rel = relOf(abs);
      for (const [bare, ns] of p.bareToNs) {
        if (!bare || bare === ns) continue;
        const re = new RegExp(`(^|[^\\w./-])${escapeRe(bare)}(?![\\w./-])`, 'g');
        let m;
        while ((m = re.exec(text))) {
          const pos = m.index + m[1].length;
          const line = lineText(text, pos);
          const inFm = pos < fmEnd;
          const key = inFm ? fmKeyAt(fmText, pos) : null;
          const decision = bareDecision({ line, inFm, fmKey: key, bare, memberIds: p.memberIds });
          rows.push({ pkg: p.rel, file: rel, line: lineOf(text, pos), bare, ns, inFrontmatter: inFm, fmKey: key, decision, ctx: line.slice(0, 140) });
        }
      }
    }
  }
  const replace = rows.filter((r) => r.decision === 'replace');
  const kept = rows.filter((r) => r.decision !== 'replace');
  return {
    occurrences: replace.length,
    files: new Set(replace.map((r) => r.file)).size,
    keptAsAgentIdentity: kept.length,
    rows: replace.map((r) => ({ pkg: r.pkg, file: r.file, line: r.line, from: r.bare, to: r.ns })),
    kept: kept.map((r) => ({ pkg: r.pkg, file: r.file, line: r.line, name: r.bare, decision: r.decision, ctx: r.ctx })),
  };
}

/**
 * Declared skill names that map to no mounted namespace (`skills/<ns>/`).
 * A declared name is matched when it equals an ns, or when `bareToNs` (the SKILL.md
 * frontmatter name) resolves to one. Everything else needs a human: guessing an ns
 * would silently point an agent at the wrong skill.
 */
function scanUnmatchedSkills(pkgs) {
  const rows = [];
  for (const p of pkgs) {
    const adir = path.join(p.dir, 'agents');
    if (!fs.existsSync(adir)) continue;
    for (const f of fs.readdirSync(adir).filter((x) => x.endsWith('.md')).sort()) {
      const abs = path.join(adir, f);
      const text = fs.readFileSync(abs, 'utf8');
      const fmMatch = text.match(/^---\r?\n[\s\S]*?\r?\n---/);
      if (!fmMatch) continue;
      const inner = fmMatch[0].replace(/^---\r?\n/, '').replace(/\r?\n---$/, '');
      const fmLines = inner.split('\n');
      let inSkills = false;
      for (let i = 0; i < fmLines.length; i++) {
        const line = fmLines[i];
        const key = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
        if (key) {
          inSkills = key[1] === 'skills';
          if (inSkills && key[2].trim()) {
            for (const tok of key[2].replace(/[\[\]]/g, '').split(',').map((s) => s.trim()).filter(Boolean)) {
              const name = tok.replace(/^['"]|['"]$/g, '');
              if (!p.nsSet.has(name) && !p.bareToNs.has(name)) rows.push({ pkg: p.rel, file: relOf(abs), line: i + 1, name });
            }
          }
          continue;
        }
        if (!inSkills) continue;
        const item = line.match(/^\s*-\s*(.+?)\s*$/);
        if (!item) continue;
        const name = item[1].replace(/^['"]|['"]$/g, '');
        if (!name) continue;
        if (!p.nsSet.has(name) && !p.bareToNs.has(name)) rows.push({ pkg: p.rel, file: relOf(abs), line: i + 1, name });
      }
    }
  }
  return rows;
}

// ---------------------------------------------------------------- item 4b: paths
/**
 * Two shapes of package-internal path that the namespace migration invalidated:
 *   references/<name>.md                      (written from the package root, the file now
 *                                              lives under skills/<ns>/references/)
 *   skills/<dir>/...                          (<dir> is the pre-namespace skill directory,
 *                                              now skills/<pkg>--<dir>/)
 */
const REF_RE = /(^|[^\w./-])((?:\.{0,2}\/)*(?:skills\/[A-Za-z0-9_.\-]+(?:\/[A-Za-z0-9_.\-\/]*)?|references\/[A-Za-z0-9_.\-\/]+\.md))/g;

function refContext(abs) {
  const dir = path.dirname(abs);
  let skillRoot = null;
  let pkgRoot = null;
  for (let d = dir; d.startsWith(PKG); d = path.dirname(d)) {
    if (!skillRoot && fs.existsSync(path.join(d, 'SKILL.md'))) skillRoot = d;
    if (!pkgRoot && fs.existsSync(path.join(d, 'plugin.json'))) pkgRoot = d;
    if (d === PKG) break;
  }
  const skillsDir = skillRoot ? path.dirname(skillRoot) : pkgRoot ? path.join(pkgRoot, 'skills') : null;
  return { dir, skillRoot, pkgRoot, skillsDir };
}

/** True when `ref` resolves from at least one legitimate anchor. */
function refResolves(ctx, ref) {
  return [ctx.dir, ctx.skillRoot, ctx.pkgRoot, ctx.skillsDir].filter(Boolean).some((a) => fs.existsSync(path.resolve(a, ref)));
}

/**
 * Plan a repair for an unresolvable reference:
 *   a) a `skills/<dir>/...` segment naming an un-namespaced skill directory is remapped to
 *      that skill's real `ns` (`skills/ugc-commerce/...` -> `skills/<pkg>--ugc-commerce/...`);
 *   b) a leading segment naming an un-namespaced skill directory
 *      (`koc-compliance-guard/references/x.md`) is remapped the same way;
 *   c) otherwise locate the file by unique basename inside the skill dir / package and
 *      rewrite the reference relative to the *referring file*.
 * null => dangling or ambiguous => manual list.
 */
function planRef(p, ctx, ref) {
  const stripped = ref.replace(/^(?:\.{0,2}\/)+/, '');
  const prefix = ref.slice(0, ref.length - stripped.length);
  const segs = stripped.split('/');

  if (segs[0] === 'skills' && segs.length >= 2 && ctx.skillsDir) {
    const bareDir = segs[1];
    const mapped = p.bareToNs.get(bareDir);
    if (mapped && mapped !== bareDir && !fs.existsSync(path.join(ctx.skillsDir, bareDir))) {
      const rest = segs.slice(2).join('/');
      const candidate = `${prefix}skills/${mapped}${rest ? `/${rest}` : '/'}`;
      if (refResolves(ctx, candidate)) return { to: candidate, reason: 'skill-dir-remap' };
    }
  }

  const head = segs[0];
  if (!prefix && head !== 'skills' && ctx.skillsDir) {
    const mapped = p.bareToNs.get(head);
    if (mapped && !fs.existsSync(path.join(ctx.skillsDir, head))) {
      const candidate = `${mapped}/${segs.slice(1).join('/')}`;
      if (refResolves(ctx, candidate)) return { to: candidate, reason: 'skill-dir-remap' };
    }
  }

  if (!/\/[^/]*\.[A-Za-z0-9]+$/.test(ref)) return null; // directory reference: no basename fallback
  const base = path.basename(ref);
  const pool = ctx.skillRoot || ctx.pkgRoot || ctx.dir;
  const hits = walk(pool).filter((f) => path.basename(f.abs) === base);
  if (hits.length === 1) return { to: posix(path.relative(ctx.dir, hits[0].abs)), reason: 'unique-basename' };
  return null;
}

function scanRefs(pkgs) {
  const byDir = new Map(pkgs.map((p) => [p.dir, p]));
  const rows = [];
  let resolvable = 0;
  for (const f of walk(PKG)) {
    if (f.ext !== '.md' || !isTextFile(f.abs, f.ext)) continue;
    const p = byDir.get(packageOf(f.abs));
    if (!p) continue;
    const text = fs.readFileSync(f.abs, 'utf8');
    const ctx = refContext(f.abs);
    let m;
    REF_RE.lastIndex = 0;
    while ((m = REF_RE.exec(text))) {
      const ref = m[2];
      if (text[m.index + m[0].length] === '*') continue; // `skills/opc-*` is a glob, not a path
      if (refResolves(ctx, ref)) {
        resolvable++;
        continue;
      }
      const plan = planRef(p, ctx, ref);
      rows.push({
        pkg: p.rel,
        file: relOf(f.abs),
        line: lineOf(text, m.index),
        ref,
        fix: plan ? plan.to : null,
        reason: plan ? plan.reason : 'unresolved',
        ctx: lineText(text, m.index).slice(0, 140),
      });
    }
  }
  return { resolvable, unresolved: rows.length, fixable: rows.filter((r) => r.fix).length, rows };
}

// ---------------------------------------------------------------- item 5
function scanFrontmatter(pkgs) {
  const rows = [];
  for (const p of pkgs) {
    for (const ns of [...p.nsSet].sort()) {
      const md = path.join(p.skillsRoot, ns, 'SKILL.md');
      if (!fs.existsSync(md)) continue;
      const text = fs.readFileSync(md, 'utf8');
      if (/^---\r?\n/.test(text)) continue;
      const h1 = (text.match(/^#\s+(.+)$/m) || [])[1] || '';
      rows.push({
        pkg: p.rel,
        skill: ns,
        title: h1.trim(),
        suggestedName: ns.startsWith(`${p.id}--`) ? ns.slice(p.id.length + 2) : ns,
        file: relOf(md),
      });
    }
  }
  return { count: rows.length, rows };
}

// ---------------------------------------------------------------- integrity
function indexState() {
  if (!fs.existsSync(INDEX)) return { ok: false, problems: ['index.json missing'], index: null };
  const index = readJson(INDEX);
  const problems = [];
  for (const entry of index.packages || []) {
    const dir = path.join(CAT, entry.path);
    if (!fs.existsSync(dir)) {
      problems.push(`missing package dir catalog/${entry.path}`);
      continue;
    }
    const files = walk(dir);
    const bytes = files.reduce((a, f) => a + fs.statSync(f.abs).size, 0);
    if (treeSha256(files) !== entry.sha256) problems.push(`${entry.path}: sha256 stale`);
    if (bytes !== entry.bytes) problems.push(`${entry.path}: bytes stale (index ${entry.bytes} on disk ${bytes})`);
    if (files.length !== entry.files) problems.push(`${entry.path}: file count stale (index ${entry.files} on disk ${files.length})`);
    for (const s of entry.skills || []) {
      const sdir = path.join(dir, s.path);
      if (!fs.existsSync(sdir)) {
        problems.push(`${entry.path}/${s.path}: skill dir missing`);
        continue;
      }
      const sf = walk(sdir);
      const sb = sf.reduce((a, f) => a + fs.statSync(f.abs).size, 0);
      if (treeSha256(sf) !== s.sha256) problems.push(`${entry.path}/${s.path}: skill sha256 stale`);
      if (sb !== s.bytes) problems.push(`${entry.path}/${s.path}: skill bytes stale`);
      if (sf.length !== s.files) problems.push(`${entry.path}/${s.path}: skill file count stale`);
    }
  }
  return { ok: problems.length === 0, problems, index };
}

/**
 * preset.requires must carry every mcp requirement index.json declares.
 *
 * The read side (`packages/core/presets/types.ts`: `asStringArray(record.requires)`)
 * keeps strings only and silently drops object entries, so an mcp requirement is
 * carried as the string `mcp:<name>` and never as `{kind,value}`.
 */
const mcpReq = (value) => `mcp:${value}`;
const mcpReqsOf = (list) =>
  (Array.isArray(list) ? list : [])
    .map((r) => {
      if (typeof r === 'string') return r;
      if (r && typeof r === 'object' && r.value) return mcpReq(r.value);
      return null;
    })
    .filter((r) => typeof r === 'string' && r.startsWith('mcp:'))
    .sort();

function presetMcpState(index) {
  const problems = [];
  for (const entry of index?.packages || []) {
    const rel = `presets/${entry.kind}/${entry.id}.preset.json`;
    const abs = path.join(ROOT, rel);
    if (!fs.existsSync(abs)) {
      problems.push(`${rel}: missing preset`);
      continue;
    }
    const preset = readJson(abs);
    const want = mcpReqsOf(entry.requires);
    const have = mcpReqsOf(preset.requires);
    if (want.join(',') !== have.join(',')) problems.push(`${rel}: requires ${JSON.stringify(have)} != index ${JSON.stringify(want)} (run node scripts/build-presets.mjs)`);
  }
  return { ok: problems.length === 0, problems };
}

// ---------------------------------------------------------------- scan
function scan() {
  const pkgs = loadPackages();
  const { avatar, connectors } = scanPluginFields(pkgs);
  const bare = scanBareRefs(pkgs);
  const refs = scanRefs(pkgs);
  const fm = scanFrontmatter(pkgs);

  const brandRows = [];
  for (const f of walk(CAT)) {
    if (!isTextFile(f.abs, f.ext)) continue;
    const text = fs.readFileSync(f.abs, 'utf8');
    if (!BRAND_SCAN.test(text)) continue;
    brandRows.push(...brandPass(text, relOf(f.abs)).hits);
  }
  const byToken = Object.fromEntries(BRAND_TOKENS.map((t) => [t, 0]));
  for (const r of brandRows) byToken[r.token] = (byToken[r.token] || 0) + 1;

  const idx = indexState();
  return {
    schemaVersion: 1,
    generator: 'morechat-assistant/scripts/fixup-catalog.mjs',
    generatedAt: new Date().toISOString(),
    root: ROOT,
    counts: {
      packages: pkgs.length,
      agents: pkgs.filter((p) => p.kind === 'agent').length,
      teams: pkgs.filter((p) => p.kind === 'team').length,
      imageFiles: walk(CAT).filter((f) => /\.(png|jpe?g|gif|webp|bmp|ico)$/i.test(f.rel)).length,
    },
    avatarFields: avatar,
    connectorFields: connectors,
    bareSkillRefs: {
      occurrences: bare.occurrences,
      files: bare.files,
      keptAsAgentIdentity: bare.keptAsAgentIdentity,
      rows: bare.rows,
      kept: bare.kept,
      unmatched: scanUnmatchedSkills(pkgs),
    },
    badPaths: { resolvable: refs.resolvable, unresolved: refs.unresolved, fixable: refs.fixable, rows: refs.rows },
    brandWords: { total: brandRows.length, byToken, rows: brandRows },
    missingFrontmatter: fm,
    indexIntegrity: { ok: idx.ok, problems: idx.problems },
    presetLayer: (() => {
      const pm = presetMcpState(idx.index);
      return { ok: pm.ok, problems: pm.problems };
    })(),
    _index: idx.index,
  };
}

// ---------------------------------------------------------------- item 5: frontmatter
/** First sentence of the first paragraph that is not a heading or a fence. */
function firstSentence(text) {
  const paras = text
    .replace(/^\uFEFF/, '')
    .split(/\r?\n\s*\r?\n/)
    .map((s) => s.trim())
    .filter((s) => s && !s.startsWith('#') && !s.startsWith('```') && !s.startsWith('---'));
  const para = paras[0] || '';
  const flat = para.replace(/\s+/g, ' ').trim();
  if (!flat) return '';
  const m = flat.match(/^.*?[.!?\u3002\uff01\uff1f](?=\s|$|[\u4e00-\u9fff])/);
  const first = (m ? m[0] : flat).trim();
  return first.length > 120 ? `${first.slice(0, 117)}...` : first;
}

/** Prepend `name` (the ns directory) + `description` (first sentence) to a bare SKILL.md. */
function addFrontmatter(p) {
  const written = [];
  if (!fs.existsSync(p.skillsRoot)) return written;
  for (const ns of [...p.nsSet].sort()) {
    const md = path.join(p.skillsRoot, ns, 'SKILL.md');
    if (!fs.existsSync(md)) continue;
    const text = fs.readFileSync(md, 'utf8');
    if (/^---\r?\n/.test(text)) continue;
    const desc = (firstSentence(text) || `Skill ${ns}`).replace(/"/g, "'");
    fs.writeFileSync(md, `---\nname: ${ns}\ndescription: "${desc}"\n---\n\n${text.replace(/^\uFEFF/, '')}`, 'utf8');
    written.push({ skill: ns, file: relOf(md), name: ns, description: desc });
  }
  return written;
}

// ---------------------------------------------------------------- apply
function apply() {
  const pkgs = loadPackages();
  const log = { pluginJson: [], mcp: [], bare: [], refs: [], brand: 0, frontmatter: [], index: [] };

  // (0) connector requirements are read before the fields are removed
  const mcpByPkg = new Map();
  for (const p of pkgs) {
    const names = [
      ...(Array.isArray(p.plugin.dependencies?.connectors) ? p.plugin.dependencies.connectors : []),
      ...(Array.isArray(p.plugin.connectorIds) ? p.plugin.connectorIds : []),
    ].map(String);
    if (names.length) mcpByPkg.set(p.rel, [...new Set(names)]);
  }

  // (1) plugin.json: drop avatar / members[].avatar / connectors
  for (const p of pkgs) {
    if (!fs.existsSync(p.pluginPath)) continue;
    const before = fs.readFileSync(p.pluginPath, 'utf8');
    const plug = JSON.parse(before);
    const removed = [];
    if (Object.prototype.hasOwnProperty.call(plug, 'avatar')) {
      delete plug.avatar;
      removed.push('avatar');
    }
    if (Array.isArray(plug.members)) {
      for (const m of plug.members) {
        if (m && Object.prototype.hasOwnProperty.call(m, 'avatar')) {
          delete m.avatar;
          removed.push(`members.${m.id}.avatar`);
        }
      }
    }
    if (plug.dependencies && Object.prototype.hasOwnProperty.call(plug.dependencies, 'connectors')) {
      delete plug.dependencies.connectors;
      removed.push('dependencies.connectors');
      if (!Object.keys(plug.dependencies).length) delete plug.dependencies;
    }
    if (Object.prototype.hasOwnProperty.call(plug, 'connectorIds')) {
      delete plug.connectorIds;
      removed.push('connectorIds');
    }
    const after = `${JSON.stringify(plug, null, 2)}\n`;
    if (after !== before) {
      fs.writeFileSync(p.pluginPath, after, 'utf8');
      log.pluginJson.push({ pkg: p.rel, removed });
    }
  }

  // (1b) SKILL.md without frontmatter: prepend the minimal, machine-derivable pair.
  //      name = the namespace directory, description = first sentence of the body.
  const fmWritten = [];
  for (const p of pkgs) fmWritten.push(...addFrontmatter(p));
  log.frontmatter = fmWritten;

  // (2) text passes. Order per file: reference paths -> bare skill names -> brand words.
  const byDir = new Map(pkgs.map((p) => [p.dir, p]));
  for (const f of walk(CAT)) {
    if (!isTextFile(f.abs, f.ext)) continue;
    const original = fs.readFileSync(f.abs, 'utf8');
    const fileRel = relOf(f.abs);
    const p = byDir.get(packageOf(f.abs)) || null;
    const ctx = refContext(f.abs);
    let next = original;

    if (f.ext === '.md' && p) {
      // (2a) reference paths that resolve from no legitimate anchor
      next = next.replace(REF_RE, (whole, lead, ref, offset) => {
        if (next[offset + whole.length] === '*') return whole; // glob pattern, not a path
        if (refResolves(ctx, ref)) return whole;
        const plan = planRef(p, ctx, ref);
        if (!plan) return whole;
        log.refs.push({ file: fileRel, from: ref, to: plan.to, reason: plan.reason });
        return lead + plan.to;
      });

      // (2b) bare skill names, only inside this package's own agents/*.md
      if (path.dirname(f.abs) === path.join(p.dir, 'agents')) {
        const fmMatch = next.match(/^---\r?\n[\s\S]*?\r?\n---/);
        const fmText = fmMatch ? fmMatch[0] : '';
        const fmEnd = fmText.length;
        for (const [bare, ns] of p.bareToNs) {
          if (!bare || bare === ns) continue;
          const re = new RegExp(`(^|[^\\w./-])${escapeRe(bare)}(?![\\w./-])`, 'g');
          const base = next;
          next = base.replace(re, (whole, lead, offset) => {
            const pos = offset + lead.length;
            const line = lineText(base, pos);
            const inFm = pos < fmEnd;
            const key = inFm ? fmKeyAt(fmText, pos) : null;
            if (bareDecision({ line, inFm, fmKey: key, bare, memberIds: p.memberIds }) !== 'replace') return whole;
            log.bare.push({ file: fileRel, from: bare, to: ns });
            return lead + ns;
          });
        }
      }
    }

    // (2c) brand words in every text file
    const bp = brandPass(next, fileRel);
    next = bp.text;
    log.brand += bp.hits.length;

    if (next !== original) fs.writeFileSync(f.abs, next, 'utf8');
  }

  // (3) re-index: recompute tree hashes and carry the connector requirements
  const index = readJson(INDEX);
  for (const entry of index.packages || []) {
    const dir = path.join(CAT, entry.path);
    const files = walk(dir);
    entry.files = files.length;
    entry.bytes = files.reduce((a, f) => a + fs.statSync(f.abs).size, 0);
    entry.sha256 = treeSha256(files);
    for (const s of entry.skills || []) {
      const sdir = path.join(dir, s.path);
      if (!fs.existsSync(sdir)) continue;
      const sf = walk(sdir);
      s.files = sf.length;
      s.bytes = sf.reduce((a, f) => a + fs.statSync(f.abs).size, 0);
      s.sha256 = treeSha256(sf);
    }
    const want = mcpByPkg.get(`${entry.kind}/${entry.id}`) || [];
    if (want.length) {
      // Keep the string requires build-catalog writes (python/node/canvas) and append
      // one `mcp:<name>` string per connector; object entries are not readable by the
      // preset parser, so any legacy {kind,value} entry is folded back into a string.
      const requires = (Array.isArray(entry.requires) ? entry.requires : []).filter((r) => typeof r === 'string');
      for (const r of Array.isArray(entry.requires) ? entry.requires : []) {
        if (r && typeof r === 'object' && r.value && !requires.includes(mcpReq(r.value))) requires.push(mcpReq(r.value));
      }
      for (const name of want) {
        if (!requires.includes(mcpReq(name))) requires.push(mcpReq(name));
      }
      if (JSON.stringify(requires) !== JSON.stringify(entry.requires)) entry.requires = requires;
      log.mcp.push({ pkg: `${entry.kind}/${entry.id}`, requires: entry.requires.filter((r) => typeof r === 'string' && r.startsWith('mcp:')) });
    }
  }
  if (index.stats) {
    index.stats.files = (index.packages || []).reduce((a, e) => a + e.files, 0);
    index.stats.bytes = (index.packages || []).reduce((a, e) => a + e.bytes, 0);
    index.stats.skills = (index.packages || []).reduce((a, e) => a + (e.skills || []).length, 0);
  }
  writeJson(INDEX, index);
  log.index.push(`recomputed sha256/bytes/files for ${(index.packages || []).length} package(s), ${index.stats?.skills ?? 0} skill dir(s)`);
  return log;
}

// ---------------------------------------------------------------- report
function printAudit(a) {
  console.log('== fixup audit ==');
  console.log(`root                 : ${a.root}`);
  console.log(`packages             : ${a.counts.packages} (${a.counts.agents} agents / ${a.counts.teams} teams)`);
  console.log(
    `(1) avatar refs      : ${a.avatarFields.packages} package(s) | plugin.json avatar ${a.avatarFields.pluginFields} | members[].avatar ${a.avatarFields.memberFields} | dangling ${a.avatarFields.dangling} | raster images on disk ${a.counts.imageFiles}`,
  );
  console.log(`(2) connector refs   : ${a.connectorFields.packages} package(s) | ${a.connectorFields.rows.length} entry(ies) -> ${[...new Set(a.connectorFields.rows.map((r) => r.value))].join(', ') || '-'}`);
  console.log(`(3) bare skill refs  : ${a.bareSkillRefs.occurrences} occurrence(s) in ${a.bareSkillRefs.files} file(s) | ${a.bareSkillRefs.keptAsAgentIdentity} agent-identity occurrence(s) excluded`);
  console.log(`(4a) brand words     : ${a.brandWords.total} -> ${BRAND_TOKENS.map((t) => `${t}=${a.brandWords.byToken[t] || 0}`).join(', ')}`);
  console.log(`(4b) ref paths       : ${a.badPaths.unresolved} unresolved of ${a.badPaths.resolvable + a.badPaths.unresolved} (${a.badPaths.fixable} mechanically fixable)`);
  console.log(`(5) SKILL.md w/o fm  : ${a.missingFrontmatter.count} (manual)`);
  console.log(`index integrity      : ${a.indexIntegrity.ok ? 'ok' : `${a.indexIntegrity.problems.length} stale entr(ies)`}`);
  if (a.brandWords.total) {
    const perRule = new Map();
    for (const r of a.brandWords.rows) {
      const k = `${r.rule}  ${r.from} -> ${r.to}`;
      perRule.set(k, (perRule.get(k) || 0) + 1);
    }
    console.log('brand rules hit      :');
    for (const [k, n] of perRule) console.log(`  ${k}   x${n}`);
  }
}

function verify() {
  const a = scan();
  const pm = presetMcpState(a._index);
  const checks = [
    { label: '(1) avatar refs == 0', ok: a.avatarFields.packages === 0 && a.avatarFields.pluginFields === 0 && a.avatarFields.memberFields === 0, detail: `packages=${a.avatarFields.packages} plugin=${a.avatarFields.pluginFields} members=${a.avatarFields.memberFields}` },
    { label: '(2) connector refs == 0', ok: a.connectorFields.packages === 0, detail: `packages=${a.connectorFields.packages}` },
    { label: '(3) bare skill refs == 0', ok: a.bareSkillRefs.occurrences === 0, detail: `occurrences=${a.bareSkillRefs.occurrences}` },
    { label: '(4) brand words == 0', ok: a.brandWords.total === 0, detail: BRAND_TOKENS.map((t) => `${t}=${a.brandWords.byToken[t] || 0}`).join(' ') },
    { label: '(4b) unresolved ref paths == 0', ok: a.badPaths.unresolved === 0, detail: `unresolved=${a.badPaths.unresolved} of ${a.badPaths.resolvable + a.badPaths.unresolved}` },
    { label: 'index.json tree hashes in sync', ok: a.indexIntegrity.ok, detail: a.indexIntegrity.problems.slice(0, 2).join(' | ') || 'all tree hashes match' },
    { label: 'preset.requires carries index mcp entries', ok: pm.ok, detail: pm.problems.slice(0, 2).join(' | ') || 'in sync' },
  ];

  console.log('== fixup verify ==');
  console.log(`packages             : ${a.counts.packages} (${a.counts.agents} agents / ${a.counts.teams} teams)`);
  console.log(`avatar refs          : ${a.avatarFields.packages}`);
  console.log(`connector refs       : ${a.connectorFields.packages}`);
  console.log(`bare skill refs      : ${a.bareSkillRefs.occurrences}`);
  console.log(`brand words          : ${a.brandWords.total}`);
  console.log(`unresolved ref paths : ${a.badPaths.unresolved}`);
  console.log(`agent-identity kept  : ${a.bareSkillRefs.keptAsAgentIdentity}`);
  console.log('');
  for (const c of checks) console.log(`  ${c.ok ? 'PASS' : 'FAIL'}  ${c.label}  (${c.detail})`);

  const manual = [];
  for (const r of a.missingFrontmatter.rows) {
    manual.push(`(5) ${r.file}: still has no YAML frontmatter (name: ${r.suggestedName})`);
  }
  for (const r of a.badPaths.rows) manual.push(`(4b) ${r.file}:${r.line}: ${r.ref} has no unique target (${r.reason})`);
  for (const r of a.bareSkillRefs.rows) manual.push(`(3) ${r.file}:${r.line}: ${r.from} -> ${r.to} still unrewritten`);
  for (const r of a.brandWords.rows) manual.push(`(4a) ${r.file}:${r.line}: ${r.from} -> ${r.to} still present`);
  for (const r of a.bareSkillRefs.unmatched || []) manual.push(`(3u) ${r.file}:${r.line}: declared skill "${r.name}" maps to no skills/<ns>/ directory`);

  console.log('');
  console.log(`remaining manual items (${manual.length}):`);
  for (const m of manual) console.log(`  - ${m}`);

  const failed = checks.filter((c) => !c.ok);
  if (failed.length) {
    console.error(`\n${failed.length} assertion(s) failed`);
    process.exit(1);
  }
  console.log('\nFIXUP VERIFIED: items 1/2/3/4 and the reference paths are clean.');
}

// ---------------------------------------------------------------- main
if (MODE === '--apply') {
  const log = apply();
  console.log('== fixup apply ==');
  console.log(`plugin.json rewritten : ${log.pluginJson.length} package(s), ${log.pluginJson.reduce((a, r) => a + r.removed.length, 0)} field(s) removed`);
  for (const r of log.pluginJson) console.log(`  ${r.pkg}: ${r.removed.join(', ')}`);
  console.log(`connector -> requires : ${log.mcp.length} package(s)`);
  for (const r of log.mcp) console.log(`  ${r.pkg}: ${JSON.stringify(r.requires)}`);
  console.log(`agents/*.md bare -> ns: ${log.bare.length}`);
  console.log(`frontmatter added     : ${log.frontmatter.length}`);
  for (const r of log.frontmatter) console.log(`  ${r.skill}: name=${r.name} description="${r.description}"`);
  console.log(`reference paths fixed : ${log.refs.length}`);
  console.log(`brand words replaced  : ${log.brand}`);
  for (const r of log.index) console.log(`index.json            : ${r}`);
  console.log('\nnext: node scripts/build-presets.mjs');
} else if (MODE === '--verify') {
  verify();
} else {
  const a = scan();
  const { _index, ...persist } = a;
  fs.writeFileSync(AUDIT_OUT, `${JSON.stringify(persist, null, 2)}\n`, 'utf8');
  printAudit(a);
  console.log(`\nwritten: ${relOf(AUDIT_OUT)}`);
}
