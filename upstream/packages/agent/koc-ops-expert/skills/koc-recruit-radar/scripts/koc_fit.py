#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOC 选人与招募测算工具 —— FIT-6 评分卡、反刷量体检、招募漏斗反推。

脚本只做换算、排序与一致性检查，**每一维的打分和理由必须由专家依据
references/fit6-scorecard.md 自己给出**。分数不是算出来的，是判断出来的。

子命令：
    score    单个 KOC 打分 → 总分、分层建议、最弱维、补强动作、否决项检查
    rank     批量打分对比 → 排序、分层配额、建议优先建联名单
    audit    反刷量体检 → 用互动结构数据判断账号数据是否可信
    funnel   招募漏斗反推 → 要拿到 N 篇合格内容，得触达多少人、寄多少样、花多少钱、要几个运营
    pool     池规模倒推 → 任务驱动池 / 自然贡献池两种口径分开算，并用人力算出真实上限
    template 打印输入模板

用法：
    python3 koc_fit.py score --json '{...}' --text
    python3 koc_fit.py rank --file /tmp/candidates.json --text
    python3 koc_fit.py audit --json '{"like":800,"comment":5,"collect":20}' --text
    python3 koc_fit.py funnel --json '{"target_notes":100,"mode":"invite"}' --text
    python3 koc_fit.py pool --json '{"target_notes_per_month":100,"ops_headcount":1}' --text
