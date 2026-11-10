#!/usr/bin/env node
/**
 * build-presets.mjs — generate the preset layer of the morechat.co-Assistant content catalog.
 *
 * Input (read-only):
 *   index.json                                  package index (schemaVersion 1)
 *   catalog/packages/<kind>/<id>/plugin.json     quickPrompts / defaultInitPrompt / agents / teamInfo
 *   catalog/packages/<kind>/<id>/agents/*.md     persona markdown
 *   catalog/packages/<kind>/<id>/skills/**       skill bundles (mounted, never inlined)
 *
 * Output (this script is the only writer of these files):
 *   presets/<kind>/<id>.preset.json   Multica-facing, whitelisted fields only
 *   presets/<kind>/<id>.cordis.yml    DSH-facing Cordis patch fragment
 *
 * Hard rules encoded below:
 *   - No model / provider / apiKey / secret / token / permission / role field is ever emitted.
 *   - conversationStarters <= 3, taken from plugin.json quickPrompts[].zh, then
 *     defaultInitPrompt.zh, then [].
 *   - contentSha256 is copied from index.json (tree hash of the package directory).
 *   - Idempotent: identical input produces byte-identical output (LF, stable key order).
 *
 * Node built-ins only. No dependencies.
 *
 * Usage:
 *   node scripts/build-presets.mjs            # write / refresh presets/**
 *   node scripts/build-presets.mjs --check    # verify on-disk presets match the generator (exit 1 on drift)
 *   node scripts/build-presets.mjs <root>     # operate on another checkout
 */
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const CHECK_ONLY = args.includes('--check');
const ROOT = path.resolve(args.find((a) => !a.startsWith('--')) || '.');

const INDEX_PATH = path.join(ROOT, 'index.json');
const PRESETS_DIR = path.join(ROOT, 'presets');
const MAX_STARTERS = 3;

/**
 * A preset may describe content and composition only. Anything that pins a model,
 * a provider, a credential, or an authorization surface belongs to the host profile.
 */
const FORBIDDEN_PRESET_KEY = /model|provider|api[_-]?key|secret|token|permission|role/i;
const PRESET_TOP_FIELDS = [
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
];

const warnings = [];
const notices = [];
const warn = (id, msg) => warnings.push(`${id}: ${msg}`);
const note = (id, msg) => notices.push(`${id}: ${msg}`);

const str = (v) => (typeof v === 'string' && v.trim() ? v.trim() : null);
const toPosix = (p) => p.split(path.sep).join('/');
const yamlScalar = (v) => JSON.stringify(String(v)); // JSON string literals are valid YAML scalars
const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));

// ---------------------------------------------------------------- field pickers

function resolveName(pkg, plugin, id) {
  const pick = (v) => (typeof v === 'string' ? str(v) : v && typeof v === 'object' ? str(v.zh) || str(v.en) : null);
  const zhOf = (v) => (typeof v === 'string' ? str(v) : v && typeof v === 'object' ? str(v.zh) : null);
  const enOf = (v) => (typeof v === 'string' ? str(v) : v && typeof v === 'object' ? str(v.en) : null);
  const zh = zhOf(pkg.name) || zhOf(plugin.displayName) || zhOf(plugin.profession) || pick(pkg.profession) || id;
  const en = enOf(pkg.name) || enOf(plugin.displayName) || enOf(plugin.profession) || str(pkg.profession) || id;
  if (!zhOf(pkg.name) || !enOf(pkg.name)) warn(id, 'index.json name{zh,en} incomplete -> filled from plugin.json / id');
  return { zh, en };
}

function resolveDescription(pkg, plugin, id) {
  const asText = (v) =>
    typeof v === 'string' ? str(v) : v && typeof v === 'object' ? str(v.zh) || str(v.en) : null;
  const desc =
    asText(pkg.descriptionZh) ||
    str(pkg.description) ||
    asText(plugin.displayDescription) ||
    str(plugin.description) ||
    '';
  if (!desc) warn(id, 'no description found -> description = ""');
  return desc;
}

