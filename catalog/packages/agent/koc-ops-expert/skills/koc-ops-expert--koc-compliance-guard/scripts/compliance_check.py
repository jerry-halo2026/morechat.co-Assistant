#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOC 合规守门工具：内容禁用词扫描 + 分销结构三闸检查 + 发布前自检。

三件事：
    text          扫描一段 KOC 内容文本：绝对化用语、医疗功效、虚假承诺、站外引流、
                  伪装素人、刷量话术，并检查「有购物链接是否标了广告」
    distribution  分销/推荐机制的三闸检查（层级 / 计酬依据 / 入门费），判断是否触碰传销红线
    checklist     打印发布前 60 秒自检表 + 项目级合规清单
    template      打印输入模板

用法：
    python3 compliance_check.py text --json '{"content":"...","has_link":true,"marked_ad":false}' --text
    python3 compliance_check.py distribution --json '{"levels":2,"pay_basis":"sales","entry_fee":false,
                                                     "reward_for_recruiting":false}' --text
    python3 compliance_check.py checklist

⚠️ 这个脚本是**初筛**，不是法律意见。词库不可能穷尽，语境类违规（暗示性功效、虚假实验形式、
   引人误解的对比）机器查不出来，必须人工复核。正式项目请由用户的法务确认。
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# --------------------------------------------------------------------------
# 词库：每条给出正则、类别、法条依据、修改建议
# 依据的法条原文见 references/legal-redlines.md
# --------------------------------------------------------------------------

RULES = [
    # ① 绝对化用语 —— 《广告法》第九条第（三）项：不得使用"国家级""最高级""最佳"等用语
    (r"国家级|世界级|最高级|最高档|最佳|最好|最优|最强|最便宜|最低价|最划算|最安全|最有效|最受欢迎",
     "绝对化用语", "《广告法》第九条第（三）项", "改成可验证的相对表述：如「我试过的几款里最顺手的一款」→「我更常用这款，原因是…」"),
    (r"第一品牌|排名第一|全国第一|销量第一|行业第一|唯一一款|独家配方|绝无仅有|史无前例|无人能及|领导品牌|王牌产品",
     "绝对化用语/排他表述", "《广告法》第九条第（三）项", "去掉排他性表述；确有第三方数据支撑时须写明来源、口径与时间"),
    (r"100%\s*(有效|安全|纯|天然|治愈)|全网最低|永久(有效|不复发)|万能|包治|一劳永逸",
     "绝对化承诺", "《广告法》第四条、第九条", "删除；改为限定条件下的具体描述"),
    # ② 医疗功效 —— 《广告法》第十七条：非医疗类广告不得涉及疾病治疗功能、不得使用医疗用语
    (r"治疗|疗效|根治|治愈|药到病除|消炎|抗炎|杀菌|抑菌|除菌率|抗病毒|抗癌|防癌|降血(压|糖|脂)|"
     r"改善(失眠|便秘|痛经)|预防(疾病|感冒|近视)|替代药物|无副作用|药用级|医用级|처방",
     "医疗/功效用语", "《广告法》第十七条（非医疗、药品、医疗器械广告不得涉及疾病治疗功能，不得使用医疗用语）",
     "普通商品改成体感描述：「用完觉得…」；确需宣称功效的须在注册/备案范围内并由品牌方提供依据"),
    (r"丰胸|生发|美白祛斑(不含备案)|溶脂|瘦身\d+斤|减肥\d+斤|去疤|修复(受损|屏障)细胞",
     "特殊功效宣称", "《广告法》第十七条、《化妆品监督管理条例》功效宣称需有依据",
     "化妆品功效宣称须在已备案范围内并有评价依据；无依据的删除"),
    # ③ 虚假承诺与保量 —— 《广告法》第二十八条虚假广告
    (r"保证有效|保证爆|包爆|保\d+万曝光|必中|100%\s*中奖|稳赚|零风险|无效退款(无依据)|"
     r"\d+\s*天(见效|瘦|白|好)",
     "效果保证/虚假承诺", "《广告法》第二十八条（虚假广告）",
     "删除保证性表述。平台侧除官方保量产品外不存在保量机制；对内也不要给 KOC 承诺"),
    # ④ 站外引流 —— 平台规则（各平台《社区公约》/商业公约均禁止）
    (r"加微信|加个微|加v|加V信?|私我|私信我微|微信号[:：]?\s*\S+|手机号[:：]?\s*1\d{10}|"
     r"扫码加|二维码加|站外(下单|购买)|淘口令|复制链接到(淘宝|微信)",
     "站外引流", "各平台社区/商业公约（站外导流条款）",
     "删除。所有交易与沟通留在平台内；商务沟通走平台官方合作工具"),
    # ⑤ 伪装素人 / 隐瞒商业关系
    (r"这是我自己买的|自费购买|不是广告|非广告|没有商务合作|自来水安利",
     "伪装素人/隐瞒商业关系",
     "《互联网广告管理办法》第九条 + 平台社区公约（反对虚假人设/伪装素人）",
     "商单必须走平台报备并按规则标注；不得让付费或置换的账号自称自费购买"),
    # ⑥ 刷量与虚假交易
    (r"互赞|互关|刷量|刷单|控评|删差评|买好评|自问自答|水军|养号",
     "刷量/虚假交易", "《反不正当竞争法》关于虚假交易与虚假商业宣传的规定；各平台明令禁止",
     "全部删除。真实评价基建的合规做法见 references/platform-rules.md"),
    # ⑦ 贬低竞品
    (r"比[^，。]{0,8}好用一百倍|吊打[^，。]{0,6}|智商税(指向具体品牌)|某\w{0,3}品牌就是垃圾|别买[A-Za-z一-龥]{2,8}了",
     "贬低竞品", "《反不正当竞争法》商业诋毁相关规定",
     "改成自家产品的正向描述；横向对比须客观、可验证、不点名贬低"),
]

