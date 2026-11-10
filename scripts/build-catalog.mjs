#!/usr/bin/env node
/**
 * build-catalog.mjs — morechat.co-Assistant content catalog builder (W5)
 *
 * Source (read-only):  D:/dev/bot
 * Output:
 *   catalog/packages/{agent,team}/<id>/        converted, runtime-agnostic package tree
 *   upstream/packages/{agent,team}/<id>/       byte-identical upstream snapshot (no avatars)
 *   index.json                                 catalog index (schemaVersion 1)
 *
 * Hard rules implemented here:
 *   - avatars/ is never copied (product side generates avatar images).
 *   - .downloaded_at / .DS_Store / __pycache__ / *.pyc are dropped.
 *   - Runtime bindings (WorkBuddy / CodeBuddy / expert-manager / present_files / TeamCreate /
 *     AskUserQuestion / allowed-tools) are rewritten for the Squad/Issue + DSH runtime.
 *   - plugin.json keeps its exact upstream formatting and byte layout except for the
 *     prohibited runtime strings, which are substituted in place; the untouched original
 *     is preserved under upstream/.
 *
 * Node built-ins only. Run:
 *   node scripts/build-catalog.mjs [--src D:/dev/bot] [--root D:/dev/morechat-assistant]
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

// ---------------------------------------------------------------- args
const argv = process.argv.slice(2);
const argOf = (name, dflt) => {
  const i = argv.indexOf(name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
};
const SRC = path.resolve(argOf('--src', 'D:/dev/bot'));
const ROOT = path.resolve(argOf('--root', 'D:/dev/morechat-assistant'));
const CAT = path.join(ROOT, 'catalog');
const UP = path.join(ROOT, 'upstream');
const PKG_OUT = path.join(CAT, 'packages');
const UP_OUT = path.join(UP, 'packages');

const SKIP_DIRS = new Set(['avatars', '__pycache__', '.git', 'node_modules', '.venv']);
const SKIP_FILES = new Set([
  '.downloaded_at',
  '.DS_Store',
  'Thumbs.db',
  // vendor telemetry helper (see stripVendorTelemetry): never distributed
  'skill_track.py',
]);
const SKIP_EXT = new Set(['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.ico', '.pyc', '.zip']);
const BIN_EXT = new Set(['.ttf', '.otf', '.woff', '.woff2', '.pdf', '.pyc']);

// ---------------------------------------------------------------- fs helpers
function walk(dir, base = dir, out = []) {
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
const ensureDir = (d) => fs.mkdirSync(d, { recursive: true });
const sha256 = (buf) => crypto.createHash('sha256').update(buf).digest('hex');

/** Rolling sha256 over files sorted by relative path: relPath \0 bytes \0 ... */
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

const isTextFile = (p, ext) => {
  if (BIN_EXT.has(ext)) return false;
  const fd = fs.openSync(p, 'r');
  const b = Buffer.alloc(8192);
  const n = fs.readSync(fd, b, 0, 8192, 0);
  fs.closeSync(fd);
  return !b.subarray(0, n).includes(0);
};

// ---------------------------------------------------------------- rewrites
const ASK_USER_INLINE = 'dsh-tool-ask-user（ask_user_question）';
const ASK_USER_FULL =
  '使用 dsh-tool-ask-user（ask_user_question）向用户提问；若运行时无该能力，改为在任务评论中提问并等待';
const PRESENT_INLINE = 'dsh-tool-present';
const PRESENT_FULL = '使用 dsh-tool-present 声明交付；在任务评论中作为附件提交';
const TEAM_CREATE = '创建平台小队（Squad）并由 leader 通过 @ 派发子任务';
const CONTENT_DIR = '<MORECHAT_CONTENT_DIR>';

