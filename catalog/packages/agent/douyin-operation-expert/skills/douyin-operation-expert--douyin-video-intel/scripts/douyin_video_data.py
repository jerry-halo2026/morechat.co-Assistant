#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频综合数据抓取器
======================
输入：抖音视频链接 / 短链 / 整段分享口令 / aweme_id
输出：结构化 JSON + Markdown 数据卡（含派生指标与对标口径）

零依赖：仅使用 Python 标准库（urllib / re / json），无需 API Key、无需登录。
数据源：抖音官方分享页 https://www.iesdouyin.com/share/video/{aweme_id}/
       内嵌的 window._ROUTER_DATA（服务端渲染数据，公开可读）

用法:
    python douyin_video_data.py "<链接或分享口令或ID>"
    python douyin_video_data.py "<...>" --json out.json
    python douyin_video_data.py "<...>" --json out.json --md out.md
    python douyin_video_data.py "<...>" --raw raw.json     # 保存接口原始 item 便于排查
"""

import sys
import os
import re
import json
import time
import argparse
import urllib.request
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
ROUTER_RE = re.compile(r"window\._ROUTER_DATA\s*=\s*(.*?)</script>", re.S)
TIMEOUT = 25

# 抖音过滤原因中文解释
FILTER_REASON_CN = {
    "SYSTEM_ITEM_NOT_EXIST": "作品不存在（ID 错误或已被彻底删除）",
    "status_self_see": "作品已被作者设为仅自己可见，或已被删除",
    "status_audit_self_see": "作品审核未通过，当前仅作者本人可见",
    "status_friend_see": "作品设为仅好友可见",
    "status_reviewing": "作品审核中，暂不可公开访问",
    "status_delete": "作品已被删除",
    "SYSTEM_ITEM_DELETED": "作品已被删除",
}


# --------------------------------------------------------------------------
# 网络
# --------------------------------------------------------------------------
def _open(url, allow_redirects=True):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA_MOBILE,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )
    if allow_redirects:
        return urllib.request.urlopen(req, timeout=TIMEOUT)
    opener = urllib.request.build_opener(_NoRedirect)
    return opener.open(req, timeout=TIMEOUT)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# --------------------------------------------------------------------------
# 输入解析
# --------------------------------------------------------------------------
def extract_aweme_id(raw_input):
    """从任意形态的用户输入中解出 aweme_id。

    支持：
      - 整段分享口令: "9.92 复制打开抖音，看看【xxx】 https://v.douyin.com/xxxx/ 06/24 MwF:/"
      - 短链: https://v.douyin.com/xxxx/
      - 长链: https://www.douyin.com/video/7xxxxx  /note/  /slides/  ?modal_id=
      - iesdouyin 分享链: https://www.iesdouyin.com/share/video/7xxxxx/
      - 纯数字 ID: 7649236420993543269
    """
    text = (raw_input or "").strip()

    # 1) 纯数字 ID
    if re.fullmatch(r"\d{15,25}", text):
        return text, text

    # 2) 从文本里捞出第一个 URL
    m = re.search(r"https?://[^\s\u4e00-\u9fff\"'<>()（），,]+", text)
    if not m:
        raise ValueError(
            "未能从输入中识别出抖音链接或视频 ID。\n"
            "请提供：抖音分享口令全文 / v.douyin.com 短链 / www.douyin.com/video/... 链接 / 纯数字 aweme_id"
        )
    url = m.group(0).rstrip(".,;)）】")

    # 3) 长链直接正则
    vid = _vid_from_url(url)
    if vid:
        return vid, url

    # 4) 短链跟随 302
    try:
        resp = _open(url)
        final = resp.geturl()
    except Exception as e:
        raise ValueError(f"短链解析失败：{type(e).__name__}: {e}")
    vid = _vid_from_url(final)
    if not vid:
        raise ValueError(f"短链已跳转到 {final}，但其中未包含视频 ID（可能是主页链接或已失效）")
    return vid, url


def _vid_from_url(url):
    for pat in (
        r"/(?:video|note|slides)/(\d{15,25})",
        r"/share/video/(\d{15,25})",
        r"[?&]modal_id=(\d{15,25})",
        r"/aweme/v1/play/\?video_id=.*?(\d{15,25})",
    ):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


# --------------------------------------------------------------------------
# 详情抓取
# --------------------------------------------------------------------------
def fetch_item(aweme_id, retries=3):
    """抓取并返回 (item, filter_list)。item 为 None 时看 filter_list 判断原因。"""
    url = f"https://www.iesdouyin.com/share/video/{aweme_id}/"
    last_err = None
    for attempt in range(retries):
        try:
            html = _open(url).read().decode("utf-8", "ignore")
            m = ROUTER_RE.search(html)
            if not m:
                last_err = "页面中未找到 _ROUTER_DATA（可能触发风控或页面改版）"
                time.sleep(1.5 * (attempt + 1))
                continue
            data = json.loads(m.group(1).strip())
            info = None
            for _k, v in (data.get("loaderData") or {}).items():
                if isinstance(v, dict) and "videoInfoRes" in v:
                    info = v["videoInfoRes"]
                    break
            if info is None:
                last_err = "响应结构中未找到 videoInfoRes"
                time.sleep(1.5 * (attempt + 1))
                continue
            items = info.get("item_list") or []
            if items:
                return items[0], []
            return None, info.get("filter_list") or []
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"抓取失败（已重试 {retries} 次）：{last_err}")


# --------------------------------------------------------------------------
# 字段整理
# --------------------------------------------------------------------------
def _int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _pick_no_watermark(item):
    """无水印直链：把 playwm 换成 play。链接有效期约 24 小时。"""
    try:
        urls = item["video"]["play_addr"]["url_list"]
    except (KeyError, TypeError):
        return None, []
    cleaned = [u.replace("playwm", "play") for u in urls if u]
    return (cleaned[0] if cleaned else None), cleaned


def normalize(item, aweme_id, source_url):
    st = item.get("statistics") or {}
    au = item.get("author") or {}
    vd = item.get("video") or {}
    mu = item.get("music") or {}

    digg = _int(st.get("digg_count"))
    comment = _int(st.get("comment_count"))
    share = _int(st.get("share_count"))
    collect = _int(st.get("collect_count"))
    play = _int(st.get("play_count"))  # 抖音公开接口恒为 0，不代表真实播放量

    create_ts = _int(item.get("create_time"))
    duration_ms = _int(vd.get("duration"))

    # 话题标签
    topics, mentions = [], []
    for te in item.get("text_extra") or []:
        name = te.get("hashtag_name")
        if name:
            topics.append(name)
        if te.get("type") == 0 and te.get("user_id"):
            nick = (te.get("caption") or "").lstrip("@")
            if nick:
                mentions.append(nick)
    for cha in item.get("cha_list") or []:
        n = cha.get("cha_name")
        if n and n not in topics:
            topics.append(n)

    nw_url, nw_all = _pick_no_watermark(item)

    # 图文帖
    images = []
    for img in item.get("images") or []:
        ul = (img or {}).get("url_list") or []
        if ul:
            images.append(ul[-1])

    aweme_type = _int(item.get("aweme_type"))
    is_gallery = bool(images) or aweme_type in (68, 2)

    data = {
        "aweme_id": aweme_id,
        "source_url": source_url,
        "canonical_url": f"https://www.douyin.com/video/{aweme_id}",
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "content_type": "图文" if is_gallery else "视频",
        "title_desc": item.get("desc") or "",
        "topics": topics,
        "mentions": mentions,
        "publish_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(create_ts)) if create_ts else None,
        "publish_ts": create_ts or None,
        "days_online": round((time.time() - create_ts) / 86400, 1) if create_ts else None,
        "statistics": {
            "digg_count": digg,
            "comment_count": comment,
            "share_count": share,
            "collect_count": collect,
            "play_count_raw": play,
            "play_count_available": play > 0,
            "total_interaction": digg + comment + share + collect,
        },
        "author": {
            "nickname": au.get("nickname") or "",
            "douyin_id": au.get("unique_id") or au.get("short_id") or "",
            "sec_uid": au.get("sec_uid") or "",
            "signature": au.get("signature") or "",
            "follower_count": _int(au.get("mplatform_followers_count")) or None,
            "following_count": _int(au.get("following_count")) or None,
            "aweme_count": _int(au.get("aweme_count")) or None,
            "total_favorited": _int(au.get("favoriting_count")) or None,
            "homepage": f"https://www.douyin.com/user/{au.get('sec_uid')}" if au.get("sec_uid") else None,
        },
        "media": {
            "duration_ms": duration_ms,
            "duration_readable": _fmt_dur(duration_ms),
            "width": _int(vd.get("width")) or None,
            "height": _int(vd.get("height")) or None,
            "cover": ((vd.get("cover") or {}).get("url_list") or [None])[0],
            "no_watermark_url": nw_url,
            "no_watermark_url_all": nw_all,
            "image_count": len(images),
            "images": images,
            "note": "无水印直链由抖音 CDN 签发，有效期约 24 小时，需尽快下载",
        },
        "music": {
            "title": mu.get("title") or "",
            "author": mu.get("author") or "",
        },
    }
    data["derived"] = compute_derived(data)
    return data


def _fmt_dur(ms):
    if not ms:
        return None
    s = ms / 1000.0
    return f"{int(s // 60)}分{s % 60:.1f}秒" if s >= 60 else f"{s:.1f}秒"


# --------------------------------------------------------------------------
# 派生指标与对标诊断
# --------------------------------------------------------------------------
# 黄金数据标准（专家方法论）：点赞率 ~3%、分享率 ~1%、收藏率 ~1%
# 以「点赞 = 100」为基数换算成结构性健康线，规避播放量不可得的问题：
#   分享/点赞 ≈ 1%/3% ≈ 0.33   收藏/点赞 ≈ 1%/3% ≈ 0.33
#   评论/点赞 行业常见健康区间 ≈ 0.08 ~ 0.25
BENCH = {
    "share_ratio": {"good": 0.33, "warn": 0.15, "label": "分享/点赞", "meaning": "传播系数：内容能否被主动转发出圈"},
    "collect_ratio": {"good": 0.33, "warn": 0.12, "label": "收藏/点赞", "meaning": "价值系数：内容是否有干货/工具价值"},
    "comment_ratio": {"good": 0.15, "warn": 0.05, "label": "评论/点赞", "meaning": "互动系数：是否引发讨论与情绪共鸣"},
}


def compute_derived(d):
    st = d["statistics"]
    digg = st["digg_count"]
    out = {
        "play_count_note": (
            "抖音公开接口不返回真实播放量（play_count 恒为 0）。"
            "如需播放量/完播率/5秒完播，请到创作者服务中心-作品数据后台读取，"
            "本工具给出的是不依赖播放量的结构性比率。"
        ),
        "ratios": {},
        "diagnosis": [],
        "engagement_level": None,
    }
    if digg <= 0:
        out["diagnosis"].append(
            {"metric": "点赞", "status": "数据不足", "detail": "点赞为 0，无法计算结构性比率；该作品可能刚发布或未获推荐流。"}
        )
        return out

    vals = {
        "share_ratio": st["share_count"] / digg,
        "collect_ratio": st["collect_count"] / digg,
        "comment_ratio": st["comment_count"] / digg,
    }
    for key, v in vals.items():
        b = BENCH[key]
        if v >= b["good"]:
            status, advice = "优秀", "保持当前内容结构，可作为爆款模板复用。"
        elif v >= b["warn"]:
            status, advice = "达标", "尚在健康区间，可针对性加强以冲击优秀线。"
        else:
            status, advice = "偏低", _advice(key)
        out["ratios"][key] = {
            "label": b["label"],
            "value": round(v, 4),
            "value_pct": f"{v * 100:.1f}%",
            "benchmark_good": b["good"],
            "meaning": b["meaning"],
            "status": status,
        }
        out["diagnosis"].append({"metric": b["label"], "status": status, "detail": advice})

    # 互动量级判定
    total = st["total_interaction"]
    for lo, name in ((100000, "S级·平台级爆款"), (10000, "A级·爆款"), (3000, "B级·小爆"), (500, "C级·合格"), (0, "D级·未起量")):
        if total >= lo:
            out["engagement_level"] = f"{name}（总互动 {total:,}）"
            break

    # 日均互动
    if d.get("days_online") and d["days_online"] > 0:
        out["interaction_per_day"] = round(total / d["days_online"], 1)

    # 粉丝转化视角
    fc = (d.get("author") or {}).get("follower_count")
    if fc and fc > 0:
        r = digg / fc
        out["digg_vs_follower"] = {
            "value": round(r, 4),
            "detail": (
                "点赞已超过粉丝量，说明这条内容主要吃到了推荐流（破圈），不是粉丝流。"
                if r >= 1
                else f"点赞仅为粉丝量的 {r * 100:.1f}%，推荐流占比可能不足，需排查内容标签与完播。"
            ),
        }
    return out


def _advice(key):
    return {
        "share_ratio": "分享偏低 = 内容缺少「替我说话」的社交货币。优化方向：结尾加转发钩子、强化观点锐度或利他信息密度。",
        "collect_ratio": "收藏偏低 = 内容缺少可复用价值。优化方向：把口播转成清单/步骤/干货表，让人有「留着以后用」的理由。",
        "comment_ratio": "评论偏低 = 缺少互动触发点。优化方向：抛争议点、留开放式提问、埋可纠错细节（2113544 的「4 互动」环节）。",
    }[key]


# --------------------------------------------------------------------------
# Markdown 渲染
# --------------------------------------------------------------------------
def render_md(d):
    st, au, me, dv = d["statistics"], d["author"], d["media"], d["derived"]
    L = []
    a = L.append
    a(f"# 抖音视频综合数据 · {d['aweme_id']}")
    a("")
    a(f"> 抓取时间：{d['fetched_at']}　|　内容形态：{d['content_type']}　|　来源：{d['canonical_url']}")
    a("")
    a("## 一、作品基础信息")
    a("")
    a("| 字段 | 值 |")
    a("|---|---|")
    a(f"| 标题/文案 | {d['title_desc'] or '（无）'} |")
    a(f"| 话题标签 | {'、'.join('#' + t for t in d['topics']) if d['topics'] else '（无）'} |")
    a(f"| @提及 | {'、'.join('@' + m for m in d['mentions']) if d['mentions'] else '（无）'} |")
    a(f"| 发布时间 | {d['publish_time'] or '未知'}（已上线 {d['days_online']} 天） |")
    if d["content_type"] == "图文":
        a(f"| 图片数量 | {me['image_count']} 张 |")
    else:
        a(f"| 视频时长 | {me['duration_readable'] or '未知'} |")
        a(f"| 分辨率 | {me['width']}×{me['height']} |")
    a(f"| 背景音乐 | {me and (d['music']['title'] or '（无）')} |")
    a(f"| aweme_id | `{d['aweme_id']}` |")
    a("")
    a("## 二、作者信息")
    a("")
    a("| 字段 | 值 |")
    a("|---|---|")
    a(f"| 昵称 | {au['nickname'] or '未知'} |")
    a(f"| 抖音号 | {au['douyin_id'] or '未公开'} |")
    a(f"| 粉丝数 | {_fmt_n(au['follower_count'])} |")
    a(f"| 作品数 | {_fmt_n(au['aweme_count'])} |")
    a(f"| 简介 | {(au['signature'] or '（无）').replace(chr(10), ' ')} |")
    a(f"| 主页 | {au['homepage'] or '未知'} |")
    a("")
    a("## 三、互动数据")
    a("")
    a("| 指标 | 数值 |")
    a("|---|---|")
    a(f"| 点赞 | {st['digg_count']:,} |")
    a(f"| 评论 | {st['comment_count']:,} |")
    a(f"| 收藏 | {st['collect_count']:,} |")
    a(f"| 分享 | {st['share_count']:,} |")
    a(f"| **总互动** | **{st['total_interaction']:,}** |")
    a(f"| 播放量 | 公开接口不提供（见下方说明） |")
    if dv.get("interaction_per_day") is not None:
        a(f"| 日均互动 | {dv['interaction_per_day']:,} |")
    a("")
    if dv.get("engagement_level"):
        a(f"**量级判定：{dv['engagement_level']}**")
        a("")
    a("## 四、结构性比率诊断（对照黄金数据标准）")
    a("")
    if dv["ratios"]:
        a("| 指标 | 实测 | 优秀线 | 状态 | 含义 |")
        a("|---|---|---|---|---|")
        for _k, r in dv["ratios"].items():
            a(f"| {r['label']} | {r['value_pct']} | {r['benchmark_good'] * 100:.0f}% | {r['status']} | {r['meaning']} |")
        a("")
    for item in dv["diagnosis"]:
        a(f"- **{item['metric']} · {item['status']}**：{item['detail']}")
    a("")
    if dv.get("digg_vs_follower"):
        a(f"- **点赞/粉丝比 {dv['digg_vs_follower']['value']}**：{dv['digg_vs_follower']['detail']}")
        a("")
    a(f"> ⚠️ {dv['play_count_note']}")
    a("")
    a("## 五、素材直链")
    a("")
    a(f"- 封面：{me['cover'] or '未获取'}")
    if me["no_watermark_url"]:
        a(f"- 无水印视频：{me['no_watermark_url']}")
        a(f"  - {me['note']}")
    if me["images"]:
        for i, u in enumerate(me["images"], 1):
            a(f"- 图片{i}：{u}")
    a("")
    return "\n".join(L)


def _fmt_n(n):
    if n is None:
        return "未公开"
    if n >= 100000000:
        return f"{n / 100000000:.2f} 亿"
    if n >= 10000:
        return f"{n / 10000:.1f} 万"
    return f"{n:,}"


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="抖音视频综合数据抓取器（零依赖 / 免 API Key）")
    ap.add_argument("input", help="抖音链接 / 短链 / 分享口令全文 / aweme_id")
    ap.add_argument("--json", dest="json_out", help="结构化 JSON 输出路径")
    ap.add_argument("--md", dest="md_out", help="Markdown 数据卡输出路径")
    ap.add_argument("--raw", dest="raw_out", help="接口原始 item 输出路径（排查用）")
    ap.add_argument("--quiet", action="store_true", help="不打印 Markdown，仅写文件")
    args = ap.parse_args()

    try:
        aweme_id, src = extract_aweme_id(args.input)
    except ValueError as e:
        print(f"[输入错误] {e}", file=sys.stderr)
        sys.exit(2)

    print(f"[1/3] 已识别 aweme_id = {aweme_id}", file=sys.stderr)

    try:
        item, filters = fetch_item(aweme_id)
    except RuntimeError as e:
        print(f"[抓取失败] {e}", file=sys.stderr)
        sys.exit(3)

    if item is None:
        reason = (filters[0] or {}).get("filter_reason", "未知") if filters else "未知"
        notice = (filters[0] or {}).get("notice", "") if filters else ""
        cn = FILTER_REASON_CN.get(reason, reason)
        print(f"[作品不可访问] {cn}" + (f"（平台提示：{notice}）" if notice else ""), file=sys.stderr)
        print("说明：该作品非公开，任何免登录工具都无法获取其数据，这不是工具故障。", file=sys.stderr)
        sys.exit(4)

    print("[2/3] 详情抓取成功，正在整理字段…", file=sys.stderr)
    data = normalize(item, aweme_id, src)
    md = render_md(data)

    if args.raw_out:
        with open(args.raw_out, "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)
    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)) or ".", exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[3/3] JSON 已保存 -> {args.json_out}", file=sys.stderr)
    if args.md_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.md_out)) or ".", exist_ok=True)
        with open(args.md_out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"[3/3] Markdown 已保存 -> {args.md_out}", file=sys.stderr)

    if not args.quiet:
        print(md)


if __name__ == "__main__":
    main()