# 需要人工判断、机器查不出来的语境类违规（提醒用）
CONTEXT_RISKS = [
    "暗示性功效（不用医疗词但暗示能治病，如「我的老毛病再也没找过我」）",
    "虚假实验 / 虚假新闻形式（自制对比实验、伪装成新闻报道）",
    "引人误解的对比（挑对自己有利的口径做对比，数据来源不明）",
    "极限词的变体与谐音（如「最」写成「zui」、拼音、表情符号替代）",
    "未成年人出镜与代言（食品、化妆品类目尤其敏感）",
    "特殊类目资质（保健食品、医疗器械、婴幼儿配方、宠物食品等）",
]


def scan_text(payload: dict) -> dict:
    content = str(payload.get("content", ""))
    if not content.strip():
        return {"错误": "content 为空"}
    hits = []
    for pattern, cat, law, fix in RULES:
        for m in re.finditer(pattern, content, flags=re.IGNORECASE):
            hits.append({
                "命中": m.group(0), "类别": cat, "依据": law, "怎么改": fix,
                "位置": f"第 {m.start()} 字符",
            })

    # 广告标识检查：有购物链接/购买方式 + 推销性质 → 必须显著标明「广告」
    has_link = bool(payload.get("has_link"))
    marked = bool(payload.get("marked_ad"))
    filed = bool(payload.get("platform_filed"))  # 是否走了平台官方报备/合作工具
    ad_flag = None
    if has_link and not (marked or filed):
        ad_flag = {
            "问题": "内容附带购物链接/购买方式且属推销，但未显著标明「广告」，也未走平台官方报备",
            "依据": "《互联网广告管理办法》第九条：通过知识介绍、体验分享、消费测评等形式推销商品或者服务，"
                  "并附加购物链接等购买方式的，广告发布者应当显著标明「广告」",
            "怎么改": "① 走平台官方合作/报备工具（平台会附合作标识）；且 ② 按平台规则在显著位置标明，"
                    "小红书侧惯例是在标题或正文第一段标注品牌合作标识。两者都做最稳。",
        }

    aigc = bool(payload.get("contains_aigc"))
    aigc_flag = None
    if aigc and not payload.get("aigc_marked"):
        aigc_flag = {
            "问题": "内容含 AI 生成合成成分但未加标识",
            "依据": "《人工智能生成合成内容标识办法》（四部门 2025-03-14 发布，2025-09-01 施行）："
                  "要求显式标识 + 隐式标识（元数据），且不得恶意删除、篡改、伪造、隐匿标识，"
                  "也不得为他人实施上述恶意行为提供工具或服务",
            "怎么改": "显式标识（画面/文案可见提示）+ 保留元数据隐式标识；二次剪辑后要复核标识是否still在",
        }

    level = "可发"
    if hits or ad_flag or aigc_flag:
        blocking = [h for h in hits if h["类别"] in
                    ("医疗/功效用语", "特殊功效宣称", "刷量/虚假交易", "伪装素人/隐瞒商业关系", "贬低竞品")]
        level = "禁发（必须改完再发）" if (blocking or ad_flag or aigc_flag) else "需改（改完可发）"

    return {
        "判定": level,
        "命中词条": hits or "无",
        "广告标识": ad_flag or "无问题（或不适用）",
        "AI 标识": aigc_flag or "无问题（或不适用）",
        "机器查不出、必须人工看的": CONTEXT_RISKS,
        "免责": "本结果为初筛。词库无法穷尽，语境类违规需人工复核；正式项目请由法务确认。",
    }


