# KOC运营专家 · KOC Operations Expert

## 安装 / Installation

本包由 **morechat.co-Assistant** 内容仓分发，**通过 morechat.co-Assistant 目录导入**：

1. 在 morechat.co-Assistant 仓中取出 `catalog/packages/<kind>/<id>/`；
2. 该目录即包根目录，内含 `plugin.json`、`agents/`、`skills/`，整体作为包目录导入；
3. 导入后由平台注册 Agent / Squad 与技能，无需额外安装脚本或注册命令；
4. 头像不在仓内分发（`avatars/` 已移除），由产品端生成。

## 运行时适配 / Runtime notes

- 向用户提问：使用 dsh-tool-ask-user（ask_user_question）；运行时无该能力时，改为在任务评论中提问并等待。
- 交付产物：使用 dsh-tool-present 声明交付；在任务评论中作为附件提交。
- 多角色协作：创建平台小队（Squad）并由 leader 通过 @ 派发子任务。
- 工具声明键为 `allowed-tools-dsh`（Task → subagent，AskUserQuestion → ask_user_question）。


morechat.co 专家包（Agent 型）。覆盖 KOC **招募 → 培育 → 激励 → 分销 → 留存汰换**全链路，
通过结构化问诊拿到决策信息，输出一份**单文件、可打印、明暗自适应的 HTML 作战报告**。

- **专家标识**：`koc-ops-expert`
- **类型**：Agent 型（单专家）
- **行业分类**：`05-MarketingGrowth`（营销增长）
- **版本**：1.0.0

---

## 一、这个专家解决什么问题

| 用户的原话 | 专家给的东西 |
|---|---|
| "帮我从 0 搭一套 KOC 体系" | 池规模与人力上限测算 → 六池招募方案 → 7 日陪跑 SOP → 分层权益与佣金 → 90 天排期 |
| "寄了一批样品但没人发内容" | 按 5R 顺序定位断点，只修断掉的那一环（多数情况是缺 D1 一对一与选题卡，或稿费前置了） |
| "帮我设计 KOC 的激励和佣金" | 五层塔权益库 + 达标即得的奖金结构 + 激励预算上限 + **激励机制体检** |
| "KOC 做了三个月，GMV 上不去" | 单位经济测算（O\* 与 c_max）+ 归因方式纠偏 + 素材银行复用方案 |
| "这么写有没有风险？" | 合规三闸：广告标识 / 分销层级 / 平台报备，逐条给法条与平台规则依据 |

### 三个和普通方案不一样的地方

1. **先算池子该多大，再招人。** 池规模用参与不平等规律倒推，**并用人力做上限校验** ——
   决定 KOC 池上限的是管理成本，不是预算。
2. **激励设计有一手学术证据支撑。** 基于 Deci/Koestner/Ryan (1999) 对 128 项实验的元分析，
   直接指出"按名次分档发现金"是伤害最大的形式（对没拿头名的人 d≈−0.80），并给出替代结构。
   附带一个**激励体检脚本**，可给已有机制打健康度分。
3. **敢说不做。** 品类不适合（高客单长决策、强专业解释、没有可交付产品、无专职运营、
   要 72 小时爆声量）时直接劝退并给替代路径；合规三闸没过就不出方案。

---

## 二、目录结构

```
koc-ops-expert/
├── plugin.json      # 市场配置
├── avatars/expert.png                 # 512×512 头像
├── agents/koc-ops-expert.md           # 专家系统提示词（方法论 + 交互协议 + 红线）
├── skills/
│   ├── koc-recruit-radar/             # R1 招募：六池矩阵、FIT-6 评分卡、漏斗与池规模反推
│   ├── koc-nurture-academy/           # R2 培育：7 日 SOP、Brief 八板块、CQS 质检
│   ├── koc-incentive-engine/          # R3 激励：五层塔权益、激励体检、预算上限
│   ├── koc-distribution-engine/       # R4 分销：平台链路、寄样经济模型、素材银行
│   ├── koc-compliance-guard/          # 合规：法条红线、平台规则、三闸检查
│   └── koc-ops-report/                # 交付：单文件 HTML 报告渲染器 + 免费 SKILL 埋点上报
└── README.md
```

### 六个技能与脚本