function resolveStarters(plugin, id) {
  const out = [];
  const quick = Array.isArray(plugin.quickPrompts) ? plugin.quickPrompts : [];
  for (const item of quick) {
    const zh = str(typeof item === 'string' ? item : item && item.zh);
    if (zh && !out.includes(zh)) out.push(zh);
    if (out.length >= MAX_STARTERS) break;
  }
  if (out.length) {
    if (quick.length > out.length) note(id, `quickPrompts ${quick.length} -> conversationStarters ${out.length} (cap ${MAX_STARTERS})`);
    return out;
  }
  const dip = str(
    typeof plugin.defaultInitPrompt === 'string' ? plugin.defaultInitPrompt : plugin.defaultInitPrompt && plugin.defaultInitPrompt.zh,
  );
  if (dip) {
    warn(id, 'plugin.json quickPrompts missing/empty -> conversationStarters from defaultInitPrompt.zh');
    return [dip];
  }
  warn(id, 'no quickPrompts and no defaultInitPrompt -> conversationStarters = []');
  return [];
}

function resolvePersona(pkgDir, pkgRel, plugin, id) {
  const candidates = [];
  for (const rel of Array.isArray(plugin.agents) ? plugin.agents : []) {
    if (typeof rel !== 'string') continue;
    const norm = rel.replace(/\\/g, '/').replace(/^\.?\//, '');
    if (norm.startsWith('agents/') && norm.endsWith('.md')) candidates.push(norm);
  }
  if (str(plugin.agentName)) candidates.push(`agents/${str(plugin.agentName)}.md`);
  candidates.push(`agents/${id}.md`);

  for (const c of candidates) {
    if (fs.existsSync(path.join(pkgDir, c))) return `${pkgRel}/${c}`;
  }
  const agentDir = path.join(pkgDir, 'agents');
  const discovered = fs.existsSync(agentDir)
    ? fs
        .readdirSync(agentDir, { withFileTypes: true })
        .filter((e) => e.isFile() && e.name.endsWith('.md'))
        .map((e) => e.name)
        .sort()
    : [];
  if (discovered.length) {
    warn(id, `plugin.json agents[] did not resolve on disk -> personaPath from agents/${discovered[0]}`);
    return `${pkgRel}/agents/${discovered[0]}`;
  }
  warn(id, 'no persona markdown under agents/ -> personaPath = ""');
  return '';
}

function resolveSkills(pkg, pkgDir, plugin, id) {
  const listed = Array.isArray(pkg.skills) ? pkg.skills : [];
  const ns = [];
  for (const s of listed) {
    const n = str(s && s.ns);
    if (!n) {
      warn(id, 'index skill entry without ns -> skipped');
      continue;
    }
    if (!ns.includes(n)) ns.push(n);
    if (!fs.existsSync(path.join(pkgDir, 'skills', n))) warn(id, `skill directory missing on disk: skills/${n}`);
  }
  const declared = Array.isArray(plugin.skills) ? plugin.skills.filter((s) => typeof s === 'string').length : 0;
  if (!ns.length) {
    if (declared) warn(id, `index skills empty while plugin.json declares ${declared} -> skills = []`);
    else warn(id, 'package ships no skills -> skills = []');
  }
  return ns;
}

function resolveTeam(pkg, plugin, personaPath, id) {
  const teamInfo = plugin.teamInfo && typeof plugin.teamInfo === 'object' ? plugin.teamInfo : null;
  const lead = str(teamInfo && teamInfo.leadAgent) || str(plugin.agentName) || (personaPath ? path.basename(personaPath, '.md') : id);

  let raw = [];
  if (teamInfo && Array.isArray(teamInfo.memberAgents)) raw = teamInfo.memberAgents;
  else if (Array.isArray(plugin.members)) raw = plugin.members.map((m) => (typeof m === 'string' ? m : m && m.id));
  if (!raw.length) {
    raw = (Array.isArray(plugin.agents) ? plugin.agents : [])
      .filter((a) => typeof a === 'string' && a.endsWith('.md'))
      .map((a) => path.basename(a.replace(/\\/g, '/'), '.md'));
  }
  const members = [];
  for (const m of raw) {
    const s = str(m);
    if (s && s !== lead && !members.includes(s)) members.push(s);
  }
  if (!lead) warn(id, 'team.leadAgent unresolved -> ""');
  if (!members.length) note(id, 'single-agent package -> team.members = []');
  return { leadAgent: lead, members };
}

function resolveRequires(pkg, id) {
  if (!Array.isArray(pkg.requires)) {
    warn(id, 'index.json requires missing -> requires = []');
    return [];
  }
  const out = [];
  for (const r of pkg.requires) {
    const s = str(r);
    if (s && !out.includes(s.toLowerCase())) out.push(s.toLowerCase());
  }
  return out;
}

// ---------------------------------------------------------------- preset.json

function buildPreset(pkg, order) {
  const id = str(pkg.id);
  const kind = str(pkg.kind);
  if (!id) throw new Error('index.json package without id');
  if (kind !== 'agent' && kind !== 'team') throw new Error(`${id}: unsupported kind ${JSON.stringify(pkg.kind)}`);

  const pkgRelIndex = str(pkg.path) ? toPosix(str(pkg.path)) : null;
  const pkgRel = pkgRelIndex ? `catalog/${pkgRelIndex}` : `catalog/packages/${kind}/${id}`;
  if (!pkgRelIndex) warn(id, 'index.json path missing -> derived from kind/id');
  const pkgDir = path.join(ROOT, pkgRel);

  let plugin = {};
  const pluginPath = path.join(pkgDir, 'plugin.json');
  if (fs.existsSync(pluginPath)) {
    try {
      plugin = readJson(pluginPath);
    } catch (e) {
      warn(id, `plugin.json is not valid JSON (${e.message}) -> defaults used`);
    }
  } else {
    warn(id, `${pkgRel}/plugin.json missing -> defaults used`);
  }

  const sha = str(pkg.sha256);
  if (!sha) warn(id, 'index.json sha256 missing -> contentSha256 = ""');
  const version = str(pkg.version) || str(plugin.version);
  if (!str(pkg.version)) warn(id, 'index.json version missing -> packageVersion from plugin.json / ""');

  const personaPath = resolvePersona(pkgDir, pkgRel, plugin, id);
  const preset = {
    schemaVersion: 1,
    id,
    kind,
    name: resolveName(pkg, plugin, id),
    description: resolveDescription(pkg, plugin, id),
    personaPath,
    skills: resolveSkills(pkg, pkgDir, plugin, id),
    conversationStarters: resolveStarters(plugin, id),
    team: resolveTeam(pkg, plugin, personaPath, id),
    requires: resolveRequires(pkg, id),
    sourcePackage: pkgRel,
    packageVersion: version || '',
    contentSha256: sha || '',
  };

  assertWhitelisted(preset, id);
  return { preset, order, pkgDir, pkgRel };
}

function assertWhitelisted(value, id, trail = '') {
  if (Array.isArray(value)) return;
  if (!value || typeof value !== 'object') return;
  for (const [k, v] of Object.entries(value)) {
    if (FORBIDDEN_PRESET_KEY.test(k)) throw new Error(`${id}: forbidden preset field "${trail}${k}"`);
    if (!trail && !PRESET_TOP_FIELDS.includes(k)) throw new Error(`${id}: field "${k}" is not on the preset whitelist`);
    if (trail === 'team.' && !['leadAgent', 'members'].includes(k)) throw new Error(`${id}: field "team.${k}" is not on the preset whitelist`);
    assertWhitelisted(v, id, trail + k + '.');
  }
}

// ---------------------------------------------------------------- cordis.yml

function buildCordis(preset, order) {
  const skillsRoot = `${preset.sourcePackage}/skills`;
  const hasSkills = preset.skills.length > 0;
  const L = [];
  const push = (s = '') => L.push(s);

  push('# 由 build-presets.mjs 生成，勿手改。');
  push('# Generated by scripts/build-presets.mjs — do not edit by hand.');
  push('#');
  push(`# package      : ${preset.kind}/${preset.id} v${preset.packageVersion}`);
  push(`# source       : ${preset.sourcePackage}`);
  push(`# persona      : ${preset.personaPath || '(package ships no persona markdown)'}`);
  push(`# skills root  : ${hasSkills ? `${skillsRoot} (${preset.skills.length} bundle(s))` : '(package ships no skills)'}`);
  push(`# contentSha256: ${preset.contentSha256}`);
  push('#');
  push('# DSH side of the preset layer: one @deepseek-ai/dsh-agent-preset declaration, shaped like');
  push('# @deepseek-ai/dsh-web-app/presets/standard.patch.yml. It injects the package persona and the');
  push('# workspace instruction chain, mounts the package skills root, and makes ask_user_question');
  push('# timed. No model, provider, credential, permission or role field is written here on purpose:');
  push('# the host profile owns those, and a preset must never pin them.');
  push('# Apply as a Cordis patch fragment on top of the profile patch. Relative paths resolve from');
  push('# the root of this content repo (the checkout that contains catalog/ and presets/).');
  push('');
  push('- insert:');
  push(`    - id: ${preset.id}-preset`);
  push("      name: '@deepseek-ai/dsh-agent-preset'");
  push('      config:');
  push(`        id: ${yamlScalar(preset.id)}`);
  push(`        order: ${order}`);
  push(`        name: ${yamlScalar(preset.name.zh)}`);
  push(`        description: ${yamlScalar(preset.description)}`);
  push('        plugins:');
  // persona
  push('          - id: persona');
  push("            name: '@deepseek-ai/dsh-persona'");
  push('            config:');
  push('              prefix: |-');
  for (const line of personaPrefixLines(preset)) push(`                ${line}`.replace(/\s+$/, ''));
  // instructions
  push('          - id: agent-instructions');
  push("            name: '@deepseek-ai/dsh-agent-instructions'");
  push('            config:');
  push('              maxBytes: 65536');
  // time context
  push('          - id: time-context');
  push("            name: '@deepseek-ai/dsh-time-context'");
  // fs tools
  push('          - id: tool-bash');
  push("            name: '@deepseek-ai/dsh-tool-bash'");
  push("            disabled: !!js process.platform === 'win32'");
  push('          - id: tool-pwsh');
  push("            name: '@deepseek-ai/dsh-tool-pwsh'");
  push("            disabled: !!js process.platform !== 'win32'");
  push('          - id: tool-fs');
  push("            name: '@deepseek-ai/dsh-tool-fs'");
  push('            config:');
  push('              applyPatch: false');
  push('          - id: tool-fs-search');
  push("            name: '@deepseek-ai/dsh-tool-fs-search'");
  // skills
  push('          - id: skill-filesystem');
  push("            name: '@deepseek-ai/dsh-skill-filesystem'");
  push('            config:');
  push('              includeDefaultRoots: true');
  if (hasSkills) {
    push('              # Package skills live one level down (<root>/<ns>/SKILL.md), which is exactly');
    push('              # what this provider discovers; default project/user roots stay enabled.');
    push('              customSkillDirs:');
    push(`                - ${skillsRoot}`);
  } else {
    push('              # This package ships no skills; keep the default roots only.');
    push('              customSkillDirs: []');
  }
  push('          - id: tool-skill');
  push("            name: '@deepseek-ai/dsh-tool-skill'");
  // user interaction
  push('          - id: tool-ask-user');
  push("            name: '@deepseek-ai/dsh-tool-ask-user'");
  push('            config:');
  push('              mode: timed');
  push('              timeout: 120');
  // mild extras from the standard skeleton
  push('          - id: tool-todo');
  push("            name: '@deepseek-ai/dsh-tool-todo'");
  push('          - id: present');
  push("            name: '@deepseek-ai/dsh-tool-present'");
  push('');
  return L.join('\n');
}

function personaPrefixLines(preset) {
  const { name, id, kind, description, personaPath, sourcePackage } = preset;
  const out = [];
  out.push(`You are ${name.zh} (${name.en}), the packaged persona of the ${kind} preset \`${id}\`.`);
  out.push(`Scope: ${description}`);
  if (personaPath) {
    out.push(
      `Your authoritative identity, tone and workflow live in \`${personaPath}\`. Read that file, plus every other file under \`${sourcePackage}/agents/\`, before your first answer, and keep following it for the rest of the conversation.`,
    );
  } else {
    out.push(
      `This package ships no persona markdown; derive identity and workflow from the scope line above and the mounted skills, and say so if the user asks for details the package does not carry.`,
    );
  }
  if (preset.skills.length) {
    out.push(
      `The package ships ${preset.skills.length} skill bundle(s) mounted from \`${sourcePackage}/skills\`. Load one with the \`skill\` tool whenever its description matches the task, and prefer it over improvised procedure.`,
    );
  } else {
    out.push(`This package ships no skill bundles; work from the persona and the standard tools.`);
  }
  out.push(
    `Stay inside this package's scope. When a request needs a capability the package does not carry, name the package or skill that would, instead of inventing a workflow.`,
  );
  out.push(`Answer in the user's language and keep output operational: steps, commands, deliverables.`);
  return out;
}

// ---------------------------------------------------------------- io

function writeIfChanged(abs, content) {
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  if (fs.existsSync(abs) && fs.readFileSync(abs, 'utf8') === content) return 'unchanged';
  fs.writeFileSync(abs, content, 'utf8');
  return 'written';
}

function main() {
  if (!fs.existsSync(INDEX_PATH)) throw new Error('index.json not found at repo root');
  const index = readJson(INDEX_PATH);
  if (index.schemaVersion !== 1) throw new Error(`index.json schemaVersion is ${index.schemaVersion}, expected 1`);
  if (!Array.isArray(index.packages) || !index.packages.length) throw new Error('index.json packages[] is empty');

  const expected = new Set();
  const rows = [];
  let written = 0;
  let unchanged = 0;
  let drift = 0;

  index.packages.forEach((pkg, i) => {
    const order = i + 1;
    const { preset } = buildPreset(pkg, order);
    const dir = toPosix(path.posix.join('presets', preset.kind));
    const jsonRel = `${dir}/${preset.id}.preset.json`;
    const ymlRel = `${dir}/${preset.id}.cordis.yml`;
    expected.add(jsonRel);
    expected.add(ymlRel);

    const jsonText = JSON.stringify(preset, null, 2) + '\n';
    const ymlText = buildCordis(preset, order);

    if (CHECK_ONLY) {
      for (const [rel, text] of [
        [jsonRel, jsonText],
        [ymlRel, ymlText],
      ]) {
        const abs = path.join(ROOT, rel);
        if (!fs.existsSync(abs)) {
          drift++;
          console.error(`drift: missing ${rel} (run node scripts/build-presets.mjs)`);
        } else if (fs.readFileSync(abs, 'utf8') !== text) {
          drift++;
          console.error(`drift: ${rel} differs from generator output (run node scripts/build-presets.mjs)`);
        }
      }
    } else {
      for (const [rel, text] of [
        [jsonRel, jsonText],
        [ymlRel, ymlText],
      ]) {
        const r = writeIfChanged(path.join(ROOT, rel), text);
        if (r === 'written') written++;
        else unchanged++;
      }
    }
    rows.push({ id: preset.id, kind: preset.kind, skills: preset.skills.length, starters: preset.conversationStarters.length });
  });

  // prune stale artifacts so regeneration is a full reconciliation, not an append
  let pruned = 0;
  for (const kind of ['agent', 'team']) {
    const dir = path.join(PRESETS_DIR, kind);
    if (!fs.existsSync(dir)) continue;
    for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!ent.isFile()) continue;
      if (!/\.(preset\.json|cordis\.yml)$/.test(ent.name)) continue;
      const rel = toPosix(path.posix.join('presets', kind, ent.name));
      if (expected.has(rel)) continue;
      if (CHECK_ONLY) {
        drift++;
        console.error(`drift: stale ${rel} has no index.json package`);
      } else {
        fs.unlinkSync(path.join(dir, ent.name));
        pruned++;
      }
    }
  }

  const agents = rows.filter((r) => r.kind === 'agent').length;
  const teams = rows.filter((r) => r.kind === 'team').length;
  const noSkills = rows.filter((r) => r.skills === 0).length;
  const capped = rows.filter((r) => r.starters === MAX_STARTERS).length;
  const empty = rows.filter((r) => r.starters === 0).length;

  if (notices.length && !CHECK_ONLY) {
    console.log(`\nnotices (${notices.length}):`);
    for (const n of notices) console.log(`  ~ ${n}`);
  }
  if (warnings.length && !CHECK_ONLY) {
    console.log(`\nwarnings (${warnings.length}) — defaults applied:`);
    for (const w of warnings) console.log(`  ! ${w}`);
  }

  console.log(`\n== presets ==`);
  console.log(`packages     : ${rows.length} (${agents} agents / ${teams} teams)`);
  console.log(`files        : ${rows.length * 2} (${rows.length} preset.json + ${rows.length} cordis.yml)`);
  console.log(`skills       : ${rows.reduce((a, r) => a + r.skills, 0)} mounted, ${noSkills} package(s) without skills`);
  console.log(`starters     : ${capped} package(s) at the ${MAX_STARTERS}-item cap, ${empty} empty`);
  if (CHECK_ONLY) {
    if (drift) {
      console.error(`\n${drift} preset drift(s) — presets/** is out of sync with the generator.`);
      process.exit(1);
    }
    console.log(`\npresets are in sync with index.json and catalog content`);
  } else {
    console.log(`written      : ${written} file(s) (${unchanged} already up to date, ${pruned} stale pruned)`);
  }
}

main();