/** Ordered rewrite chain. Every entry targets runtime bindings. */
const REWRITES = [
  // --- tool call rewrites (before generic name scrubbing) ---
  [/\$WORKBUDDY_CONFIG_DIR/g, CONTENT_DIR],
  [/\bWORKBUDDY_CONFIG_DIR\b/g, 'MORECHAT_CONTENT_DIR'],
  // WorkBuddy artifact channel -> dsh present tool
  [/WorkBuddy\s*产物/g, 'dsh-tool-present 交付（作为任务附件）'],
  [/workbuddy\s*产物/g, 'dsh-tool-present 交付（作为任务附件）'],
  // standalone list item / line: tool names in YAML lists
  [/^([ \t]*[-*+][ \t]*)(`?AskUserQuestion`?)[ \t]*$/gm, '$1ask_user_question'],
  [/^([ \t]*[-*+][ \t]*)(`?present_files`?)[ \t]*$/gm, '$1dsh-tool-present'],
  // standalone line == the sole content of the line
  [/^([ \t]*(?:[-*+][ \t]*)?)`?AskUserQuestion`?[ \t]*$/gm, `$1${ASK_USER_FULL}`],
  [/^([ \t]*(?:[-*+][ \t]*)?)`?present_files`?[ \t]*$/gm, `$1${PRESENT_FULL}`],
  // inline occurrences
  [/\bAskUserQuestion\b/g, ASK_USER_INLINE],
  [/\bask_user\b(?!_question)/g, ASK_USER_INLINE],
  [/\bpresent_files\b/g, PRESENT_INLINE],
  [/\bTeamCreate\b/g, TEAM_CREATE],
  // --- runtime home / tooling dirs ---
  [/~\/\.workbuddy/g, CONTENT_DIR],
  [/~\/\.codebuddy/g, CONTENT_DIR],
  [/\.workbuddy/g, '.morechat'],
  [/\.codebuddy-plugin\//g, ''],
  [/\.codebuddy/g, '.morechat'],
  [/codebuddy-plugin/g, 'plugin-dir'],
  [/\bexpert-manager\b/g, 'content-registry'],
  [/\bpackage_expert\.py\b/g, 'build-catalog.mjs'],
  [/\bregister_expert\.py\b/g, 'build-catalog.mjs'],
  // --- product / runtime names ---
  [/\bWorkBuddy\b/g, 'morechat.co'],
  [/\bworkbuddy\b/g, 'morechat.co'],
  [/\bCodeBuddy\b/g, 'morechat.co'],
  [/\bcodebuddy\b/g, 'morechat.co'],
];

/**
 * Upstream `koc-ops-report` ships a vendor telemetry helper that POSTs report
 * bodies to a hardcoded third-party host (http://120.77.156.6:8001) and reports
 * account/client_ip back. Company report content must not leave the tenant, so
 * the section, the helper script and every trace of the endpoint are removed
 * from the distributed copy. The untouched originals live under upstream/.
 */
const TELEMETRY_SECTION =
  /### 五、报告生成后必须做埋点上报[\s\S]*?(?=\n## 输出要求)/;
const TELEMETRY_REPLACEMENT = `### 五、报告生成后直接交付（本目录不做任何上报）

报告写完后，把**绝对路径**交给用户，并在任务评论里以附件形式提交即可。
本目录不分发任何第三方埋点脚本，也不含外部上报地址或密钥；如需公司内部分发登记，按你所在公司的规范另行处理。
`;
const TELEMETRY_LINE =
  /^.*(?:skill_track\.py|SKILL_PROVIDER_|WORKBUDDY_ACCOUNT_ID|120\.77\.156\.6).*$\n?/gm;

function stripVendorTelemetry(text) {
  return text
    .replace(TELEMETRY_SECTION, TELEMETRY_REPLACEMENT)
    .replace(TELEMETRY_LINE, '')
    .replace(/\bWORKBUDDY_([A-Z0-9_]+)/g, 'MORECHAT_$1')
    .replace(/\bSKILL_PROVIDER_([A-Z0-9_]+)/g, 'MORECHAT_REPORT_$1')
    .replace(/\bSKILL_TRACK_([A-Z0-9_]+)/g, 'MORECHAT_REPORT_$1')
    .replace(/120\.77\.156\.6(?::\d+)?/g, '<internal-report-endpoint>')
    .replace(/skill-provider/g, 'report-service');
}

/** Frontmatter tool key rename + tool id mapping (allowed-tools: -> allowed-tools-dsh:). */
function rewriteAllowedTools(text) {
  return text
    .replace(/^([ \t]*)allowed-tools:([^\n]*)$/gm, (_m, indent, rest) => {
      let val = rest;
      val = val.replace(/\bAskUserQuestion\b/g, 'ask_user_question');
      val = val.replace(/\bask_user\b(?!_question)/g, 'ask_user_question');
      val = val.replace(/\bTask\b/g, 'subagent');
      return `${indent}allowed-tools-dsh:${val}`;
    })
    .replace(/^([ \t]*)-[ \t]+Task[ \t]*$/gm, '$1- subagent')
    .replace(/^([ \t]*)-[ \t]+AskUserQuestion[ \t]*$/gm, '$1- ask_user_question');
}

function convertText(text) {
  // allowed-tools mapping first, so the tool id lands as a plain id (ask_user_question)
  // instead of being rewritten into the prose form by the inline rules below.
  let out = stripVendorTelemetry(text);
  out = rewriteAllowedTools(out);
  for (const [re, rep] of REWRITES) out = out.replace(re, rep);
  return out;
}

/** plugin.json: preserve layout, substitute only the prohibited runtime strings. */
function convertPluginJson(text) {
  return stripVendorTelemetry(text)
    .replace(/WorkBuddy/g, 'morechat.co')
    .replace(/CodeBuddy/g, 'morechat.co')
    .replace(/codebuddy/g, 'morechat.co')
    .replace(/workbuddy/g, 'morechat.co');
}

// ---------------------------------------------------------------- README install section
const INSTALL_BLOCK = `## 安装 / Installation

本包由 **morechat.co-Assistant** 内容仓分发，**通过 morechat.co-Assistant 目录导入**：

1. 在 morechat.co-Assistant 仓中取出 \`catalog/packages/<kind>/<id>/\`；
2. 该目录即包根目录，内含 \`plugin.json\`、\`agents/\`、\`skills/\`，整体作为包目录导入；
3. 导入后由平台注册 Agent / Squad 与技能，无需额外安装脚本或注册命令；
4. 头像不在仓内分发（\`avatars/\` 已移除），由产品端生成。
`;
const RUNTIME_BLOCK = `## 运行时适配 / Runtime notes

- 向用户提问：使用 dsh-tool-ask-user（ask_user_question）；运行时无该能力时，改为在任务评论中提问并等待。
- 交付产物：使用 dsh-tool-present 声明交付；在任务评论中作为附件提交。
- 多角色协作：创建平台小队（Squad）并由 leader 通过 @ 派发子任务。
- 工具声明键为 \`allowed-tools-dsh\`（Task → subagent，AskUserQuestion → ask_user_question）。
`;

const LEGACY_LINE = /(WORKBUDDY_CONFIG_DIR|MORECHAT_CONTENT_DIR|plugins\/marketplaces|package_expert|register_expert|expert-manager|plugin install|\/plugin|插件市场|专家中心|解压.{0,6}zip|zip 包路径|\.morechat|marketplaces)/i;
const INSTALL_HEAD = /^#{1,6}[ \t]*(安装|安裝|导入|導入|Install|Installation|打包|分发|分發|获取方式)/i;
const AVATAR_HEAD = /^#{1,6}[ \t]*(头像|頭像|Avatar)/i;
const AVATAR_BODY = `头像不随本内容仓分发（\`avatars/\` 已移除），由产品端生成（grok 引擎）。
`;

function rewriteReadme(text) {
  const lines = text.split('\n');
  const out = [];
  let fence = null;

  // pass 1: drop fenced blocks that hold legacy install commands, drop legacy instruction lines
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const fenceMatch = line.match(/^\s*(```+|~~~+)/);
    if (fenceMatch) {
      if (fence === null) {
        // collect block to decide
        let j = i + 1;
        const body = [];
        while (j < lines.length && !/^\s*(```+|~~~+)/.test(lines[j])) body.push(lines[j++]);
        const blockText = body.join('\n');
        if (LEGACY_LINE.test(blockText) || LEGACY_LINE.test(line)) {
          i = j; // skip whole block incl. closing fence
          continue;
        }
        fence = fenceMatch[1][0];
        out.push(line);
        continue;
      }
      fence = null;
      out.push(line);
      continue;
    }
    if (fence === null && LEGACY_LINE.test(line)) continue; // legacy instruction line
    out.push(line);
  }

  // pass 2: replace install-ish sections with the canonical block
  const secLines = out;
  const res = [];
  let replaced = false;
  for (let i = 0; i < secLines.length; i++) {
    const line = secLines[i];
    const h = line.match(/^(#{1,6})\s/);
    if (h && AVATAR_HEAD.test(line)) {
      const level = h[1].length;
      let j = i + 1;
      while (j < secLines.length) {
        const h2 = secLines[j].match(/^(#{1,6})\s/);
        if (h2 && h2[1].length <= level) break;
        j++;
      }
      res.push(line, '', AVATAR_BODY.trimEnd(), '');
      i = j - 1;
      continue;
    }
    if (h && INSTALL_HEAD.test(line)) {
      const level = h[1].length;
      let j = i + 1;
      while (j < secLines.length) {
        const h2 = secLines[j].match(/^(#{1,6})\s/);
        if (h2 && h2[1].length <= level) break;
        j++;
      }
      if (!replaced) {
        res.push(INSTALL_BLOCK.trimEnd());
        replaced = true;
      }
      i = j - 1;
      continue;
    }
    res.push(line);
  }
  const body = res.join('\n');

  if (!replaced) {
    // insert canonical install block right after the first H1
    const idx = body.search(/^#\s/m);
    if (idx >= 0) {
      const lineEnd = body.indexOf('\n', idx);
      const head = lineEnd < 0 ? body : body.slice(0, lineEnd + 1);
      const tail = lineEnd < 0 ? '' : body.slice(lineEnd + 1);
      return `${head}\n${INSTALL_BLOCK}\n${RUNTIME_BLOCK}\n${tail}`;
    }
    return `${INSTALL_BLOCK}\n${RUNTIME_BLOCK}\n${body}`;
  }
  return body;
}

// ---------------------------------------------------------------- skill discovery
function frontmatterName(mdPath) {
  let head = '';
  try {
    head = fs.readFileSync(mdPath, 'utf8').slice(0, 4000);
  } catch {
    return null;
  }
  const fm = head.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!fm) return null;
  const m = fm[1].match(/^name:\s*["']?([^"'\r\n]+)["']?\s*$/m);
  return m ? m[1].trim() : null;
}

function discoverSkills(pkgDir) {
  const skillsRoot = path.join(pkgDir, 'skills');
  if (!fs.existsSync(skillsRoot)) return [];
  const all = walk(skillsRoot, pkgDir); // rel is package-relative
  const skillMd = all.filter((f) => path.basename(f.rel) === 'SKILL.md');
  const dirs = skillMd.map((f) => f.rel.slice(0, -'SKILL.md'.length).replace(/\/$/, ''));
  const skills = dirs.map((relDir) => ({
    relDir, // e.g. skills/deep-research/research
    name: frontmatterName(path.join(pkgDir, relDir, 'SKILL.md')) || path.basename(relDir),
    files: [],
  }));
  // partition: a file belongs to the deepest skill dir that contains it
  for (const f of all) {
    let owner = null;
    for (const s of skills) {
      if (f.rel === `${s.relDir}/SKILL.md`) { owner = s; break; }
      if (f.rel.startsWith(`${s.relDir}/`) && (!owner || s.relDir.length > owner.relDir.length)) owner = s;
    }
    if (owner) owner.files.push(f);
    else skills[0]?.files.push(f);
  }
  return skills;
}

const slug = (s) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/-{2,}/g, '-')
    .replace(/^-|-$/g, '');

// ---------------------------------------------------------------- main
const report = { agents: 0, teams: 0, skills: 0, files: 0, bytes: 0, srcBytes: 0 };
const packages = [];
const usedNs = new Set();

function copyPackage(kind, id) {
  const srcDir = path.join(SRC, kind === 'agent' ? 'bot' : 'team', id);
  const pluginPath = path.join(srcDir, '.codebuddy-plugin', 'plugin.json');
  if (!fs.existsSync(pluginPath)) return null;
  const pluginRaw = fs.readFileSync(pluginPath);
  const plugin = JSON.parse(pluginRaw.toString('utf8'));

  const catalogDir = path.join(PKG_OUT, kind, id);
  const upstreamDir = path.join(UP_OUT, kind, id);
  ensureDir(catalogDir);
  ensureDir(upstreamDir);

  const srcFiles = walk(srcDir, srcDir);
  for (const f of srcFiles) report.srcBytes += fs.statSync(f.abs).size;

  // 1) upstream snapshot (verbatim, no avatars)
  for (const f of srcFiles) {
    const dst = path.join(upstreamDir, f.rel);
    ensureDir(path.dirname(dst));
    fs.copyFileSync(f.abs, dst);
  }
  // upstream keeps plugin.json at plugin/plugin.json (dir name is itself a binding)
  ensureDir(path.join(upstreamDir, 'plugin'));
  fs.writeFileSync(path.join(upstreamDir, 'plugin', 'plugin.json'), pluginRaw);

  // 2) converted catalog tree
  const skills = discoverSkills(srcDir);
  const skillNs = new Map(); // relDir -> physical dir name
  const takenInPkg = new Set();
  for (const s of skills) {
    let ns = `${slug(id)}--${slug(s.name)}`;
    if (takenInPkg.has(ns)) ns = `${slug(id)}--${slug(s.relDir.replace(/^skills\//, ''))}`;
    let n = 2;
    while (takenInPkg.has(ns) || usedNs.has(`${kind}:${ns}`)) ns = `${slug(id)}--${slug(s.relDir.replace(/^skills\//, ''))}-${n++}`;
    takenInPkg.add(ns);
    usedNs.add(`${kind}:${ns}`);
    skillNs.set(s.relDir, ns);
  }

  const outFiles = [];
  for (const f of srcFiles) {
    if (f.rel === '.codebuddy-plugin/plugin.json') continue;
    // locate owning skill
    let ns = null;
    for (const s of skills) {
      if (f.rel.startsWith(`${s.relDir}/`)) {
        if (!ns || s.relDir.length > ns.length) ns = s.relDir;
      }
    }
    let rel;
    if (ns) rel = `skills/${skillNs.get(ns)}/${f.rel.slice(ns.length + 1)}`;
    else rel = f.rel;
    const dst = path.join(catalogDir, rel);
    ensureDir(path.dirname(dst));
    const text = isTextFile(f.abs, f.ext);
    if (!text) {
      fs.copyFileSync(f.abs, dst);
    } else {
      let s = fs.readFileSync(f.abs, 'utf8');
      s = convertText(s);
      if (rel === 'README.md' || (rel.endsWith('/README.md') && !rel.startsWith('skills/'))) s = rewriteReadme(s);
      fs.writeFileSync(dst, s, 'utf8');
    }
    outFiles.push({ rel, abs: dst });
  }
  // plugin.json (converted in place, layout preserved) — except the skills
  // list: upstream paths (./skills/<name>) do not exist in catalog/, where
  // every skill directory is namespaced. Leaving them would make any importer
  // that trusts plugin.json resolve zero skills.
  let convertedPlugin = convertPluginJson(pluginRaw.toString('utf8'));
  const namespacedSkills = skills.map((s) => './skills/' + skillNs.get(s.relDir));
  // Parse → set → re-serialize: a regex over upstream formatting was fragile
  // (the array did not get rewritten), and the upstream byte copy already lives
  // in upstream/. The catalog copy only has to be valid JSON with real paths.
  const pluginObj = JSON.parse(convertedPlugin);
  pluginObj.skills = namespacedSkills;
  const finalPlugin = JSON.stringify(pluginObj, null, 2) + '\n';  if (process.env.DEBUG_PLUGIN) console.error('DBG', kind, id, 'skills', skills.length, 'ns', namespacedSkills.slice(0,2));
  fs.writeFileSync(path.join(catalogDir, 'plugin.json'), finalPlugin, 'utf8');
  outFiles.push({ rel: 'plugin.json', abs: path.join(catalogDir, 'plugin.json') });

  // 3) index entry
  const skillEntries = [];
  for (const s of skills) {
    const ns = skillNs.get(s.relDir);
    const dirAbs = path.join(catalogDir, 'skills', ns);
    const sfiles = walk(dirAbs, dirAbs);
    const bytes = sfiles.reduce((a, f) => a + fs.statSync(f.abs).size, 0);
    skillEntries.push({
      name: s.name,
      ns,
      path: `skills/${ns}`,
      files: sfiles.length,
      bytes,
      sha256: treeSha256(sfiles),
    });
    report.skills++;
  }
  skillEntries.sort((a, b) => (a.ns < b.ns ? -1 : 1));

  const exts = new Set(outFiles.map((f) => path.extname(f.rel).toLowerCase()));
  const requires = [];
  if (exts.has('.py')) requires.push('python');
  if (exts.has('.mjs')) requires.push('node');
  if (exts.has('.ttf')) requires.push('canvas');

  const totalBytes = outFiles.reduce((a, f) => a + fs.statSync(f.abs).size, 0);
  report.files += outFiles.length;
  report.bytes += totalBytes;
  report[kind === 'agent' ? 'agents' : 'teams']++;

  const tags = Array.isArray(plugin.tags) ? plugin.tags : [];
  const entry = {
    id,
    kind,
    name: {
      zh: plugin.displayName?.zh || plugin.profession?.zh || id,
      en: plugin.displayName?.en || plugin.profession?.en || id,
    },
    profession: {
      zh: plugin.profession?.zh || '',
      en: plugin.profession?.en || '',
    },
    description: plugin.displayDescription?.en || plugin.description || '',
    descriptionZh: plugin.displayDescription?.zh || '',
    version: plugin.version || '',
    path: `packages/${kind}/${id}`,
    files: outFiles.length,
    bytes: totalBytes,
    sha256: treeSha256(outFiles),
    skills: skillEntries,
    requires,
    tags,
    categoryId: plugin.categoryId || '',
  };
  if (kind === 'team') {
    entry.leadAgent = plugin.teamInfo?.leadAgent || plugin.agentName || '';
    entry.members = (plugin.members || []).map((m) => ({
      id: m.id,
      name: { zh: m.name?.zh || '', en: m.name?.en || '' },
      profession: { zh: m.profession?.zh || '', en: m.profession?.en || '' },
      role: m.role || (m.id === entry.leadAgent ? 'lead' : 'member'),
    }));
  }
  return entry;
}

// clean outputs
for (const d of [CAT, UP]) fs.rmSync(d, { recursive: true, force: true });
ensureDir(PKG_OUT);
ensureDir(UP_OUT);

const agentIds = fs.readdirSync(path.join(SRC, 'bot'), { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name).sort();
const teamIds = fs.readdirSync(path.join(SRC, 'team'), { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name).sort();

for (const id of agentIds) {
  const e = copyPackage('agent', id);
  if (e) packages.push(e);
  else console.warn(`skip agent ${id}: no plugin.json`);
}
for (const id of teamIds) {
  const e = copyPackage('team', id);
  if (e) packages.push(e);
  else console.warn(`skip team ${id}: no plugin.json`);
}

// duplicate skill names across the whole catalog (namespaced by pkg)
const nameCount = new Map();
for (const p of packages) for (const s of p.skills) nameCount.set(s.name, (nameCount.get(s.name) || 0) + 1);
const dupNames = [...nameCount.entries()].filter(([, c]) => c > 1).map(([n, c]) => ({ name: n, count: c })).sort((a, b) => a.name.localeCompare(b.name));

const index = {
  schemaVersion: 1,
  generator: 'morechat-assistant/scripts/build-catalog.mjs',
  generatedAt: new Date().toISOString(),
  source: { catalogRoot: 'catalog', upstreamRoot: 'upstream', sourceRepo: 'D:/dev/bot' },
  avatarPolicy: 'avatars are not distributed; generated product-side',
  hashAlgorithm: 'sha256 over files sorted by relative path, fed as relPath\\0 content \\0',
  stats: {
    packages: packages.length,
    agents: report.agents,
    teams: report.teams,
    skills: report.skills,
    files: report.files,
    bytes: report.bytes,
    sourceBytes: report.srcBytes,
    duplicateSkillNames: dupNames,
  },
  packages,
};
fs.writeFileSync(path.join(ROOT, 'index.json'), `${JSON.stringify(index, null, 2)}\n`, 'utf8');

const perPkg = packages.map((p) => `${p.kind}/${p.id}\t${p.skills.length} skills\t${p.files} files\t${(p.bytes / 1048576).toFixed(2)} MiB\trequires=${p.requires.join(',') || '-'}`);
console.log(perPkg.join('\n'));
console.log('---');
console.log(`packages=${packages.length} agents=${report.agents} teams=${report.teams} skills=${report.skills} files=${report.files}`);
console.log(`bytes=${report.bytes} (${(report.bytes / 1048576).toFixed(2)} MiB)  sourceBytes(incl avatars)=${report.srcBytes} (${(report.srcBytes / 1048576).toFixed(2)} MiB)`);
console.log(`duplicate skill names: ${dupNames.map((d) => `${d.name}x${d.count}`).join(', ') || 'none'}`);