def check_distribution(payload: dict) -> dict:
    """分销/推荐机制三闸：层级、计酬依据、入门费。"""
    levels = int(payload.get("levels", 0) or 0)
    pay_basis = str(payload.get("pay_basis", "")).lower()   # sales / headcount / team_sales / mixed
    entry_fee = bool(payload.get("entry_fee"))
    recruit_reward = bool(payload.get("reward_for_recruiting"))
    stock_required = bool(payload.get("stock_required"))

    gates, fatal = [], []

    # 闸一：层级
    if levels <= 2:
        gates.append({"闸": "① 层级", "结论": f"通过（{levels} 级）",
                      "说明": "自己 + 直接下级为常见的安全设计。层级越多，越容易被认定为「形成上下线关系」"})
    else:
        fatal.append({
            "闸": "① 层级", "结论": f"高风险（{levels} 级）",
            "依据": "《禁止传销条例》第七条第（三）项：要求被发展人员发展其他人员加入，形成上下线关系，"
                  "并以下线的销售业绩为依据计算和给付上线报酬，牟取非法利益的，属于传销行为。"
                  "另：组织、领导传销活动罪的追诉标准涉及人数与层级要件（层级三级以上），**具体标准须由法务确认**",
            "怎么改": "压到 2 级以内；或改为「平台直接与每个 KOC 结算」的单层结构，团长只拿服务费不拿下线分成",
        })

    # 闸二：计酬依据
    if pay_basis in ("sales", "gmv", "net_sales", "真实销售", "销售额"):
        gates.append({"闸": "② 计酬依据", "结论": "通过（按真实商品销售计酬）",
                      "说明": "计酬必须来源于真实商品销售，且商品有真实市场价值"})
    elif pay_basis in ("headcount", "人头", "拉新人数"):
        fatal.append({
            "闸": "② 计酬依据", "结论": "致命（按发展人数计酬）",
            "依据": "《禁止传销条例》第七条第（一）项：对发展的人员以其直接或者间接滚动发展的人员数量为依据"
                  "计算和给付报酬，牟取非法利益的，属于传销行为",
            "怎么改": "推荐奖励只能挂钩「被推荐人的真实内容产出或真实销售」，绝不能挂钩人数本身",
        })
    elif pay_basis in ("team_sales", "团队计酬", "下线业绩"):
        fatal.append({
            "闸": "② 计酬依据", "结论": "高风险（团队计酬）",
            "依据": "《禁止传销条例》第七条第（三）项（以下线销售业绩为依据计算上线报酬）",
            "怎么改": "团长的收入改为「服务费/坑位费/自身销售佣金」，不与下线业绩挂钩；"
                    "或由平台按每个人的自身销售分别结算",
        })
    else:
        gates.append({"闸": "② 计酬依据", "结论": "未提供，无法判断",
                      "说明": "pay_basis 请填 sales / headcount / team_sales"})

    # 闸三：入门费
    if entry_fee or stock_required:
        fatal.append({
            "闸": "③ 入门费", "结论": "致命（存在入门费或强制囤货）",
            "依据": "《禁止传销条例》第七条第（二）项：要求被发展人员交纳费用或者以认购商品等方式变相交纳费用，"
                  "取得加入或者发展其他人员加入的资格，牟取非法利益的，属于传销行为",
            "怎么改": "入池零门槛；不得设保证金、资格费、首单囤货、等级购买包",
        })
    else:
        gates.append({"闸": "③ 入门费", "结论": "通过（无入门费、无强制囤货）", "说明": "这是最不能碰的一条"})

    if recruit_reward:
        fatal.append({
            "闸": "附加检查", "结论": "高风险（对「拉人」本身发奖）",
            "依据": "同第七条第（一）项的计酬依据问题",
            "怎么改": "改成：被推荐人产出首篇合格内容或产生首单真实销售后，推荐人获得一次性奖励；"
                    "且不随下线层级滚动",
        })

    verdict = ("通过：三闸全过，可以按此结构设计" if not fatal else
               "不可出方案：存在触碰传销红线的设计，必须先改结构")
    return {
        "判定": verdict,
        "通过的闸": gates,
        "必须修掉的": fatal or "无",
        "三条同时满足才安全": [
            "层级 ≤2 级（自己 + 直接下级）",
            "计酬依据只能是真实商品销售额，不得以发展人员数量或下线业绩为依据",
            "不得收取任何形式的入门费（资格费、保证金、强制囤货、等级购买包）",
        ],
        "免责": "本检查基于《禁止传销条例》第二条、第七条的构成要件做结构性初筛，"
              "不构成法律意见。分销机制上线前必须由法务出具意见。",
    }


