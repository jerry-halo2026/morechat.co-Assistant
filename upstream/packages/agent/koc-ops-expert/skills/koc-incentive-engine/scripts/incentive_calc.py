#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOC 激励设计测算与体检工具。

三件事：
    budget   激励预算上限与分层分配（激励预算由"它能撬动的增量"决定，不是拍脑袋定比例）
    checkup  激励机制体检 —— 按 Deci/Koestner/Ryan (1999) 128 项实验元分析的结论，
             逐条检查你的激励设计有没有踩上"越奖励越不想干"的坑
    roi      激励投入产出测算（含盈亏平衡的增量篇数）
    template 打印输入模板

用法：
    python3 incentive_calc.py budget --json '{...}' --text
    python3 incentive_calc.py checkup --json '{...}' --text
    python3 incentive_calc.py roi --json '{...}' --text

体检依据（可对客户复述的一手来源）：
    Deci, E.L., Koestner, R., & Ryan, R.M. (1999). Psychological Bulletin, 125(6), 627–668.
    · 按绩效分档的奖励，对"没拿到最高档"的人：d ≈ −0.80（剔除离群值 −0.88），全文最强的削弱效应
    · 完成即给（达标即得）：d = −0.36；参与即给：d = −0.40
    · 事先不承诺的惊喜奖励：d = 0.01（几乎无害）
    · 言语奖励/正向反馈：d = +0.33（成年人子样本 +0.43），唯一能提升内在动机的手段
    · 奖励撤销后削弱效应至少持续一周以上（延迟测量 d ≈ −0.49/−0.53）