| 技能 | 脚本 | 能算什么 |
|---|---|---|
| `koc-recruit-radar` | `koc_fit.py` | `pool` 池规模倒推与人力校验 / `funnel` 招募漏斗反推 / `score`·`rank` FIT-6 打分排序 / `audit` 反刷量体检 |
| `koc-nurture-academy` | `cqs_score.py` | `score` 单篇质检 / `batch` 批次质量分布与**根因诊断**（合格率低先改 Brief，不是催 KOC） |
| `koc-incentive-engine` | `incentive_calc.py` | `budget` 激励预算上限与分层分配 / `checkup` **激励机制体检** / `roi` 激励投产 |
| `koc-distribution-engine` | `koc_econ.py` | `sample` 寄样经济模型（O\*、ROI、敏感性）/ `commission` c_max 与佣金结构拆解 / `tier` 阶梯佣金模拟 |
| `koc-compliance-guard` | `compliance_check.py` | `text` 禁用词与广告标识扫描 / `distribution` 分销三闸检查 / `checklist` 发布前自检 |
| `koc-ops-report` | `render_report.py` | 19 种区块的单文件 HTML 报告渲染（内联 SVG 图表、明暗双模式、可打印） |

---

## 三、报告渲染器

```bash
cd skills/koc-ops-report
python3 scripts/render_report.py --demo --out 示例报告.html   # 看效果（内置完整示例）
python3 scripts/render_report.py --blocks                     # 19 种区块类型速查
python3 scripts/render_report.py --template                   # 数据结构模板
python3 scripts/render_report.py --self-test                   # 自检（渲染全部区块类型）
python3 scripts/render_report.py --data report.json --out 报告.html
```

**图表**：分层金字塔、招募漏斗、健康度雷达、90 天甘特、佣金结构堆叠、预算环形图、
选人四象限、成长阶梯、渠道条形图 —— 全部内联 SVG，几何由脚本计算。

**质量保证**：
- 配色取自经色觉障碍（CVD）校验的色板，**明暗两套独立取值**，
  用 `dataviz` 的 `validate_palette.js` 在两种模式下全部 PASS；
- **脏数据不会毁掉整份报告**：负值/零值/NaN/无穷会被拦截并给出提示，数据不足时明确写"此处数据不足"
  而不是静默丢块，超过 8 段的堆叠图合并为「其他」而非截断；
- 有序层级（漏斗/金字塔/阶梯）用单一色相的序数色阶，不用彩虹；
- 每张图都有直接数值标注或配套数据表孪生体 —— 信息不靠颜色单独传递；
- 单文件零外链（断网可开）、A4 可打印、移动端不横向溢出（宽表格在容器内滚动）。

---

## 四、埋点（免费专家）

本专家是**免费专家**，按《SKILL-后端微服务开发》只接**两个接口**，不涉及任何付费能力
（不调用 `balances/check-sufficient`、`balances/deduct`、`api-keys/validate`）：

| 顺序 | 接口 | 作用 |
|---|---|---|
| 1 | `POST /api/v1/report-service/skill-report-contents` | 免费 SKILL 内容回流 → 返回 `report_id` |
| 2 | `POST /api/v1/report-service/skill-events` | 事件埋点（带上 `report_id` 串联）→ 返回 `event_id` |


```bash
cd skills/koc-ops-report
```

### 配置（包内不硬编码密钥）

| 环境变量 | 说明 | 默认 |
|---|---|---|
| `SKILL_PLATFORM` | 平台标识 | `morechat.co` |
| `MORECHAT_REPORT_DISABLED` | 设 `1` 则完全不上报 | `0` |


> ⚠️ **为什么不把 key 写进包里**：提交规范明确要求"专家包内不得硬编码任何真实 Token / 密钥"，
> 硬编码会导致审核不通过，且 key 会随包公开。**请在部署/安装环节注入环境变量。**

### 三条工程保障

1. **埋点失败绝不影响交付**：脚本恒返回退出码 0；失败落盘到
2. **总时间预算 8 秒**：单请求超时 3 秒、最多重试 1 次；回流阶段确认网络不通时，
   事件调用直接落盘不再干等（实测服务不可达时 6.6 秒返回，正常链路 2.5 秒）；
