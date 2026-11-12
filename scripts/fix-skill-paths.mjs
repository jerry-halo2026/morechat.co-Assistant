"use strict";
// Rewrites the package-relative paths inside agent briefs into skill names.
//
// The briefs were written for a host whose package directory was the working
// directory, so they address a skill's files as `../skills/<ns>/references/x.md`.
// After import the skill lives at `{workdir}/.dsh/skills/<ns>/`, and there is no
// `../skills/` to walk up into - the agent reading the brief would look for a path
// that cannot exist. Naming the skill instead of the path survives every host.
//
// Usage: node scripts/fix-skill-paths.mjs [--apply]
import fs from "node:fs";
import path from "node:path";

const APPLY = process.argv.includes("--apply");
const ROOT = "catalog/packages";

// `<SKILL_ROOT>../skills/<ns>/<rest>` and `@../skills/<ns>/<rest>` and the bare form.
// Three shapes seen in the tree:
//   <SKILL_ROOT>../skills/<ns>/<rest>   (agent briefs, walking up into the package)
//   <SKILL_ROOT>/skills/<ns>/<rest>     (agent briefs, the other spelling)
//   <SKILL_ROOT>/<rest>                 (inside a skill's own references, already correct
//                                        once the placeholder is gone)
const PATTERN = /(?:<SKILL_ROOT>|@)?(?:\.\.\/skills\/([a-z0-9-]+--[a-z0-9-]+)|<SKILL_ROOT>\/skills\/([a-z0-9-]+--[a-z0-9-]+)|<SKILL_ROOT>)\/([^\s`'")\],，。；]+)/g;

/** A line that runs something: the path has to stay executable, not become prose. */
const COMMAND_LINE = /^\s*(?:[-*|]\s*)?(?:python3?|node|bash|sh|npx|cd|\.\/)/;

function rewriteLine(line) {
  if (COMMAND_LINE.test(line)) {
    // `python <SKILL_ROOT>../skills/<ns>/scripts/x.py` becomes an instruction to run
    // the same file from inside the skill's own directory, which is where every host
    // puts a skill's files.
    const ns = line.match(/\.\.\/skills\/([a-z0-9-]+--[a-z0-9-]+)\//)?.[1];
    if (ns) {
      const command = line.replace(/<SKILL_ROOT>|\.\.\/skills\/[a-z0-9-]+--[a-z0-9-]+\//g, "").trim();
      const indent = line.match(/^\s*/)?.[0] ?? "";
      return `${indent}在 \`${ns}\` 技能目录下执行：\`${command}\``;
    }
  }
  return line.replace(PATTERN, (match, nsA, nsB, rest, offset, whole) => {
    const ns = nsA ?? nsB ?? null;
    // Already inside a code span? Then the span supplies the formatting and adding
    // our own backticks would nest them.
    const before = whole[offset - 1];
    const after = whole[offset + match.length];
    if (!ns) return match.replace(/^<SKILL_ROOT>\//, "");
    if (before === "`" && after === "`") return `${ns} 技能的 ${rest}`;
    return `\`${ns}\` 技能的 \`${rest}\``;
  });
}

let files = 0;
let lines = 0;
const touched = [];

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full);
    else if (entry.name.endsWith(".md") && full.includes(`${path.sep}agents${path.sep}`)) visit(full);
  }
}

function visit(file) {
  const raw = fs.readFileSync(file, "utf8");
  let changed = 0;
  const next = raw
    .split("\n")
    .map((line) => {
      if (!PATTERN.test(line)) return line;
      PATTERN.lastIndex = 0;
      const out = rewriteLine(line);
      if (out !== line) changed += 1;
      return out;
    })
    .join("\n");
  if (changed === 0) return;
  files += 1;
  lines += changed;
  touched.push(`${file} (${changed})`);
  if (APPLY) fs.writeFileSync(file, next, "utf8");
}

walk(ROOT);
console.log(`${APPLY ? "rewrote" : "would rewrite"} ${lines} lines in ${files} files`);
for (const line of touched.slice(0, 12)) console.log("  " + line);
if (touched.length > 12) console.log(`  … and ${touched.length - 12} more`);