"""

from __future__ import annotations

import argparse
import json
import sys

# --------------------------------------------------------------------------
# 激励机制体检规则：命中即扣分，每条都给依据与修正动作
# --------------------------------------------------------------------------

CHECKS = [
    {
        "key": "leaderboard_cash",
        "hit": True,
        "weight": 30,
        "risk": "按名次分档发现金（排行榜 Top1 拿大奖、其余递减）",
        "why": "这是元分析里伤害最大的形式：拿到低于最高档奖励的人 d≈−0.80。"
               "它伤害的是排在后面的**大多数人**，而这些人才是池子的主体。",
        "fix": "改成「达标即得」的固定门槛制（如：本月出 2 篇合格内容 → 固定奖金 X 元），"
               "所有达标的人拿一样的钱。要评优就评「进步榜/互助榜」，且不挂钩现金。",
    },
    {
        "key": "public_ranking",
        "hit": True,
        "weight": 15,
        "risk": "公开个人排名 / 公开质检分",
        "why": "公开排名让「非第一名」这件事变得可见，等价于给大多数人持续的负反馈。",
        "fix": "质检分与排名只对本人可见；对外只公布「本期精选内容」，不公布名次与末位。",
    },
    {
        "key": "cash_only_top_tier",
        "hit": True,
        "weight": 12,
        "risk": "核心层的主要激励仍然是现金",
        "why": "对本来就热爱品类的人，现金反而削弱内在动机（有趣任务 d=−0.68；无趣任务 d=+0.18 不显著）。"
               "行业数据也一致：社群回报中现金仅占 11%，公开认可占 67%。",
        "fix": "核心层改给「钱买不到的东西」：共创权、选题决定权、内测资格、带教身份、官方点名、线下见面。"
               "现金留给外围层与一次性铺量。",
    },
    {
        "key": "recently_reduced",
        "hit": True,
        "weight": 15,
        "risk": "最近削减过激励额度",
        "why": "奖励撤销后的削弱效应至少持续一周以上（延迟测量 d≈−0.49/−0.53），且不会自动恢复。",
        "fix": "**激励只能加不能减**。确实要降成本，就换形式而不是砍额度："
               "现金换成等值权益/优先寄样/身份升级，并配一次说明沟通。",
    },
    {
        "key": "verbal_feedback_sop",
        "hit": False,
        "weight": 18,
        "risk": "逐条内容反馈没有写进 SOP（只发钱不说话）",
        "why": "言语正反馈是元分析中**唯一**提升内在动机的手段（d=+0.33，成年人 +0.43），"
               "而且零成本。不做等于白白丢掉最划算的一项。",
        "fix": "把「每篇内容回一句具体的话」写进运营 SOP 与考核："
               "指出哪一段/哪张图好、为什么好，再给不超过 1 条建议。",
    },
    {
        "key": "surprise_reserved",
        "hit": False,
        "weight": 10,
        "risk": "没有预留「惊喜加码」预算",
        "why": "事先不承诺的奖励几乎无害（d=0.01），是所有物质激励里性价比最高的一种。",
        "fix": "把激励预算的 15%~25% 留作不预告的加码（突然的红包/礼盒/升级），事后发放并配一句具体理由。",
    },
    {
        "key": "quota_pressure",
        "hit": True,
        "weight": 8,
        "risk": "月度硬性产出考核 + 未达标即降级",
        "why": "持续被考核会损害自主感；掉级机制（规避损失）与「奖励只能加不能减」叠加会造成双重伤害。",
        "fix": "评估周期改季度；降级设 1 个季度宽限期；允许主动申请 1~3 个月「休赛期」而不掉级；"
               "降级只私信通知并附恢复路径，绝不公示。",
    },
    {
        "key": "派单_not_选单",
        "hit": True,
        "weight": 12,
        "risk": "选题是派发的，不是可选的",
        "why": "自主感是三种基本心理需要中对内在动机影响最大的一项，而「把派单改成选单」成本为零。",
        "fix": "每期给 3~5 个选题让 KOC 自选 1~2 个，允许自己提；审稿轮次上限 1 轮。",
    },
]


TRUEISH = {"true", "yes", "y", "1", "是", "有"}
FALSEISH = {"false", "no", "n", "0", "否", "无", ""}


def _as_bool(v, key):
    """字符串 "false" 在 Python 里是真值 —— 必须走白名单，否则体检结论会反。"""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    if s in TRUEISH:
        return True
    if s in FALSEISH:
        return False
    raise ValueError(f"{key} 的取值 {v!r} 无法判断真假，请用 true / false")


def checkup(payload: dict) -> dict:
    m = payload.get("mechanisms", payload)
    hits, oks, missing = [], [], []
    lost, covered_weight = 0, 0
    total_weight = sum(c["weight"] for c in CHECKS)
    for c in CHECKS:
        v = m.get(c["key"])
        if v is None:
            missing.append(c["risk"])
            oks.append({"项": c["risk"], "状态": "未提供，无法判断"})
            continue
        covered_weight += c["weight"]
        if _as_bool(v, c["key"]) == c["hit"]:
            lost += c["weight"]
            hits.append({
                "风险": c["risk"], "扣分": c["weight"],
                "为什么": c["why"], "怎么改": c["fix"],
            })
        else:
            oks.append({"项": c["risk"], "状态": "已避开 ✓"})

    coverage = covered_weight / total_weight if total_weight else 0
    if coverage < 0.6:
        return {
            "激励健康度": "无法评分",
            "结论": f"信息覆盖率仅 {coverage:.0%}（{len(missing)} 项未提供），**不足以给出健康度分数**。"
                  "把下面这些先问清楚再体检 —— 空着不填不等于没问题。",
            "缺失项": missing,
            "命中的风险": hits or "无（但样本不足）",
            "依据": "Deci, Koestner & Ryan (1999), Psychological Bulletin 125(6):627–668（128 项实验元分析）",
        }

    # 按已提供项归一化：没问到的项不算分，避免「什么都不填得 100 分」
    score = max(0, round(100 * (covered_weight - lost) / covered_weight))
    if score >= 85:
        verdict = "健康：机制设计没有明显的动机挤出风险，可以上线。"
    elif score >= 65:
        verdict = "可用但有隐患：先修掉扣分最高的两项再上线，否则 3~6 个月后会看到核心层流失。"
    elif score >= 40:
        verdict = "有系统性风险：当前设计会在中期把内在动机换成外在依赖，撤掉奖励就没人干。建议重做激励结构。"
    else:
        verdict = "必须重做：这套设计的主要机制正是元分析中伤害最大的那几种。"

    return {
        "激励健康度": score,
        "信息覆盖率": f"{coverage:.0%}" + (f"（{len(missing)} 项未提供，分数只反映已提供的部分）" if missing else ""),
        "结论": verdict,
        "命中的风险": hits or "无",
        "已避开": oks,
        "一句话原则": "达标即得 + 逐条言语反馈 + 预留惊喜加码；核心层给身份与权力，外围层给物质；激励只能加不能减。",
        "依据": "Deci, Koestner & Ryan (1999), Psychological Bulletin 125(6):627–668（128 项实验元分析）",
    }


def budget(payload: dict) -> dict:
    """激励预算不是拍比例定的，是由它能撬动的增量决定的。"""
    baseline = float(payload.get("baseline_notes", 0) or 0)
    target = float(payload.get("target_notes", 0) or 0)
    value = float(payload.get("value_per_note", 0) or 0)
    active = float(payload.get("active_koc", 0) or 0)
    share = float(payload.get("share", 0.3) or 0.3)

    if target <= baseline:
        return {"错误": "target_notes 必须大于 baseline_notes —— 激励是用来买增量的，不是给存量发钱。"}
    if value <= 0:
        return {"错误": "需要 value_per_note：一篇合格内容对你值多少钱。"
                      "取法二选一：①外采一条同类内容的报价；②该内容进素材银行后能替代的素材制作费。"}
    if not (0 < share <= 0.5):
        return {"错误": f"share={share} 越界：激励拿走增量价值的比例应在 0~50% 之间，超过就不值得做了。"}

    incr = target - baseline
    cap = incr * value * share
    # 四项占比之和 = 100%，惊喜加码是从总额里切出来的，不是额外再加
    split = [
        ("L0–L1 外围与新人", 0.45, "达标即得的小额现金/礼品卡 + 优先寄样（物质为主，这层就是冲物质来的）"),
        ("L2 带货层", 0.20, "阶梯佣金 + 达标奖金 + 素材授权费（把钱和结果绑在一起）"),
        ("L3–L4 核心层", 0.15, "**主要不是钱**：共创权、内测、带教身份、线下活动；预算花在体验与礼遇上"),
        ("惊喜加码（不预告）", 0.20, "事先不承诺、事后发放，几乎不伤内在动机（d=0.01），是最划算的一档"),
    ]
    out = {
        "增量内容篇数": incr,
        "单篇内容价值": value,
        "激励可分走的比例": f"{share:.0%}（经验值：拿走增量价值的 30% 以内，剩下的才是你赚的）",
        "激励预算上限（月）": round(cap, 0),
        "分层分配建议": [
            {"层": name, "占比": f"{r:.0%}", "金额": round(cap * r, 0), "形式": desc}
            for name, r, desc in split
        ],
        "分配校验": f"{sum(r for _, r, _ in split):.0%}（四项之和应为 100%，惊喜加码含在总额内，不是额外追加）",
    }
    if active > 0:
        out["单人月激励上限"] = round(cap / active, 1)
        out["提醒"] = ("单人月激励一旦超过当地兼职时薪的心理锚点，KOC 会开始把这件事当兼职做，"
                     "内容真实感下降。宁可把钱花在「更多人拿小额 + 少数人拿身份」上。")
    out["纪律"] = "先定上限再设计形式；先设计形式再谈金额。顺序反了就会变成加价竞赛。"
    return out


def roi(payload: dict) -> dict:
    spend = float(payload.get("incentive_spend", 0) or 0)
    baseline = float(payload.get("baseline_notes", 0) or 0)
    after = float(payload.get("after_notes", 0) or 0)
    value = float(payload.get("value_per_note", 0) or 0)
    if spend <= 0 or value <= 0:
        return {"错误": "需要 incentive_spend 与 value_per_note"}
    incr = after - baseline
    gain = incr * value
    out = {
        "激励投入": spend,
        "增量篇数": incr,
        "增量价值": round(gain, 0),
        "激励 ROI": round(gain / spend, 2) if spend else None,
        "盈亏平衡增量篇数": round(spend / value, 1),
    }
    if incr <= 0:
        out["结论"] = "激励没有带来增量：不要加钱，先查是不是履约机制（稿费后置/选题门槛/结算及时率）的问题。"
    elif gain / spend < 1:
        out["结论"] = (f"ROI {gain / spend:.2f} < 1：激励强度不足以撬动增量，或撬动的是本来就会产出的人。"
                      "改成「只对增量部分给激励」（如超出个人历史均值的部分才计奖）。")
    elif gain / spend < 2:
        out["结论"] = f"ROI {gain / spend:.2f}：有效但不宽裕。优先把预算从普惠发钱挪到惊喜加码与身份类权益。"
    else:
        out["结论"] = f"ROI {gain / spend:.2f}：有效。可以扩大到下一层，但**先别加金额，先加人数**。"
    out["提醒"] = ("这里算的是内容产出的增量，没算内容带来的销售增量。"
                 "销售增量必须用对照组/专属码/时间断点单独测，不要把两者混在一个 ROI 里。")
    return out


TEMPLATE = {
    "budget": {"baseline_notes": 40, "target_notes": 100, "value_per_note": 300,
               "active_koc": 120, "share": 0.3},
    "checkup": {"mechanisms": {
        "leaderboard_cash": True, "public_ranking": True, "cash_only_top_tier": True,
        "recently_reduced": False, "verbal_feedback_sop": False, "surprise_reserved": False,
        "quota_pressure": True, "派单_not_选单": True,
    }},
    "roi": {"incentive_spend": 12000, "baseline_notes": 40, "after_notes": 96, "value_per_note": 300},
}


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
                lines.append(pad + "· " + "  ".join(f"{k}={v}" for k, v in item.items()))
            else:
                lines.append(f"{pad}- {item}")
    else:
        lines.append(f"{pad}{d}")
    return "\n".join(x for x in lines if x.strip())


def main() -> None:
    ap = argparse.ArgumentParser(description="KOC 激励设计测算与体检")
    ap.add_argument("cmd", choices=["budget", "checkup", "roi", "template"])
    ap.add_argument("--json")
    ap.add_argument("--file")
    ap.add_argument("--text", action="store_true")
    a = ap.parse_args()

    if a.cmd == "template":
        print("激励体检的 8 个开关（true/false），对应 references/incentive-design.md：\n")
        for c in CHECKS:
            print(f"  {c['key']:<22}{'命中即扣分' if c['hit'] else '缺失即扣分'}  {c['risk']}")
        print()
        print(json.dumps(TEMPLATE, ensure_ascii=False, indent=2))
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

    result = {"budget": budget, "checkup": checkup, "roi": roi}[a.cmd](payload)
    print(to_text(result) if a.text else json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
