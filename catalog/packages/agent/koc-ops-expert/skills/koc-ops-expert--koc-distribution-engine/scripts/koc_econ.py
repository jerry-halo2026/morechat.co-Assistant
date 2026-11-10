#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOC 分销单位经济模型 —— 寄样、佣金、阶梯与盈亏平衡的测算工具。

这个脚本只做算术和一致性检查，**判断和取舍必须由专家自己给出**。
所有默认值都是行业经验值，必须用用户自己的数据替换后再进入决策。

子命令：
    sample      寄样经济模型：单篇有效内容成本、盈亏平衡篇均单量、直接 ROI、可承受寄样量
    commission  佣金上限与结构分解：c_max、每 100 元 GMV 的钱去哪了
    tier        阶梯佣金模拟：给定阶梯与 GMV 分布，算综合佣金率与边际激励效果
    template    打印输入模板

用法：
    python3 koc_econ.py sample --json '{...}'
    python3 koc_econ.py sample --file /tmp/econ.json --text
    python3 koc_econ.py commission --json '{...}' --text
    python3 koc_econ.py tier --json '{...}' --text
    python3 koc_econ.py template

核心公式（口径见 references/unit-economics.md）：
    C_sample   = C_goods + C_ship                         单件寄样总成本
    r_eff      = r_pub × r_qc                             有效出稿率（出稿率的分母是「签收数」）
    C_note_eff = C_sample/r_deliver/r_eff + F + I         单篇有效内容成本（稿费后置）
               = (C_sample/r_deliver + F + I) / r_eff     （稿费前置）
                 r_deliver 默认 1.0；设成实际签收率可把「寄出未签收」的损耗也算进来
    g          = (1−rr)×AOV×(m−c−f) − rr×C_ret            单笔净毛利
    O*         = C_note_eff / g                           盈亏平衡的篇均归因订单数
    ROI_direct = O / O*                                   直接归因 ROI
    K          = C_sample + r_eff×(F+I)                   每个样品摊到的固定成本（稿费后置）
    take       = (c+tz)×(1+alliance) + f                  从 GMV 里被拿走的总比例
    c_max      = { m − f − [K/n_exp + rr×C_ret]/((1−rr)×AOV) } / (1+alliance) − tz
                 ← 必须含 F/I/团长费/联盟费，漏掉任何一项都会把 c_max 系统性高估
