#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频文案提取器（本地 Whisper，免 API Key）
==============================================
输入：抖音视频链接 / 短链 / 分享口令 / aweme_id（或本地音视频文件）
输出：口播逐字稿 TXT / SRT 字幕 / 带时间轴 JSON

链路：解析链接 -> 取无水印直链 -> 下载 -> ffmpeg 抽音轨 -> faster-whisper 本地转写

依赖（已随专家环境预装）：
    faster-whisper, imageio-ffmpeg, requests
运行解释器：
    C:/Users/Administrator/.workbuddy/binaries/python/envs/douyin-asr/Scripts/python.exe
    （或任意装有上述依赖的 Python；脚本会自检并给出提示）

用法:
    python douyin_transcript.py "<抖音链接>"
    python douyin_transcript.py "<抖音链接>" --model medium --outdir ./out
    python douyin_transcript.py "D:/video/a.mp4" --local
    python douyin_transcript.py "<抖音链接>" --keep-video     # 保留原视频
"""

import sys
import os
import re
import json
import time
import shutil
import argparse
import subprocess
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 国内网络下 HuggingFace 模型下载走镜像。
# 必须同时关闭 hf_xet：它走 cas-server.xethub.hf.co 直连，会绕开 HF_ENDPOINT 镜像并返回 401。
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

AUDIO_EXT = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma", ".opus"}
VIDEO_EXT = {".mp4", ".m4v", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".ts"}


def log(msg):
    print(f"[transcript] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------------
# 环境自检
# --------------------------------------------------------------------------
def check_env():
    missing = []
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        missing.append("faster-whisper")
    if missing:
        print(
            "[环境缺失] 未安装：" + ", ".join(missing) + "\n"
            "请用专家预置的 ASR 环境运行本脚本：\n"
            "  C:/Users/Administrator/.workbuddy/binaries/python/envs/douyin-asr/Scripts/python.exe "
            + os.path.basename(__file__) + " \"<链接>\"\n"
            "或手动安装： pip install faster-whisper imageio-ffmpeg requests",
            file=sys.stderr,
        )
        sys.exit(10)


def get_ffmpeg():
    """优先用系统 ffmpeg，其次用 imageio-ffmpeg 自带的二进制。"""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


# --------------------------------------------------------------------------
# 下载
# --------------------------------------------------------------------------
def resolve_video_url(user_input):
    """复用 douyin_video_data 的解析能力，拿到无水印直链与作品元信息。"""
    from douyin_video_data import extract_aweme_id, fetch_item, normalize, FILTER_REASON_CN

    aweme_id, src = extract_aweme_id(user_input)
    log(f"aweme_id = {aweme_id}")
    item, filters = fetch_item(aweme_id)
    if item is None:
        reason = (filters[0] or {}).get("filter_reason", "未知") if filters else "未知"
        raise RuntimeError(
            "作品不可访问：" + FILTER_REASON_CN.get(reason, reason) + "（非公开作品无法转写）"
        )
    data = normalize(item, aweme_id, src)
    url = data["media"]["no_watermark_url"]
    if not url:
        raise RuntimeError("未能获取视频直链（可能是纯图文作品，没有音轨可转写）")
    return url, data


def download(url, dest):
    log(f"下载视频 -> {os.path.basename(dest)}")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.douyin.com/"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if total:
                print(f"\r  {got / 1048576:.1f}/{total / 1048576:.1f} MB", end="", file=sys.stderr)
    print("", file=sys.stderr)
    if os.path.getsize(dest) < 10240:
        raise RuntimeError("下载到的文件过小，直链可能已过期，请重新获取")
    return dest


def extract_audio(ffmpeg, src, dest):
    log("抽取音轨 (16k mono wav)")
    cmd = [ffmpeg, "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", dest]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0 or not os.path.exists(dest):
        raise RuntimeError("ffmpeg 抽音轨失败：\n" + p.stderr.decode("utf-8", "ignore")[-1200:])
    return dest


# --------------------------------------------------------------------------
# 转写
# --------------------------------------------------------------------------
def transcribe(audio, model_size="medium", language="zh"):
    from faster_whisper import WhisperModel

    log(f"加载 Whisper 模型：{model_size}（首次运行需下载，之后走本地缓存）")
    t0 = time.time()
    model = WhisperModel(model_size, device="auto", compute_type="int8")
    log(f"模型就绪，用时 {time.time() - t0:.1f}s，开始转写…")

    t1 = time.time()
    segments, info = model.transcribe(
        audio,
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        # 关键：关闭「用上一段输出作为下一段输入」，避免无语音/纯音乐时模型反复复述
        # initial_prompt（表现为逐段重复同一句话）。语言已用 language="zh" 硬约束，无需 initial_prompt。
        condition_on_previous_text=False,
        # 调高静音判定阈值：音频里没有人声时直接返回空，而不是编造内容
        no_speech_threshold=0.8,
        log_prob_threshold=-1.0,
        compression_ratio_threshold=2.4,
    )
    segs = []
    for s in segments:
        segs.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
        print(f"\r  已转写 {s.end:.0f}s …", end="", file=sys.stderr)
    print("", file=sys.stderr)
    log(f"转写完成，音频 {info.duration:.1f}s，耗时 {time.time() - t1:.1f}s")
    log(f"语种判定={getattr(info, 'language', '?')} 置信度={getattr(info, 'language_prob', 0):.2f} 静音概率(no_speech_prob)={getattr(info, 'no_speech_prob', 0):.2f}")
    return segs, info


def to_srt(segs):
    def ts(t):
        h, r = divmod(t, 3600)
        m, s = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"

    return "\n".join(
        f"{i}\n{ts(s['start'])} --> {ts(s['end'])}\n{s['text']}\n" for i, s in enumerate(segs, 1)
    )


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="抖音视频文案提取（本地 Whisper）")
    ap.add_argument("input", help="抖音链接 / 分享口令 / aweme_id / 本地音视频路径")
    ap.add_argument("--local", action="store_true", help="输入是本地文件而非抖音链接")
    ap.add_argument("--model", default="medium",
                    choices=["tiny", "base", "small", "medium", "large-v3"],
                    help="Whisper 模型，默认 medium（中文性价比最佳）")
    ap.add_argument("--language", default="zh", help="语种，默认 zh；设 auto 自动检测")
    ap.add_argument("--outdir", default=".", help="输出目录")
    ap.add_argument("--keep-video", action="store_true", help="保留下载的原视频")
    args = ap.parse_args()

    check_env()
    ffmpeg = get_ffmpeg()
    if not ffmpeg:
        print("[环境缺失] 未找到 ffmpeg，请 pip install imageio-ffmpeg", file=sys.stderr)
        sys.exit(11)

    outdir = os.path.abspath(args.outdir)
    os.makedirs(outdir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    meta = None

    # 1. 拿到媒体文件
    if args.local or os.path.exists(args.input):
        media = os.path.abspath(args.input)
        if not os.path.exists(media):
            print(f"[输入错误] 文件不存在：{media}", file=sys.stderr)
            sys.exit(2)
        ext = os.path.splitext(media)[1].lower()
        if ext not in AUDIO_EXT | VIDEO_EXT:
            print(f"[输入错误] 不支持的格式 {ext}", file=sys.stderr)
            sys.exit(2)
        stem = re.sub(r"[^\w\u4e00-\u9fff-]", "_", os.path.splitext(os.path.basename(media))[0])[:40]
        video_path = media
        cleanup_video = False
    else:
        try:
            url, meta = resolve_video_url(args.input)
        except Exception as e:
            print(f"[解析失败] {e}", file=sys.stderr)
            sys.exit(3)
        stem = re.sub(r"[^\w\u4e00-\u9fff-]", "_", (meta["title_desc"] or meta["aweme_id"]))[:40] or meta["aweme_id"]
        video_path = os.path.join(outdir, f"douyin_{ts}.mp4")
        try:
            download(url, video_path)
        except Exception as e:
            print(f"[下载失败] {e}", file=sys.stderr)
            sys.exit(4)
        cleanup_video = not args.keep_video

    base = os.path.join(outdir, f"{stem}_{ts}")

    # 2. 抽音轨
    wav = base + ".wav"
    try:
        extract_audio(ffmpeg, video_path, wav)
    except Exception as e:
        print(f"[抽音失败] {e}", file=sys.stderr)
        sys.exit(5)

    # 3. 转写
    try:
        lang = None if args.language == "auto" else args.language
        segs, info = transcribe(wav, args.model, lang)
    except Exception as e:
        print(f"[转写失败] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(6)
    finally:
        if os.path.exists(wav):
            os.remove(wav)
        if cleanup_video and os.path.exists(video_path):
            os.remove(video_path)

    plain = "".join(s["text"] for s in segs).strip()

    no_speech_prob = getattr(info, "no_speech_prob", 0) or 0
    if not plain and no_speech_prob >= 0.8:
        print(
            "【提示】未检测到可转写的人声（no_speech_prob=%.2f）。\n"
            "该作品可能为纯音乐 / 文字幻灯片 / 音轨缺失，属正常情况；\n"
            "此类作品无口播逐字稿，请直接交付「综合数据 + 图文文案(title_desc)」即可。"
            % no_speech_prob,
            file=sys.stderr,
        )

    # 4. 落盘
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write(plain)
    with open(base + ".srt", "w", encoding="utf-8") as f:
        f.write(to_srt(segs))
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "source": args.input,
                "meta": meta,
                "language": getattr(info, "language", args.language),
                "language_prob": round(getattr(info, "language_prob", 0) or 0, 3),
                "no_speech_prob": round(no_speech_prob, 3),
                "duration_sec": round(getattr(info, "duration", 0), 1),
                "model": args.model,
                "segments": segs,
                "plain_text": plain,
            },
            f, ensure_ascii=False, indent=2,
        )

    log(f"产物：{base}.txt / .srt / .json")

    # 5. stdout 交付原始逐字稿，供 agent 做整理纠错
    print("=" * 60)
    print(f"【口播逐字稿·原始】共 {len(segs)} 段 / {getattr(info, 'duration', 0):.1f} 秒")
    print("=" * 60)
    print(plain)
    print()
    print("-" * 60)
    print("【带时间轴】")
    for s in segs:
        print(f"[{s['start']:>7.2f}s] {s['text']}")


if __name__ == "__main__":
    main()
