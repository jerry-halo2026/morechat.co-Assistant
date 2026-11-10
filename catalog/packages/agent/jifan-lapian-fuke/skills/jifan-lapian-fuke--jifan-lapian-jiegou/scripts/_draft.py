"""极帆生成型技能共享库：读输入 → 出 Markdown 成稿。"""
import json
import os
import sys


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("输入必须是 JSON 对象")
    return data


def text(value):
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


def req(data, field, errors):
    value = text(data.get(field))
    if not value:
        errors.append("%s 必填" % field)
    return value


def rows(data, errors, field="items", least=1):
    raw = data.get(field)
    if not isinstance(raw, list) or len(raw) < least:
        errors.append("%s 必须是至少 %d 项的数组" % (field, least))
        return []
    out = []
    for i, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            errors.append("%s[%d] 必须是对象" % (field, i))
            continue
        out.append(item)
    return out


def md_table(header, body, empty="（无）"):
    if not body:
        return empty
    line = "| " + " | ".join(header) + " |"
    rule = "|" + "|".join(["---"] * len(header)) + "|"
    out = [line, rule]
    for r in body:
        cells = [text(c).replace("|", "｜").replace("\n", "<br>") or "-" for c in r]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def bullets(values, empty="（无）"):
    values = [text(v) for v in values if text(v)]
    if not values:
        return empty
    return "\n".join("- " + v for v in values)


def write_md(path, title, meta, blocks):
    parts = ["# " + title, ""]
    if meta:
        parts += [md_table(["项", "内容"], meta), ""]
    for heading, body in blocks:
        parts += ["## " + heading, "", body, ""]
    content = "\n".join(parts).rstrip() + "\n"
    folder = os.path.dirname(os.path.abspath(path))
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return os.path.abspath(path)


def emit(summary):
    print(json.dumps(summary, ensure_ascii=False))


def fail(exc):
    sys.stderr.write("ERROR: %s\n" % exc)
    return 1