"""

from __future__ import annotations

import argparse
import json
import sys

# --------------------------------------------------------------------------
# 默认值：全部是【经验值/待校准】，只用于用户没给数时先跑通模型
# --------------------------------------------------------------------------

DEFAULTS = {
    "C_goods": None, "C_ship": 8.0, "F": 0.0, "I": 0.0,
    "r_pub": 0.55, "r_qc": 0.85,
    "AOV": None, "m": None, "c": 0.20, "f": 0.02,
    "rr": 0.10, "C_ret": 8.0,
    "O": None, "fee_timing": "post",
}

DEFAULT_NOTES = {
    "C_ship": "单件寄样物流 8 元（含仓内操作分摊，经验值）",
    "r_pub": "出稿率 55%（纯寄样定向邀约区间 55%~75% 的下沿，经验值，必须用首批 100 样实测替换）",
    "r_qc": "合格率 85%（经验值）",
    "c": "达人佣金率 20%（各类目差异极大：3C 5~10%、食品 10~20%、服饰 15~25%、美妆 20~30%、保健 25~50%）",
    "f": "平台技术服务费率 2%（占 GMV。注意：抖音精选联盟按「推广费×10%」计，脚本会另算）",
    "rr": "退货退款率 10%（服饰鞋类通常远高于此）",
    "C_ret": "单笔退货逆向成本 8 元（经验值）",
}


def _num(v, name):
    if v is None:
        raise ValueError(f"缺少必填参数：{name}")
    return float(v)


def _merge(payload: dict) -> dict:
    d = dict(DEFAULTS)
    d.update({k: v for k, v in payload.items() if v is not None})
    return d


RANGES = {
    "rr": (0.0, 0.99, "退货率必须在 0~0.99 之间"),
    "m": (-1.0, 1.0, "毛利率必须 ≤1"),
    "c": (0.0, 1.0, "佣金率必须在 0~1 之间"),
    "f": (0.0, 1.0, "平台费率必须在 0~1 之间"),
    "r_pub": (0.0001, 1.0, "出稿率必须在 0~1 之间（0 表示无人出稿，模型无意义）"),
    "r_qc": (0.0001, 1.0, "合格率必须在 0~1 之间"),
}


def _validate(p: dict) -> None:
    """值域校验：错误的输入会让模型给出方向相反的结论，必须拦在计算之前。"""
    for k, (lo, hi, msg) in RANGES.items():
        if k in p and p[k] is not None:
            v = float(p[k])
            if not (lo <= v <= hi):
                raise ValueError(f"{k}={v} 越界：{msg}")
    for k in ("AOV", "C_goods", "C_ship", "F", "I", "C_ret"):
        if p.get(k) is not None and float(p[k]) < 0:
            raise ValueError(f"{k} 不能为负数")
    if p.get("AOV") is not None and float(p["AOV"]) <= 0:
        raise ValueError("AOV（客单价）必须大于 0")


def unit_margin(p: dict) -> float:
    """单笔净毛利 g：扣掉佣金、平台费、退货损耗之后，一单真正落袋多少。"""
    rr = float(p["rr"])
    return (1 - rr) * float(p["AOV"]) * (float(p["m"]) - float(p["c"]) - float(p["f"])) - rr * float(p["C_ret"])


def sample_model(payload: dict) -> dict:
    p = _merge(payload)
    for k in ("C_goods", "AOV", "m"):
        _num(p.get(k), k)
    _validate(p)

    c_sample = float(p["C_goods"]) + float(p["C_ship"])
    r_pub, r_qc = float(p["r_pub"]), float(p["r_qc"])
    r_eff = r_pub * r_qc
    F, I = float(p["F"]), float(p["I"])
    post = str(p.get("fee_timing", "post")).lower() != "pre"

    if r_eff <= 0:
        raise ValueError("有效出稿率为 0，模型无意义：先解决履约问题再谈成本。")

    # r_deliver = 签收率。默认 1.0，即只把「已签收样品」的成本算进来（与出稿率的分母口径一致）。
    # 想把「寄出但没签收」的损耗也算进来，就把它设成你的实际签收率（常见 0.95）。
    r_deliver = float(payload.get("r_deliver", 1.0) or 1.0)
    if not (0 < r_deliver <= 1):
        raise ValueError("r_deliver（签收率）必须在 0~1 之间")
    c_sample_eff = c_sample / r_deliver
    c_note = c_sample_eff / r_eff + F + I if post else (c_sample_eff + F + I) / r_eff
    if c_note <= 0:
        raise ValueError("单篇有效内容成本为 0：样品成本、稿费、激励不可能全为 0，请检查输入。")
    g = unit_margin(p)

    out = {
        "输入": {
            "单件寄样总成本 C_sample": round(c_sample, 2),
            "签收率 r_deliver": r_deliver,
            "出稿率 r_pub": r_pub, "合格率 r_qc": r_qc, "有效出稿率 r_eff": round(r_eff, 4),
            "稿费 F": F, "激励 I": I, "稿费支付方式": "后置" if post else "前置",
            "客单价 AOV": float(p["AOV"]), "毛利率 m": float(p["m"]),
            "达人佣金率 c": float(p["c"]), "平台费率 f": float(p["f"]),
            "退货率 rr": float(p["rr"]), "单笔逆向成本 C_ret": float(p["C_ret"]),
        },
        "结果": {
            "单篇有效内容成本 C_note_eff": round(c_note, 2),
            "单笔净毛利 g": round(g, 2),
        },
        "警告": [],
        "结论": "",
    }

    if g <= 0:
        out["结果"]["盈亏平衡篇均订单数 O*"] = None
        out["警告"].append(
            f"单笔净毛利为 {g:.2f} 元（≤0）：把佣金 {p['c']:.0%} 和平台费 {p['f']:.0%} 扣掉之后这单本身就在亏钱。"
            "**先降佣金率或提客单价/毛利率，再谈寄样规模。**")
        out["结论"] = "KILL：当前佣金结构下，卖得越多亏得越多。"
        return out

    o_star = c_note / g
    out["结果"]["盈亏平衡篇均订单数 O*"] = round(o_star, 2)
    out["结果"]["口径说明"] = "O* = 每篇合格内容至少要带来这么多归因订单，寄样才回本（只算直接归因，不含品牌增量与内容复用）"

    O = p.get("O")
    if O is not None:
        O = float(O)
        roi = O / o_star
        out["结果"]["实际篇均订单数 O"] = O
        out["结果"]["直接归因 ROI"] = round(roi, 2)
        if roi >= 1.5:
            out["结论"] = f"扩量 Scale：直接归因 ROI {roi:.2f}，已跑通，寄样量只受现金流与运营人力限制。"
        elif roi >= 1.0:
            out["结论"] = f"谨慎放量 Hold：ROI {roi:.2f} 刚过线，先把有效出稿率抬上去再扩量。"
        elif roi >= 0.6:
            out["结论"] = (f"修模 Fix：直接归因 ROI {roi:.2f} 未回本。**不要扩量**，优先修有效出稿率"
                          f"（当前 {r_eff:.0%}），其次压佣金或提客单。")
        else:
            out["结论"] = (f"存疑 Review：直接归因 ROI {roi:.2f}。先别急着停 —— 直接归因会系统性低估种草效果"
                          f"（15 天窗口截断、跨端断链、最后点击把功劳给了搜索广告）。"
                          f"按下面三项逐一核对，三项都补不上才判止损。")
        if roi < 1.0:
            out["判止损前必须核对的三块"] = [
                "增量：品牌词/品类词搜索量在投放后 2~4 周有没有起来？做过 holdout 或时间序列断点吗？",
                "内容复用：合格内容有没有拿到二次使用授权、有没有喂给投流（聚光/千川）？复用摊薄后单篇成本 = 单篇成本 ÷ (1+复用深度)。",
                "搜索承接：被种草的人搜过来之后，搜索结果页和商详有没有接住？承接不住时砍 KOC 预算是砍错了地方。",
            ]

    # 敏感性：有效出稿率对成本是倒数级敏感。网格里必须包含用户当前值，
    # 否则会出现「建议把履约率往下调」这种荒谬解读。
    grid = [(0.40, 0.75), (0.55, 0.80), (0.70, 0.85), (0.85, 0.90)]
    grid.append((r_pub, r_qc))
    seen, sens = set(), []
    for rp, rq in sorted(grid, key=lambda x: x[0] * x[1]):
        re_ = rp * rq
        if round(re_, 4) in seen:
            continue
        seen.add(round(re_, 4))
        cn = c_sample_eff / re_ + F + I if post else (c_sample_eff + F + I) / re_
        sens.append({
            "出稿率": round(rp, 3), "合格率": round(rq, 3), "有效出稿率": round(re_, 3),
            "单篇有效内容成本": round(cn, 1),
            "盈亏平衡 O*": round(cn / g, 2),
            "当前": "← 你现在在这里" if abs(re_ - r_eff) < 1e-9 else "",
        })
    out["有效出稿率敏感性"] = sens
    above = [s for s in sens if s["有效出稿率"] > round(r_eff, 3)]
    cur_cost = c_note - (F + I) + (F + I)  # 当前单篇成本
    if above:
        tgt = above[-1]
        out["敏感性结论"] = (f"你当前有效出稿率 {r_eff:.0%}、单篇 {cur_cost:.1f} 元。"
                        f"若提到 {tgt['有效出稿率']:.0%}，单篇降到 {tgt['单篇有效内容成本']} 元"
                        f"（降 {(1 - tgt['单篇有效内容成本'] / cur_cost):.0%}），"
                        f"盈亏平衡从 {o_star:.2f} 单/篇降到 {tgt['盈亏平衡 O*']} 单/篇。"
                        "**履约机制的收益大于任何议价。**")
    else:
        out["敏感性结论"] = (f"你当前有效出稿率 {r_eff:.0%} 已在高位，继续压履约的边际收益有限。"
                        "**下一步的杠杆在内容复用（素材银行）与选人，不在履约。**")

    # 后置稿费划算区间：F < C_sample × (1/r_old − 1/r_new)
    r_new = min(0.90, r_eff + 0.25)
    if r_new > r_eff:
        f_max = c_sample_eff * (1 / r_eff - 1 / r_new)
        out["后置稿费建议"] = {
            "假设": f"若小额后置稿费能把有效出稿率从 {r_eff:.0%} 提到 {r_new:.0%}",
            "单篇后置稿费上限": round(f_max, 1),
            "说明": "低于这个数就比不给稿费更省。稿费必须发布验收后再付，前置付款会降低履约率。",
        }

    # 预算约束下的可承受寄样量
    B = payload.get("budget_sample")
    if B:
        per = c_sample + (F + I) * r_eff * r_deliver if post else c_sample + F + I
        out["预算测算"] = {
            "寄样预算": float(B),
            "单个样品全成本": round(per, 2),
            "可寄样人数": int(float(B) // per),
            "预计合格内容篇数": int(float(B) // per * r_eff),
            "提醒": "寄样量还受运营人力限制：单运营可管理活跃 KOC 按关系强度分档（已有工具）——"
                   "一次性铺量 200~500 / 复投池 80~150 / 深度陪跑 50~80；纯手工按 0.6 折算。",
        }

    if r_eff < 0.45:
        out["警告"].append(f"有效出稿率 {r_eff:.0%} 低于 45% 红线：停止扩大寄样，改稿费后置 / 加履约承诺函 / 收紧准入。")
    if float(p["rr"]) > 0.25:
        out["警告"].append(f"退货率 {float(p['rr']):.0%} 偏高：先压退货（尺码表/材质说明/预期管理），再谈佣金率。")
    if float(p["AOV"]) and c_sample / float(p["AOV"]) > 0.5:
        out["警告"].append("样品成本超过客单价的 50%：低客单品类做纯佣寄样通常不成立，考虑改小样/试用装或按篇采买内容。")
    return out


def commission_model(payload: dict) -> dict:
    """佣金上限 c_max + 每 100 元 GMV 的分配结构。

    两处口径必须一致（这是最容易出错的地方）：
      · c_max 与分配表用**同一套费率**：达人佣金 c、团长费 tz、联盟技术服务费（按推广费计）、
        平台技术服务费 f（按 GMV 计），并且都扣退货损耗；
      · 稿费 F 与激励 I **必须计入 c_max**（后置发放时按有效出稿率摊到每个样品上），
        漏掉它们会把 c_max 系统性高估。

    推导（K = 每个样品摊到的固定成本）：
        K = C_sample + r_eff × (F + I)        （稿费后置；前置则 K = C_sample + F + I）
        take = (c + tz) × (1 + alliance) + f  （从 GMV 里被拿走的总比例）
        盈亏平衡： n_exp × [(1−rr)·AOV·(m − take) − rr·C_ret] = K
        → c_max = { m − f − [K/n_exp + rr·C_ret] / ((1−rr)·AOV) } / (1 + alliance) − tz
    """
    p = _merge(payload)
    for k in ("AOV", "m"):
        _num(p.get(k), k)
    _validate(p)
    aov, m, f = float(p["AOV"]), float(p["m"]), float(p["f"])
    rr, c_ret = float(p["rr"]), float(p["C_ret"])
    c_sample = float(p["C_goods"] or 0) + float(p["C_ship"] or 0)
    F, I = float(p["F"]), float(p["I"])
    post = str(p.get("fee_timing", "post")).lower() != "pre"
    r_eff = float(p["r_pub"]) * float(p["r_qc"])
    n_exp = float(payload.get("n_exp") or 0)

    c = float(p["c"])
    tz = float(payload.get("tuanzhang_rate") or 0)               # 团长服务费率（占 GMV）
    alliance = float(payload.get("alliance_fee_on_promo") or 0)  # 联盟技术服务费率（占「推广费」）
    if payload.get("store_fee_on_gmv") is not None:
        # 兼容旧字段：与 f 合并为单一「按 GMV 计的平台技术服务费」，避免两处口径打架
        f = f + float(payload["store_fee_on_gmv"])

    K = c_sample + r_eff * (F + I) if post else c_sample + F + I

    out = {"输入": {"客单价": aov, "毛利率": m, "平台技术服务费率(占GMV)": round(f, 4),
                  "团长服务费率": tz, "联盟技术服务费率(占推广费)": alliance,
                  "退货率": rr, "单件寄样成本": round(c_sample, 2),
                  "稿费 F": F, "激励 I": I, "有效出稿率 r_eff": round(r_eff, 4),
                  "每样品摊到的固定成本 K": round(K, 2),
                  "单样期望订单数 n_exp": n_exp or "未提供"},
           "警告": []}

    if n_exp > 0:
        c_max = (m - f - (K / n_exp + rr * c_ret) / ((1 - rr) * aov)) / (1 + alliance) - tz
        out["可承受最高佣金率 c_max"] = round(c_max, 4)
        out["c_max 口径"] = (f"已计入：样品 {c_sample:.0f} 元、稿费 {F:.0f} 元、激励 {I:.0f} 元"
                           f"（{'按有效出稿率摊薄' if post else '前置全额计入'}）、团长费 {tz:.0%}、"
                           f"联盟费率 {alliance:.0%}（按推广费计）、平台费 {f:.1%}、退货损耗。"
                           "n_exp = 有效出稿率 × 篇均订单数。")
        if c_max <= 0:
            out["警告"].append("c_max ≤ 0：这个品在当前样品成本与单量假设下，给任何佣金都不回本。"
                              "→ 改按篇采买内容（不给佣金）或换品。")
        else:
            band = payload.get("category_band")
            if band and len(band) == 2 and c_max < float(band[0]):
                out["警告"].append(
                    f"c_max {c_max:.1%} 低于类目常见佣金下限 {float(band[0]):.0%}："
                    "该品类不适合做 CPS 型 KOC 铺量，改「内容采买 + 授权复用」模式。")

    # 每 100 元 GMV 的钱去哪了（下单口径，六项之和恰为 100）
    cogs = 1 - m
    alliance_cost = (c + tz) * alliance
    take = c + tz + alliance_cost + f
    ret_loss = rr * (m - take) + rr * c_ret / aov      # 退货吃掉的毛利 + 逆向成本
    留存 = (1 - rr) * (m - take) - rr * c_ret / aov     # = g_full / AOV，与 c_max 同源
    breakdown = [
        {"项": "商品成本与履约 COGS", "占 GMV": round(cogs, 4), "每 100 元": round(cogs * 100, 2)},
        {"项": "达人佣金", "占 GMV": round(c, 4), "每 100 元": round(c * 100, 2)},
        {"项": "团长/服务商服务费", "占 GMV": round(tz, 4), "每 100 元": round(tz * 100, 2)},
        {"项": "联盟技术服务费（按推广费计）", "占 GMV": round(alliance_cost, 4),
         "每 100 元": round(alliance_cost * 100, 2)},
        {"项": "平台技术服务费（按 GMV 计）", "占 GMV": round(f, 4), "每 100 元": round(f * 100, 2)},
        {"项": f"退货净损（退货率 {rr:.0%}）", "占 GMV": round(ret_loss, 4), "每 100 元": round(ret_loss * 100, 2)},
        {"项": "品牌留存（未扣寄样/内容/人力）", "占 GMV": round(留存, 4), "每 100 元": round(留存 * 100, 2)},
    ]
    out["每 100 元 GMV 的分配"] = breakdown
    out["合计校验"] = f"{sum(x['每 100 元'] for x in breakdown):.2f} 元（应为 100.00）"
    out["注意"] = (f"这里的「品牌留存」{留存:.1%} 只扣到平台与退货，**还没扣寄样、内容与人力**。"
                 f"把单个样品摊到的固定成本 K={K:.0f} 元算进来才是真账 —— 用 sample 子命令看 O*。")
    if 留存 <= 0:
        out["警告"].append("品牌留存为负：这笔生意在成交那一刻就是亏的，且还没算寄样与人力。")
    elif 留存 < 0.10:
        out["警告"].append(f"品牌留存仅 {留存:.1%}，扣掉寄样与人力后大概率为负。谨慎放量。")
    out["提醒"] = ("平台费率会变且按账户分层：抖音精选联盟已从统一费率改为按合规与经营表现分层，"
                 "签合同前必须登录后台查本月适用费率。")
    return out


def tier_model(payload: dict) -> dict:
    """阶梯佣金模拟：超额累进（marginal）vs 全额跳档（total）。"""
    raw = payload.get("tiers", [])
    if not raw:
        raise ValueError("需要 tiers：[{\"from\": 0, \"rate\": 0.10}, {\"from\": 3000, \"rate\": 0.15}]")
    tiers = []
    for i, t in enumerate(raw):
        if "rate" not in t:
            raise ValueError(f"第 {i + 1} 档缺少 rate 字段")
        rate = float(t["rate"])
        frm = float(t.get("from", 0))
        if not (0 <= rate <= 1):
            raise ValueError(f"第 {i + 1} 档 rate={rate} 越界：佣金率必须在 0~1 之间")
        if frm < 0:
            raise ValueError(f"第 {i + 1} 档 from={frm} 不能为负")
        tiers.append({"from": frm, "rate": rate})
    tiers.sort(key=lambda t: t["from"])
    mode = str(payload.get("mode", "marginal")).lower()
    samples = [float(x) for x in (payload.get("gmv_points") or [1000, 3000, 5000, 10000, 30000])
               if float(x) >= 0]
    if not samples:
        raise ValueError("gmv_points 必须包含至少一个非负数值")

    first_from = tiers[0]["from"]

    def cost(gmv: float) -> float:
        gmv = max(0.0, float(gmv))
        if gmv < first_from:          # 未达首档门槛：不计佣（两种模式一致）
            return 0.0
        if mode == "total":
            rate = tiers[0]["rate"]
            for t in tiers:
                if gmv >= t["from"]:
                    rate = t["rate"]
            return gmv * rate
        total = 0.0
        for i, t in enumerate(tiers):
            lo = t["from"]
            hi = tiers[i + 1]["from"] if i + 1 < len(tiers) else float("inf")
            if gmv > lo:
                total += (min(gmv, hi) - lo) * t["rate"]
        return total

    rows = []
    for gmv in samples:
        c_ = cost(gmv)
        rows.append({
            "GMV": gmv,
            "佣金支出": round(c_, 2),
            "综合佣金率": round(c_ / gmv, 4) if gmv else 0,
            "该档边际佣金率": round((cost(gmv * 1.1) - c_) / (gmv * 0.1), 4) if gmv else 0,
        })
    out = {
        "模式": "超额累进（推荐）" if mode != "total" else "全额跳档（有悬崖效应，慎用）",
        "阶梯": tiers,
        "测算": rows,
    }
    if mode == "total":
        # 检查悬崖：跨档时达人收入是否出现"多卖反而赚更少"
        cliffs = []
        for i in range(1, len(tiers)):
            b = float(tiers[i]["from"])
            before, after = cost(b - 1), cost(b)
            cliffs.append({"档位门槛": b, "临界前佣金": round(before, 2), "临界后佣金": round(after, 2),
                           "跳升": round(after - before, 2)})
        out["悬崖效应"] = cliffs
        out["建议"] = ("全额跳档会制造「刷单凑门槛」的动机，也会让差一点点的达人直接放弃。"
                     "**优先用超额累进**：基础佣金保底，超额部分给高佣，把边际激励给到增量。")
    else:
        out["建议"] = "超额累进没有悬崖，达人每多卖一单都有正向收益；门槛数量建议 3~4 档，跨度不要太大。"
    return out


TEMPLATE = {
    "sample": {
        "C_goods": 45, "C_ship": 8, "F": 0, "I": 0, "fee_timing": "post",
        "r_pub": 0.55, "r_qc": 0.85,
        "AOV": 129, "m": 0.45, "c": 0.20, "f": 0.02, "rr": 0.10, "C_ret": 8,
        "O": 2.5, "budget_sample": 30000,
    },
    "commission": {
        "C_goods": 45, "C_ship": 8, "AOV": 129, "m": 0.45, "f": 0.02, "rr": 0.10, "C_ret": 8,
        "n_exp": 1.5, "c": 0.20, "tuanzhang_rate": 0.05,
        "alliance_fee_on_promo": 0.10, "store_fee_on_gmv": 0.0,
        "category_band": [0.15, 0.25],
    },
    "tier": {
        "mode": "marginal",
        "tiers": [{"from": 0, "rate": 0.10}, {"from": 3000, "rate": 0.15}, {"from": 10000, "rate": 0.20}],
        "gmv_points": [1000, 3000, 5000, 10000, 30000],
    },
}

FIELD_HELP = """字段说明（全部为小数，如 0.20 表示 20%）：
  C_goods  单件商品成本（COGS，含包材，不是零售价）    C_ship  单件寄样物流+仓内操作
  F        单篇稿费（纯佣为 0）                        I       单人激励成本（红包/抽奖期望值）
  fee_timing  稿费支付方式 post=发布验收后付（推荐）/ pre=前置付
  r_pub    出稿率＝发布篇数÷签收人数（分母是签收，不是寄出）
  r_qc     合格率＝通过 brief 验收篇数÷发布篇数
  AOV      客单价（实付口径）                          m       毛利率（扣 COGS 与履约后）
  c        达人佣金率                                  f       平台技术服务费率（占 GMV）
  rr       退货退款率                                  C_ret   单笔退货逆向成本
  O        篇均归因订单数（口径B：归因订单总数÷发布篇数，不是"出单达人比例"）
  n_exp    单个样品期望带来的订单数 = 有效出稿率 × 篇均订单数
  budget_sample  寄样预算
"""


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
    ap = argparse.ArgumentParser(description="KOC 分销单位经济模型")
    ap.add_argument("cmd", choices=["sample", "commission", "tier", "template"])
    ap.add_argument("--json", help="JSON 字符串")
    ap.add_argument("--file", help="JSON 文件路径")
    ap.add_argument("--text", action="store_true", help="输出为可读文本而非 JSON")
    a = ap.parse_args()

    if a.cmd == "template":
        print(FIELD_HELP)
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
        fn = {"sample": sample_model, "commission": commission_model, "tier": tier_model}[a.cmd]
        result = fn(payload)
    except ValueError as e:
        print(f"输入有误：{e}", file=sys.stderr)
        sys.exit(2)

    print(to_text(result) if a.text else json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