PRE_PUBLISH = """
发布前 60 秒自检（KOC 自己就能做，建议做成群公告置顶）

1. 有没有购物链接 / 团购码 / 小黄车？ → 有的话，标「广告」了吗？走平台报备了吗？
2. 有没有「最」「第一」「国家级」「100%」这类词？（包括拼音、谐音、表情替代）
3. 有没有说到治病、消炎、抗菌、疗效、替代药物？（普通商品一律不能说）
4. 有没有承诺效果或时间？（「7 天见效」「保证有效」）
5. 有没有留微信/手机号/二维码/站外链接？
6. 有没有说「这是我自己买的」？（走了报备或置换的，不能这么说）
7. 有没有点名说别的品牌不好？
8. 用了 AI 生成的图/视频/文案吗？ → 加 AI 标识了吗？
9. 参数、成分、功效数据是从品牌给的说明卡里抄的吗？（不要自己编）
10. 未成年人出镜了吗？（食品、化妆品类目要特别谨慎）

任意一条不确定 → 先问对接人，不要先发。改标题和正文比删稿的代价小得多。
"""

PROJECT_CHECK = """
项目级合规清单（每个 KOC 项目启动前逐项打勾）

【内容与广告】
[ ] Brief 里写明了「是否需标注广告 + 怎么标」
[ ] Brief 里附了禁用词表（含品类专属功效词）
[ ] 所有付费/置换合作 100% 走平台官方报备或授权工具，零私下置换
[ ] 质检 rubric 里合规是一票否决项
[ ] 品牌方提供了功效/成分/参数的书面依据（KOC 不自己编）

【分销与激励】
[ ] 分销层级 ≤2 级
[ ] 计酬依据是真实销售额，不与拉新人数、下线业绩挂钩
[ ] 无入门费、无保证金、无强制囤货
[ ] 推荐奖励只挂钩被推荐人的真实产出/销售，且不滚动
[ ] 合同写了刷量追回、未满留存期删稿按未完成交付处理

【数据与个人信息】
[ ] 报名表只收必要信息，写明用途与保存期限，取得同意（最小必要原则）
[ ] 收货地址、手机号等信息的访问权限做了限制（谁能看、看多久）
[ ] 台账里的 KOC 个人信息不外传给第三方（含 MCN、代运营）未经同意

【结算与税务】
[ ] 发放主体、税前税后口径、是否代扣代缴，已在协议中写明
[ ] 大量小额发放走平台结算或有资质的服务商，不用个人账号大额转账
[ ] 实物/礼品激励的发放记录留档

【AI】
[ ] 交给 KOC 的 AI 生成素材，已在 Brief 与合同里写明标识义务归属
[ ] 二次剪辑后复核过 AI 标识是否仍在
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
                lines.append(pad + "· " + "  ".join(f"{k}={v}" for k, v in item.items()))
            else:
                lines.append(f"{pad}- {item}")
    else:
        lines.append(f"{pad}{d}")
    return "\n".join(x for x in lines if x.strip())


TEMPLATE = {
    "text": {"content": "这款面霜真的是最好用的，用了三天就消炎了，加我微信有优惠",
             "has_link": True, "marked_ad": False, "platform_filed": False,
             "contains_aigc": False, "aigc_marked": False},
    "distribution": {"levels": 2, "pay_basis": "sales", "entry_fee": False,
                     "reward_for_recruiting": False, "stock_required": False},
}


def main() -> None:
    ap = argparse.ArgumentParser(description="KOC 合规守门：内容扫描与分销结构检查")
    ap.add_argument("cmd", choices=["text", "distribution", "checklist", "template"])
    ap.add_argument("--json")
    ap.add_argument("--file")
    ap.add_argument("--text", action="store_true")
    a = ap.parse_args()

    if a.cmd == "checklist":
        print(PRE_PUBLISH)
        print(PROJECT_CHECK)
        return
    if a.cmd == "template":
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

    result = scan_text(payload) if a.cmd == "text" else check_distribution(payload)
    print(to_text(result) if a.text else json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