"""

from __future__ import annotations

import argparse
import json
import sys

# --------------------------------------------------------------------------
# FIT-6 评分卡：六个维度，满分 100
# --------------------------------------------------------------------------

DIMENSIONS = [
    ("fit", "人货匹配", 25, "内容领域与品类相关度 × 粉丝画像与目标人群重合度"),
    ("content", "内容力", 20, "近 30 天更新稳定性、表达与审美、批次内爆文能力"),
    ("audience", "粉丝质量", 15, "真实度（互动结构）、地域/性别/年龄与目标人群一致性"),
    ("conversion", "转化力", 20, "历史带货或挂链表现、评论区求购信号、内容形态是否易转化"),
    ("coop", "配合度", 10, "响应速度、改稿意愿、历史履约记录"),
    ("cost", "成本效率", 10, "寄样+稿费+佣金的综合成本 vs 预期产出"),
]

VETO_LABELS = {
    "fake_data": "V1 数据异常：互动结构不合常理、粉丝画像失真，高度疑似刷量",
    "risk_persona": "V2 人设风险：有争议言论、违规记录或负面舆情历史",
    "competitor": "V3 竞品绑定：近 90 天接过直接竞品商单且无排他约定",
    "no_disclosure": "V4 拒绝合规：不接受平台报备或不愿标注「广告」",
    "prepay_trap": "V5 结算风险：要求高额前置买断且拒签履约条款",
}

GRADES = [
    (80, "S · 直通带货位", "签", "可进 L2/L3：给固定稿费 + 高佣或阶梯佣金，优先寄新品，纳入内容授权范围"),
    (65, "A · 主力内容位", "签", "进 L1：寄样 + 纯佣（或小额后置稿费），连续 2 篇合格后评估升级"),
    (50, "B · 体验官观察", "试", "进 L0：只寄小样/试用装，跑 1 篇看合格率，不给稿费"),
    (0, "C · 不建议合作", "拒", "不寄样。若内容力单项突出，可只做内容采买（按篇付费，不进池）"),
]

REINFORCE = {
    "fit": ["换人：人货不匹配是最贵的错误，靠 brief 补不回来",
            "若人必须用：改内容角度，从「产品测评」切到「生活场景植入」，降低违和感"],
    "content": ["给样例：附 2~3 条对标笔记 + 逐条讲为什么好，比写 500 字 brief 有用",
                "降形态难度：视频改图文、口播改图文测评，先让他能稳定交付"],
    "audience": ["先跑 audit 子命令做反刷量体检，异常直接否决",
                 "画像不匹配但内容力强：只用作素材来源（授权后投流定向到目标人群）"],
    "conversion": ["带货是练出来的：先给挂链任务 + 专属券码，用小单量验证",
                   "转化力弱但种草强：放在内容位，不背 GMV 指标，别用出单率考核他"],
    "coop": ["用机制而不是感情解决：稿费后置、履约承诺函、黑名单跨项目共享",
             "响应慢的批量沟通改成模板化 SOP，减少来回"],
    "cost": ["报价高就压需求：从「定制视频」降到「图文直发」",
             "改纯佣或阶梯：把不确定性转成分成，不要前置买断"],
}


def _clip(v, lo, hi):
    return max(lo, min(hi, v))


def score_one(payload: dict) -> dict:
    name = payload.get("name") or payload.get("account") or "未命名 KOC"
    total, detail, missing = 0.0, [], []
    for key, label, full, hint in DIMENSIONS:
        item = payload.get(key)
        if item is None:
            missing.append(label)
            continue
        if isinstance(item, (int, float)):
            item = {"score": item}
        s = _clip(float(item.get("score", 0)), 0, full)
        total += s
        detail.append({
            "维度": label, "得分": round(s, 1), "满分": full,
            "达成率": round(s / full, 2),
            "理由": item.get("reason", "（未填写理由 —— 打分必须给理由）"),
        })

    vetoes = payload.get("vetoes") or {}
    hits = [VETO_LABELS[k] for k in VETO_LABELS if vetoes.get(k)]

    out = {
        "对象": name,
        "总分": round(total, 1),
        "逐维": detail,
        "否决项": hits or "无",
    }
    if missing:
        out["未打分维度"] = missing
        out["提醒"] = "有维度未打分，总分被低估。要么补齐，要么在报告里注明该维度信息缺失。"

    if hits:
        out["结论"] = "拒 · 一票否决"
        out["处置"] = "命中否决项，不看总分。" + hits[0]
        return out

    for cut, grade, action, advice in GRADES:
        if total >= cut:
            out["分层建议"] = grade
            out["结论"] = action
            out["处置"] = advice
            break

    if detail:
        weakest = min(detail, key=lambda d: d["达成率"])
        key = next(k for k, label, _, _ in DIMENSIONS if label == weakest["维度"])
        out["最弱维"] = f'{weakest["维度"]}（{weakest["得分"]}/{weakest["满分"]}）'
        out["补强动作"] = REINFORCE.get(key, [])
    return out


def rank_many(payload) -> dict:
    items = payload if isinstance(payload, list) else payload.get("candidates", [])
    scored = [score_one(x) for x in items]
    ok = [s for s in scored if s.get("结论") != "拒 · 一票否决"]
    ok.sort(key=lambda s: s["总分"], reverse=True)
    vetoed = [s for s in scored if s.get("结论") == "拒 · 一票否决"]

    rows = []
    for i, s in enumerate(ok, 1):
        rows.append({"排名": i, "对象": s["对象"], "总分": s["总分"],
                     "分层": s.get("分层建议", "—"), "最弱维": s.get("最弱维", "—")})
    n = len(ok)
    out = {
        "候选数": len(scored),
        "通过初筛": n,
        "被否决": [{"对象": s["对象"], "原因": s["处置"]} for s in vetoed],
        "排序": rows,
    }
    if n:
        s_cnt = sum(1 for s in ok if s["总分"] >= 80)
        a_cnt = sum(1 for s in ok if 65 <= s["总分"] < 80)
        b_cnt = sum(1 for s in ok if 50 <= s["总分"] < 65)
        out["分层分布"] = {"S 直通带货位": s_cnt, "A 主力内容位": a_cnt, "B 体验官观察": b_cnt,
                       "C 不建议": n - s_cnt - a_cnt - b_cnt}
        out["建联优先级"] = [r["对象"] for r in rows[:min(20, n)]]
        if s_cnt + a_cnt < n * 0.3:
            out["提醒"] = ("70% 以上的候选都在 B 档及以下：说明招募渠道的人群不对，"
                         "先换渠道（老客池 / 竞品评论区 / 垂类话题）再谈筛选标准，"
                         "在差池子里挑人是浪费时间。")
    return out


def audit_account(payload: dict) -> dict:
    """反刷量体检：互动结构比单看点赞数诚实得多。"""
    like = float(payload.get("like", 0) or 0)
    comment = float(payload.get("comment", 0) or 0)
    collect = float(payload.get("collect", 0) or 0)
    read = float(payload.get("read", 0) or 0)
    fans = float(payload.get("fans", 0) or 0)
    category = str(payload.get("category", "情绪型"))

    if like <= 0:
        return {"结论": "无法判断", "原因": "缺少点赞数"}

    cl = comment / like
    kl = collect / like
    collect_floor = 0.15 if category in ("功能型", "功能", "家清", "母婴", "3C") else 0.08
    # hard = 可直接判 V1 否决；soft = 需人工看、不单独构成否决
    hard, soft, notes = [], [], []

    if cl < 0.01:
        hard.append(f"评论/点赞 {cl:.3f} < 0.01：高度疑似刷赞（真实账号很少低于 0.02）")
    elif cl > 0.30:
        soft.append(f"评论/点赞 {cl:.2f} > 0.30：疑似互赞群/评论互刷，也可能是内容引战，需看评论内容")
    else:
        notes.append(f"评论/点赞 {cl:.3f} 在合理带（0.02~0.10 常见）")

    if kl < 0.03:
        hard.append(f"收藏/点赞 {kl:.3f} < 0.03：收藏极低，内容缺少「有用性」，或数据注水")
    elif kl < collect_floor:
        notes.append(f"收藏/点赞 {kl:.2f} 低于该品类建议线 {collect_floor}：偏情绪型内容，转化能力存疑")
    else:
        notes.append(f"收藏/点赞 {kl:.2f} 达标（{category}品类建议 ≥{collect_floor}）")

    if read > 0:
        er = (like + collect + comment) / read
        notes.append(f"互动率 {er:.2%}（常见带 3%~5%）")
        if er > 0.15:
            soft.append(f"互动率 {er:.1%} 异常高：可能是爆文，也可能是刷量 —— 看单篇分布而非均值再定")
    if fans > 0 and like / fans > 1.5:
        soft.append(f"篇均点赞是粉丝数的 {like / fans:.1f} 倍：可能是爆款账号，也可能是买量，看历史稳定性")

    if hard:
        verdict = "建议否决（命中 V1 数据异常）"
    elif soft:
        verdict = "不否决，但转人工深审 —— 软信号单独不构成否决证据"
    else:
        verdict = "数据结构可信度可接受"

    return {
        "评论/点赞": round(cl, 4),
        "收藏/点赞": round(kl, 4),
        "硬信号（可判否决）": hard or "无",
        "软信号（需人工看）": soft or "无",
        "观察": notes,
        "结论": verdict,
        "提醒": "单篇数据不足以定论。至少看近 10 篇的分布：真实账号波动大，刷量账号数据整齐得反常。"
              "软信号里「互动率异常高」尤其容易误杀优质小号 —— 它同样是爆文的特征。",
    }


# --------------------------------------------------------------------------
# 招募漏斗反推
# --------------------------------------------------------------------------

FUNNEL_DEFAULTS = {
    # 【经验值/待校准】：本次研究未检索到公开的行业基准，以下为结构性推导起始值
    "open": {  # 公开招募（发帖/落地页报名）
        "pass_rate": 0.20,      # 报名 → 初筛通过
        "response": 0.60,       # 通过 → 建联响应
        "accept": 0.30,         # 响应 → 接受合作（纯佣）
        "address": 0.90, "ship": 0.98, "deliver": 0.95,
        "r_pub": 0.45, "r_qc": 0.78,
    },
    "invite": {  # 定向邀约（一对一私信/挖人）
        "pass_rate": 1.0,
        "response": 0.45,
        "accept": 0.35,
        "address": 0.92, "ship": 0.98, "deliver": 0.95,
        "r_pub": 0.65, "r_qc": 0.85,
    },
    "platform": {  # 平台官方合作单（蒲公英/星图下单）
        "pass_rate": 1.0,
        "response": 0.55,
        "accept": 0.60,
        "address": 0.98, "ship": 0.99, "deliver": 0.98,
        "r_pub": 0.93, "r_qc": 0.93,
    },
}


def funnel_plan(payload: dict) -> dict:
    mode = str(payload.get("mode", "invite"))
    if mode not in FUNNEL_DEFAULTS:
        raise ValueError(f"mode 必须是 open / invite / platform 之一，收到 {mode!r}")
    p = dict(FUNNEL_DEFAULTS[mode])
    p.update({k: float(v) for k, v in payload.items()
              if k in FUNNEL_DEFAULTS[mode] and v is not None})

    target = float(payload.get("target_notes", 0) or 0)
    if target <= 0:
        raise ValueError("需要 target_notes：本期要拿到多少篇合格内容")
    for k, v in p.items():
        v = float(v)
        if not (0 < v <= 1):
            raise ValueError(f"{k}={v} 越界：所有环节转化率必须在 0（不含）到 1 之间")
        p[k] = v

    r_eff = p["r_pub"] * p["r_qc"]
    published = target / p["r_qc"]
    delivered = published / p["r_pub"]
    shipped = delivered / p["deliver"]
    addressed = shipped / p["ship"]
    accepted = addressed / p["address"]
    responded = accepted / p["accept"]
    reached = responded / p["response"]
    applied = reached / p["pass_rate"]

    stages = [
        ("触达/报名", applied, "招募帖曝光后报名，或私信触达人数"),
        ("初筛通过", reached, f"通过率 {p['pass_rate']:.0%}（FIT-6 ≥50 分）"),
        ("建联响应", responded, f"响应率 {p['response']:.0%}"),
        ("接受合作", accepted, f"接受率 {p['accept']:.0%}"),
        ("回收地址", addressed, f"地址回收 {p['address']:.0%}"),
        ("实际寄出", shipped, f"寄出率 {p['ship']:.0%}"),
        ("签收", delivered, f"签收率 {p['deliver']:.0%}"),
        ("按期发布", published, f"出稿率 {p['r_pub']:.0%}"),
        ("验收合格", target, f"合格率 {p['r_qc']:.0%}"),
    ]

    # 单调性自检：漏斗每一级人数必须逐级不增，否则说明某个转化率被填成了 >1
    seq = [applied, reached, responded, accepted, addressed, shipped, delivered, published, target]
    for a, b in zip(seq, seq[1:]):
        if b > a + 1e-9:
            raise ValueError("漏斗出现逆增（后一级人数大于前一级）：请检查各环节转化率是否都 ≤1")

    c_sample = float(payload.get("C_sample", 0) or 0)
    F = float(payload.get("F", 0) or 0)
    I = float(payload.get("I", 0) or 0)
    cost = None
    if c_sample:
        # 寄样成本按「寄出数」计，不按「签收数」—— 未签收的样品钱同样花掉了
        sample_cost = shipped * c_sample
        cost = {
            "寄样成本（按寄出数计）": round(sample_cost, 0),
            "稿费（按合格篇数后置）": round(target * F, 0),
            "激励": round(target * I, 0),
            "合计": round(sample_cost + target * (F + I), 0),
            "单篇合格内容综合成本": round((sample_cost + target * (F + I)) / target, 1),
            "口径": f"寄出 {int(round(shipped))} 件（其中签收 {int(round(delivered))} 件）。"
                  "未签收的样品成本已计入 —— 用签收数计价会系统性低估。",
        }

    weeks = float(payload.get("weeks", 4) or 4)
    per_op = float(payload.get("koc_per_op", 150) or 150)
    ops_needed = round(delivered / per_op, 1)

    return {
        "招募方式": {"open": "公开招募", "invite": "定向邀约", "platform": "平台官方合作单"}[mode],
        "目标合格内容": target,
        "有效出稿率 r_eff": round(r_eff, 3),
        "漏斗反推": [{"环节": n, "需要人数": int(round(v)), "口径": d} for n, v, d in stages],
        "成本估算": cost or "未提供样品成本，无法估算",
        "人力校验": {
            "本期需服务 KOC 数": int(round(delivered)),
            "单运营可管理活跃 KOC": per_op,
            "所需运营人力": ops_needed,
            "提醒": "单运营上限按关系强度分档（已有工具）：一次性铺量 200~500 / 复投池 80~150 / "
                  "深度陪跑 50~80；纯手工（Excel + 微信）按 0.6 折算。超载时履约率先崩。",
        },
        "周节奏": {
            "周期（周）": weeks,
            "每周需触达/私信": int(round(applied / weeks)),
            "每周需寄出": int(round(shipped / weeks)),
            "每周产出合格内容": round(target / weeks, 1),
        },
        "口径说明": "全部转化率为【经验值/待校准】起始值。**跑完首批 100 个样品后必须用自家实测值替换**，否则整个测算不可信。",
    }


def pool_sizing(payload: dict) -> dict:
    """池规模倒推：两种口径分开算，再用人力算出真实上限。

    **两种池子不能用同一套系数**：
      A 任务驱动池（有寄样 + 有任务 + 有陪跑）：池规模 = 目标篇数 ÷ (月活率 × 单人月产)
        月活率经验值 25%~40%，单人月产 1~2 篇。这是品牌自建 KOC 池的常见形态。
      B 自然贡献池（无寄样、靠自发产出）：适用参与不平等规律
        —— Nielsen 90-9-1（潜水 90 / 偶尔贡献 9 / 重度贡献 1）、CMX 自有社群实测 2%/5%/93%，
        重度贡献者占 1%~2%、月产 2~4 篇。
    两者结果可以差 5~10 倍，混用是最常见的测算错误。均需用自家数据校准。
    """
    target = float(payload.get("target_notes_per_month", 0) or 0)
    if target <= 0:
        raise ValueError("需要 target_notes_per_month：每月要拿到多少篇合格内容")
    ops = float(payload.get("ops_headcount", 0) or 0)
    mode = str(payload.get("service_mode", "复投池"))
    pool_type = str(payload.get("pool_type", "task_driven")).lower()

    # A 任务驱动池
    act = payload.get("active_rate") or [0.25, 0.40]
    per_active = payload.get("notes_per_active") or [1, 2]
    a_lo = target / (float(act[1]) * float(per_active[1]))
    a_hi = target / (float(act[0]) * float(per_active[0]))
    # B 自然贡献池
    core_ratio = payload.get("core_ratio") or [0.01, 0.02]
    per_core = payload.get("notes_per_core") or [2, 4]
    b_lo = target / (float(core_ratio[1]) * float(per_core[1]))
    b_hi = target / (float(core_ratio[0]) * float(per_core[0]))

    organic = pool_type in ("organic", "自然", "自然贡献池")
    lo, hi = (b_lo, b_hi) if organic else (a_lo, a_hi)

    capacity = {"一次性铺量": (200, 500), "复投池": (80, 150), "深度陪跑": (50, 80)}
    cap = capacity.get(mode, (80, 150))

    out = {
        "目标": f"每月 {target:.0f} 篇合格内容",
        "采用口径": "B 自然贡献池（无寄样、靠自发）" if organic else "A 任务驱动池（有寄样 + 任务 + 陪跑）",
        "A 任务驱动池测算": {
            "假设": f"月活率 {float(act[0]):.0%}~{float(act[1]):.0%}，活跃者月产 {per_active[0]}~{per_active[1]} 篇",
            "需要的注册池": f"{a_lo:.0f} ~ {a_hi:.0f} 人",
            "对应活跃 KOC": f"{target / float(per_active[1]):.0f} ~ {target / float(per_active[0]):.0f} 人",
        },
        "B 自然贡献池测算": {
            "假设": f"重度贡献者占 {float(core_ratio[0]):.0%}~{float(core_ratio[1]):.0%}，"
                  f"月产 {per_core[0]}~{per_core[1]} 篇（Nielsen 90-9-1 / CMX 2%-5%-93%）",
            "需要的注册池": f"{b_lo:.0f} ~ {b_hi:.0f} 人",
            "说明": "自发产出的量级要求的池子大 5~10 倍。**只要你还在寄样、还在派任务，就不要用这一口径倒推。**",
        },
        "本次采用的注册池规模": f"{lo:.0f} ~ {hi:.0f} 人",
        "关键提醒": "「提升整体活跃率」是低效目标（长尾结构决定的）。"
                "真正的高杠杆动作是把活跃层往核心层推 —— 看的指标是「活跃→核心晋级率」和「核心层绝对人数」。",
    }
    if ops > 0:
        out["人力上限校验"] = {
            "服务模式": mode,
            "单运营可承载": f"{cap[0]}~{cap[1]} 人",
            "现有运营人力": ops,
            "人力可承载的活跃 KOC 上限": f"{ops * cap[0]:.0f} ~ {ops * cap[1]:.0f} 人",
            "判定": ("人力够用" if ops * cap[1] >= lo else
                   f"**人力不足**：按 {mode} 模式，{ops:.0f} 个运营最多带 {ops * cap[1]:.0f} 人，"
                   f"而目标需要 {lo:.0f} 人起的池子。要么加人，要么降目标，要么把服务模式降级"
                   f"（深度陪跑→复投池→一次性铺量）并上工具。"),
            "口径": "上表按「关系强度」分档，且假设已有寄样/台账工具。"
                  "**纯手工（Excel + 微信）按 0.6 折算**（复投池 ≈ 50~90 人/人）。",
            "依据": "决定 KOC 池上限的是管理成本，不是预算。人均管理耗时是必须监控的指标。",
        }
    return out


TEMPLATE = {
    "pool": {"target_notes_per_month": 40, "ops_headcount": 1.5, "service_mode": "复投池",
             "pool_type": "task_driven  # 或 organic（无寄样、靠自发）"},
    "score": {
        "name": "KOC-示例",
        "fit": {"score": 21, "reason": "母婴垂类，粉丝 82% 为 25-34 岁女性，与目标人群高度重合"},
        "content": {"score": 14, "reason": "近 30 天更新 9 篇，图文排版稳定，有 1 篇进批次 P95"},
        "audience": {"score": 11, "reason": "评论/点赞 0.06，收藏/点赞 0.18，结构健康"},
        "conversion": {"score": 12, "reason": "有 3 次挂链记录，评论区出现过求链接"},
        "coop": {"score": 8, "reason": "私信 2 小时内回复，接受改稿"},
        "cost": {"score": 7, "reason": "纯佣可谈，只需寄样"},
        "vetoes": {"fake_data": False, "risk_persona": False, "competitor": False,
                   "no_disclosure": False, "prepay_trap": False},
    },
    "rank": {"candidates": ["（把多个 score 结构放进数组）"]},
    "audit": {"like": 800, "comment": 24, "collect": 130, "read": 22000, "fans": 6200, "category": "功能型"},
    "funnel": {"target_notes": 100, "mode": "invite", "C_sample": 53, "F": 0, "I": 0,
               "weeks": 4, "koc_per_op": 150},
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
                lines.append(pad + "  ".join(f"{k}={v}" for k, v in item.items()))
            else:
                lines.append(f"{pad}- {item}")
    else:
        lines.append(f"{pad}{d}")
    return "\n".join(x for x in lines if x.strip())


def main() -> None:
    ap = argparse.ArgumentParser(description="KOC 选人与招募测算工具")
    ap.add_argument("cmd", choices=["score", "rank", "audit", "funnel", "pool", "template"])
    ap.add_argument("--json")
    ap.add_argument("--file")
    ap.add_argument("--text", action="store_true")
    a = ap.parse_args()

    if a.cmd == "template":
        print("FIT-6 评分卡（满分 100）：")
        for key, label, full, hint in DIMENSIONS:
            print(f"  {key:<11}{label:<6}{full:>3} 分   {hint}")
        print("\n一票否决项：")
        for k, v in VETO_LABELS.items():
            print(f"  {k:<14}{v}")
        print("\n分层线：≥80 直通带货位 / 65-79 主力内容位 / 50-64 体验官观察 / <50 不建议\n")
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

    try:
        result = {"score": score_one, "rank": rank_many, "audit": audit_account,
                  "funnel": funnel_plan, "pool": pool_sizing}[a.cmd](payload)
    except ValueError as e:
        print(f"输入有误：{e}", file=sys.stderr)
        sys.exit(2)

    print(to_text(result) if a.text else json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