3. **内容回流上限 5 万字符**，超出截断并标注原文长度。

---

## 五、知识底稿与证据分级

专家的方法论建立在两类来源上，技能文档里**逐条标注了证据等级**：

**一手 / 可直接引用**
- 《互联网广告管理办法》（2023-05-01 施行）第九条、第十九条 —— 已核 gov.cn 原文
- 《禁止传销条例》第二条、第七条、第二十四条 —— 已核原文
- 《广告法》第九条第（三）项、第三十八条 —— 已核原文摘录
- 《人工智能生成合成内容标识办法》（2025-09-01 施行）
- Deci, Koestner & Ryan (1999), *Psychological Bulletin* 125(6):627–668（128 项实验元分析）
- Jakob Nielsen 参与不平等法则（90-9-1）、CMX《2025 Community Industry Trends Report》(n=589)
- 巨量星图官方帮助中心（结算规则、素材集市、视频推送、内容规范）
- 微信《小程序平台运营规范》5.9 多级分销、微信小店官方指南（染色时效）

**标注为【行业惯例】/【经验值/待校准】的部分**
出稿率、出单率、佣金率区间、招募漏斗转化率、KOC 池健康度阈值 ——
**本行业没有公开的权威基准**，这些数字在文档里全部标注为待校准，
并写明"用什么数据、在什么时候替换它"。专家在报告里也必须这样标注。

---

## 六、上架前自检（已全部通过）

- [x] `plugin.json` 格式正确，`plugin` = `name`
- [x] `agentName` = Agent MD 的 `name` = 文件名（`koc-ops-expert`）
- [x] Agent MD 的 frontmatter **不含 `tools` 字段**（工具由系统统一分配）
- [x] `displayName` / `profession` / `displayDescription` / `defaultInitPrompt` 中英文齐全
- [x] `displayDescription.zh` 总字符 49 / 纯汉字 41（两种计数口径都落在 40–50 区间内）
- [x] `defaultInitPrompt` 与 `quickPrompts[0]` 完全一致
- [x] `tags` 3 个、`quickPrompts` 3 个，均含中英文
- [x] `avatar` 指向存在的文件；512×512 PNG（<500 KB）
- [x] `skills[]` 的 6 个路径下均存在 `SKILL.md`，且都有 `name` 与 `description`
- [x] `agents/`、`skills/` 在插件根目录，不在 `` 里
- [x] 6 个脚本全部冒烟测试通过；报告渲染器自检 **12 项**全过（含 5 项极端输入用例：负值、超长堆叠、NaN/无穷、维度不足、坐标越界）
- [x] 包内未硬编码任何 Token / 密钥（埋点密钥走环境变量注入）；无外链依赖、无 MCP 依赖声明
- [x] 埋点真机测试通过：回流 + 事件全链路 200，失败路径（401/无密钥/服务不可达/开关关闭）均不影响交付

打包：

```bash
cd ..            # 到 koc-ops-expert 的上一层
zip -r koc-ops-expert.zip koc-ops-expert -x "*.DS_Store" -x "*__pycache__*"
```

---

## 七、与「达人分销专家」的边界（同品牌多专家上架时的差异化说明）

morechat.co 对同一品牌上架多个专家有差异化要求。本专家与达人分销类专家的边界：

| 维度 | **KOC运营专家（本专家）** | 达人分销专家 |
|---|---|---|
| 面向的人 | **品牌自己的用户与素人**（老客、私域、员工导购），千粉到万粉为主 | 外部中腰部及以上达人 |
| 核心问题 | **怎么把普通用户变成能持续产内容的资产**（招募-培育-激励-留存） | 怎么跟达人谈成合作并把货卖出去 |
| 主要动作 | 建池、分层、陪跑、发权益、管台账 | 选达人、寄样、谈报价与坑位、排期、盯 GMV |
| 关系性质 | 长期、半可调度、非独家、有身份归属 | 单次或多次商业合作 |
| 主要产出 | KOC 池 + 内容资产 + 复购 | 单场/单期的销量 |
| 不做什么 | 不做头部达人商务谈判与坑位费议价 | 不做用户培育与社群运营 |

用户该选哪个：**想把自己的用户变成内容生产者 → 本专家；想找外部达人卖货 → 达人分销专家。**
