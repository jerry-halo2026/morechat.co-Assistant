"""拉片拆解表生成｜逐镜时长景别信息点

极帆·生成型技能：读标准化 JSON，出一份可直接用的 Markdown 成稿。
"""
import argparse
import sys

from _draft import bullets, emit, fail, load, md_table, req, rows, text, write_md

CONFIG = {
    "display": "拉片拆解表生成｜逐镜时长景别信息点",
    "short": "拉片拆解",
    "kind": "list",
    "boundary": "输出是**候选清单**，供用户挑选与改写；不替用户做最终选择，也不保证任一条目的实际效果。",
    "meta_fields": []
}


def build_doc(data, records, errors):
    blocks = []
    for i, item in enumerate(records, 1):
        heading = text(item.get("heading")) or "第 %d 节" % i
        body = text(item.get("body"))
        points = item.get("points")
        chunk = []
        if body:
            chunk.append(body)
        if isinstance(points, list) and points:
            chunk.append(bullets(points))
        if not chunk:
            errors.append("items[%d] 需要 body 或 points 至少一项" % i)
            continue
        blocks.append((heading, "\n\n".join(chunk)))
    return blocks


def build_list(data, records, errors):
    body = []
    for i, item in enumerate(records, 1):
        title = text(item.get("title"))
        if not title:
            errors.append("items[%d].title 必填" % i)
            continue
        body.append([i, title, text(item.get("content")), text(item.get("note"))])
    return [("候选清单", md_table(["#", "条目", "内容", "备注"], body))]


def build_plan(data, records, errors):
    body = []
    for i, item in enumerate(records, 1):
        step = text(item.get("step")) or str(i)
        what = text(item.get("what"))
        if not what:
            errors.append("items[%d].what 必填" % i)
            continue
        body.append([step, text(item.get("when")), what, text(item.get("owner")), text(item.get("note"))])
    return [("执行计划", md_table(["顺序", "时间", "动作", "负责人", "备注"], body))]


BUILDERS = {"doc": build_doc, "list": build_list, "plan": build_plan}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        data = load(args.input)
        errors = []
        topic = req(data, "topic", errors)
        records = rows(data, errors)
        blocks = BUILDERS[CONFIG["kind"]](data, records, errors)
        if errors:
            raise ValueError("；".join(errors))

        pending = [x for x in (data.get("pending") or []) if text(x)]
        meta = [["成稿类型", CONFIG["display"]],
                ["主题", topic],
                ["用户给定条目", len(records)],
                ["待确认项", len(pending)]]
        for key in CONFIG.get("meta_fields", []):
            value = text(data.get(key))
            if value:
                meta.append([key, value])

        blocks = blocks + [
            ("待确认项", bullets(pending, "（用户未标注待确认项）")),
            ("使用边界", CONFIG["boundary"]),
        ]
        out = write_md(args.output, "%s｜%s" % (topic, CONFIG["short"]), meta, blocks)
        emit({"ok": True, "output": out, "sections": len(blocks), "items": len(records),
              "pending": len(pending), "kind": CONFIG["kind"]})
    except Exception as exc:
        return fail(exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
