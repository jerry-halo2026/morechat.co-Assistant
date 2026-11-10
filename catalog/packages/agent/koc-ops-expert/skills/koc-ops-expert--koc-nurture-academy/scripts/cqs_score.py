#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOC 内容质检打分工具（CQS 5 维 20 分）。

脚本只做换算、判定与批次根因诊断，**每一维的分数和理由必须由人依据
references/qc-rubric.md 给出**。合规维度是一票否决，不参与计分。

子命令：
    score   单篇打分 → 总分、判定、必须给的反馈要点
    batch   批次统计 → 分布、合格率、根因诊断、下一步动作
    rubric  打印评分锚点

用法：
    python3 cqs_score.py score --json '{...}' --text
    python3 cqs_score.py batch --file /tmp/qc.json --text
"""

from __future__ import annotations

import argparse
import json
import sys

DIMS = [
    ("accuracy", "信息准确", "卖点准确、参数无误、有细节佐证"),
    ("authenticity", "真实感", "第一人称、场景可验证、有不完美的细节"),
    ("completeness", "完成度", "达到 Brief 的最低规格与必备元素"),
    ("searchability", "可搜索性", "标题与正文自然带上目标搜索词"),
]

ANCHORS = {
    "accuracy": {4: "卖点准确且有细节佐证", 3: "卖点准确无错误", 2: "有轻微表述偏差", 1: "有事实性错误"},
    "authenticity": {4: "个人化细节 + 场景可验证 + 写了不完美处", 3: "第一人称、场景成立",
                     2: "像通稿", 1: "明显搬运/模板化"},
    "completeness": {4: "超过最低规格且有巧思", 3: "达到最低规格", 2: "缺 1 项必备元素", 1: "缺 ≥2 项"},
    "searchability": {4: "标题与正文含目标词且自然", 3: "含目标词", 2: "词不匹配", 1: "无关键词"},
}

FEEDBACK = {
    "accuracy": "有个地方要改：{note}。这类数字类描述直接抄说明卡就行，不用自己记。",
    "authenticity": "内容是完整的，但读起来偏介绍页。加一段你自己的具体场景——当时在什么情况下用的、哪一步不太顺。不完美的细节最让人信。",
    "completeness": "少了必备元素：{note}。补上就可以，其他都挺好。",
    "searchability": "内容没问题，但标题没带目标搜索词。大部分人是搜这个词才刷到这类内容的，加上去曝光差挺多。",
}


def score_one(p: dict) -> dict:
    name = p.get("note") or p.get("name") or "未命名内容"
    if p.get("compliance") is False:
        return {
            "内容": name,
            "判定": "退回 · 合规一票否决",
            "总分": None,
            "必须做的动作": [
                "立刻退回，附具体的违规点与正确表述",
                "已发布的先改后删：优先修改标题/正文，不能改的再考虑下架",
                "把该违规点补进新人包的禁用词表，避免同批次重复发生",
            ],
            "原因": p.get("compliance_reason", "（未填写违规点 —— 退回时必须写清楚）"),
        }

    total, detail, weak = 0, [], []
    for key, label, hint in DIMS:
        v = p.get(key)
        if v is None:
            return {"内容": name, "判定": "无法打分", "缺少维度": label}
        try:
            v = round(float(v))          # 3.9 应按 4 计，不是截断成 3
        except (TypeError, ValueError):
            return {"内容": name, "判定": "无法打分", "缺少维度": f"{label}（取值 {v!r} 不是数字）"}
        if not (1 <= v <= 4):
            return {"内容": name, "判定": "无法打分",
                    "缺少维度": f"{label}（{v} 分越界：rubric 只有 1~4 分，0 分请用 compliance=false 表达）"}
        total += v
        detail.append({"维度": label, "得分": v, "锚点": ANCHORS[key][v]})
        if v <= 2:
            note = (p.get("notes") or {}).get(key, "")
            weak.append(FEEDBACK[key].format(note=note or "见质检备注"))

    # 4 维 × 4 分 = 16 分原始分，换算成 rubric 的 20 分制
    score20 = round(total / 16 * 20, 1)

    if score20 >= 16:
        verdict, action = "精选", [
            "进精选池，申请流量放大（投流 / 官号转发）",
            "**优先谈二次授权**：这是把单篇成本摊薄的关键动作",
            "回复时说清楚「好在哪」，并邀请他做下一期的选题共创",
        ]
    elif score20 >= 12:
        verdict, action = "合格", ["正常结算", "回一句具体的肯定（不要只发『收到』）"]
    elif score20 >= 8:
        verdict, action = "合格待改", ["正常结算", "**必须给具体改进反馈**，不可跳过", "下一期给他更简单的选题，先把胜任感建起来"]
    else:
        verdict, action = "退回", ["退回重做（限 1 次），必须附具体修改点", "同时提供半成品素材包，降低返修门槛"]

    return {
        "内容": name,
        "总分": score20,
        "原始分": f"{total}/16",
        "判定": verdict,
        "逐维": detail,
        "必须给的反馈": weak or ["回一句具体的肯定：指出哪一段/哪一张图好，以及为什么好"],
        "下一步": action,
        "纪律": "反馈只对本人说，不做公开排名。",
    }


def batch(payload) -> dict:
    items = payload if isinstance(payload, list) else payload.get("items", [])
    scored = [score_one(x) for x in items]
    rejected = [s for s in scored if str(s.get("判定", "")).startswith("退回 · 合规")]
    unscorable = [s for s in scored if s.get("判定") == "无法打分"]
    valid = [s for s in scored if s.get("总分") is not None]
    n = len(scored)
    if not n:
        return {"错误": "没有可统计的内容"}
    # 分母口径：合格率 = 合格篇数 ÷ 已交付且可判定的篇数（含合规退回，不含数据缺失的）
    judged = len(valid) + len(rejected)
    if judged == 0:
        return {"错误": f"{n} 条内容全部无法打分（维度缺失或取值越界），先补齐质检数据"}

    qualified = [s for s in valid if s["总分"] >= 12]
    featured = [s for s in valid if s["总分"] >= 16]
    # 各维均分只统计「打得出分」的篇（合规退回篇不参与，否则会把内容质量问题误判成维度问题）
    valid_names = {s["内容"] for s in valid}
    dim_avg = {}
    for key, label, _ in DIMS:
        vals = [float(x[key]) for x in items
                if (x.get("note") or x.get("name") or "未命名内容") in valid_names
                and isinstance(x.get(key), (int, float))]
        if vals:
            dim_avg[label] = round(sum(vals) / len(vals), 2)

    out = {
        "篇数": n,
        "可判定篇数": judged,
        "无法打分（数据缺失）": len(unscorable),
        "合规退回": len(rejected),
        "合格率": f"{len(qualified) / judged:.0%}（分母 = 可判定篇数 {judged}）",
        "精选率": f"{len(featured) / judged:.0%}",
        "各维均分（满分 4，仅统计可打分篇）": dim_avg,
        "分布": {
            "精选 ≥16": len(featured),
            "合格 12-15": len([s for s in valid if 12 <= s["总分"] < 16]),
            "待改 8-11": len([s for s in valid if 8 <= s["总分"] < 12]),
            "退回 <8 或合规否决": len([s for s in valid if s["总分"] < 8]) + len(rejected),
            "无法打分": len(unscorable),
        },
    }

    # 根因诊断：批次问题几乎都在流程，不在个人
    diag = []
    if len(qualified) / judged < 0.75:
        diag.append("合格率 < 75% → **问题在 Brief 不在 KOC**：重写 Brief、补样例、逐篇标注「参考什么」。")
    if dim_avg.get("真实感", 4) < 2.6:
        diag.append("真实感普遍偏低 → Brief 给了卖点没给场景，或素材包给得太满导致照抄。"
                    "Brief 增加「必须出现的使用场景」，素材包只给结构不给成稿。")
    if dim_avg.get("可搜索性", 4) < 2.6:
        diag.append("可搜索性普遍偏低 → 选题是从卖点倒推的。改用「用户会搜什么」倒推选题库。")
    if dim_avg.get("完成度", 4) < 2.6:
        diag.append("完成度普遍偏低 → 最低规格没写清楚或定得过高。用「下限」表述，并降低首篇难度。")
    if dim_avg.get("信息准确", 4) < 2.6:
        diag.append("信息准确普遍偏低 → 没给说明卡，KOC 在自己编参数（这也是合规风险最高的地方）。")
    if len(rejected) / judged > 0.05:
        diag.append(f"合规退回 {len(rejected) / judged:.0%} → 禁用词表没发到人。新人包里加禁用词表 + 上线发布前 60 秒自检。")
    if valid:
        hi = len(featured) / len(valid)
        lo = len([s for s in valid if s["总分"] < 8]) / len(valid)
        if hi > 0.15 and lo > 0.15:
            diag.append("分数两极分化 → 招募筛选太松，人不对。回到 FIT-6 收紧准入，或换招募渠道。")

    out["根因诊断"] = diag or ["本批次没有系统性问题，按单篇反馈即可。"]
    out["提醒"] = "批次看流程，单篇看人。合格率低于 75% 时不要去催 KOC，先改 Brief。"
    return out


def to_text(d, indent=0) -> str:
    pad = "  " * indent
    lines = []
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}{k}:")
                lines.append(to_text(v, indent + 1))
            else:
                lines.append(f"{pad}{k}: {v}")
    elif isinstance(d, list):
        for item in d:
            if isinstance(item, dict):
                lines.append(pad + "  ".join(f"{k}={v}" for k, v in item.items()))
            else:
                lines.append(f"{pad}- {item}")
    else:
        lines.append(f"{pad}{d}")
    return "\n".join(x for x in lines if x.strip())


def main() -> None:
    ap = argparse.ArgumentParser(description="KOC 内容质检打分（CQS）")
    ap.add_argument("cmd", choices=["score", "batch", "rubric"])
    ap.add_argument("--json")
    ap.add_argument("--file")
    ap.add_argument("--text", action="store_true")
    a = ap.parse_args()

    if a.cmd == "rubric":
        print("CQS 内容质检 5 维（合规为一票否决，其余 4 维各 1~4 分，换算为 20 分制）\n")
        print("  compliance   合规性     true/false —— false 直接退回，不计分")
        for key, label, hint in DIMS:
            print(f"  {key:<14}{label:<6}{hint}")
            for s in (4, 3, 2, 1):
                print(f"      {s} 分：{ANCHORS[key][s]}")
        print("\n判定：≥16 精选 / 12-15 合格 / 8-11 合格待改 / <8 退回；连续 2 次 <12 触发陪跑而非淘汰。")
        return

    try:
        if a.file:
            with open(a.file, encoding="utf-8") as f:
                payload = json.load(f)
        elif a.json:
            payload = json.loads(a.json)
        else:
            ap.error("需要 --json 或 --file")
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败：{e}", file=sys.stderr)
        sys.exit(2)

    try:
        result = score_one(payload) if a.cmd == "score" else batch(payload)
    except (ValueError, TypeError, KeyError) as e:
        print(f"输入有误：{e}", file=sys.stderr)
        sys.exit(2)
    print(to_text(result) if a.text else json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
