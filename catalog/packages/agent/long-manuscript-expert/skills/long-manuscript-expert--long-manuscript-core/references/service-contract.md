# 可选远端策略合同说明（2026.11.5）

本说明面向使用者与维护者，描述**默认关闭**的可选远端策略能力。普通研究、五形态项目文件、局部修订与接续不依赖配套策略服务、登录或连接器即可完成；但这不暗示所有内容保证不离机——实际模型、联网检索与材料处理位置由 Multica 宿主、当前会话与本次授权决定。所有远端出口（含回执查询与反馈）均服从同一默认关闭门；本地恢复不联网。**历史（2026.11.0200 时点）**：配套服务 `paper-20261105-0200-r3` 曾由独立服务路部署并公网读回；前置 0200 版本字节的三件客户端源码曾在原时点通过一次受控合成 Python HTTPS 链（resolve / 原号 receipt / 明确同意 feedback，结果 selected / recorded / accepted），该结果绑定当时字节、保留不改。**当前（2026.11.5）**：新版服务 release `paper-20261105-115-r1` 已部署；本版固定字节的三件客户端以精确 `2026.11.5` consumer 完成一次受控合成 Python HTTPS 配对（selected / recorded / accepted）。该证据是新合成 Python 请求，不是 Multica 原生远端用户任务、不是用户采用或业务结果，也不构成服务持续可用性或线上持续通过的保证；默认配置值不自动代表某次实际执行结论。本包不声称市场可用；真实配对与部署证据由服务 lane 独立持有。

## 一、选定合同

唯一选定组合：闭合 `paper.intent.v2` wire + 精确 `2026.11.5` 准入 + 同号 receipt 只读查询。不启用 v3、foundation preview、feedback v3、私有项目查询、付费供应商或全局稿件存储。五形态字段与 v3 字段**不得**塞入旧 wire；旧 270/300 闭合形状仅作兼容说明，0200 绝不伪装旧版。

| 项 | 值 |
| --- | --- |
| resolve | `POST /v1/strategies/resolve`，schema `paper.intent.v2` |
| feedback | `POST /v1/feedback`，schema `paper.feedback.v2`，默认关闭且需明确同意 |
| receipt 查询 | `POST /v1/strategies/receipt`，schema `paper.strategy-receipt-query.v1`，**只读** |
| 请求上限 | 沿用 v2 既有 16 KiB 请求与闭合字段 |
| consumer | `product=long-manuscript-expert`，`version=2026.11.5`（精确） |
| 默认 | 远端关闭、反馈关闭、遥测关闭 |

## 二、规范字节与摘要

canonical JSON 采用 UTF-8、保留 Unicode、键按字典序排序、分隔符为逗号与冒号且无空白、无 BOM、无末尾换行、仅有限数值，整数仍序列化为整数。参考实现：

```
json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
```

对**已校验的原 `paper.intent.v2` 对象**（含精确 consumer.version 与原 request_id）计算 SHA-256 作为 `request_digest`。不得哈希带缩进的 JSON 或文件末尾换行；不得改变整数序列化或请求字节。

合同样例的 canonical 为 1464 字节（样例文件自身 1465 字节含末尾换行），摘要 `860d5f2086c83102634b0dc629068361ea1069dd95d9e2fd4a51b617bbd09f5f`。本包客户端以该样例为固定回归点；服务端同时保留对旧版 2026.11.0200 的只读回执查询准入（caller 版本为准入元数据，不改原请求归属）。

## 三、一次 resolve

1. **先存再发**：排他保存原规范字节、UUID、摘要、当前意图/证据修订与合同来源，并实际读回；保存失败时网络调用必须为零。发送前记录 `send_started`。
2. **仅发一次**：0200 客户端关闭旧版同号自动 resolve 重试。超时、EOF、503、正文无效或结果未知后，只能按原 UUID 与原摘要查 receipt；查询失败也不转成重发或换号。不沿旧诊断码自动重试 resolve。
3. **进程中断**：不能凭"缺响应"断言没有发送；重启后先按原号只读查询。

## 四、两层校验

**外层 receipt** (`paper.strategy-receipt.v1`)：七个闭合字段 `schema / request_id / request_digest / state / response / executable / retry_permitted`；schema 与状态枚举、原 UUID 与原摘要、真实布尔值、状态与字段组合分别校验；`retry_permitted` 恒为 false。状态取值：`recorded`、`expired`、`catalog_changed`、`unknown`。

**内层 v2 decision** (`paper.strategy-decision.v2`)：按完整 v2 语义校验决定状态、目录修订、策略/计划/轨道绑定、预算、能力、候选与轨道评估、签发/到期与单调有效期。`executable=true` 不是充分条件，仍须复核当前本地修订、预算、能力、候选和轨道。

**状态不越界**：
- `recorded + selected`：通过全部本地复核后才可执行；
- `recorded + skipped / no_match / needs_selection`：不执行网络计划，可保留解释性候选；
- `expired / catalog_changed / unknown`：均不执行、不重发；
- `unknown` 的 `response` 必须为 null、`executable` 必须为 false；
- UUID 改大小写并非新操作；相同 UUID 不同 digest 视为不匹配。

## 五、恢复不是重做

- 本地动作状态保存 `started / completed / unknown` 与已花预算；重复读取 receipt 不重复产生本地成果，不重新执行已完成或结果未知的搜索、写出与反馈。
- **不刷新寿命**：旧客户端要求签发时间距当前不超过 30 秒，不能直接拿来验 60 秒前但仍有效的恢复回执。恢复保留原 `issued_at` / `expires_at`，不重设 600 秒；使用可核验时间边界判断，恰好到期不可执行；不跨进程复用单调时钟；时钟不可信时保守拒绝。
- 恢复决策不等于重做工作；先查原状态或原文件。

## 六、反馈独立

反馈默认关闭；只有明确 consent、真实选定 decision 与实际指标才可尝试。本地持久绑定只支持一种受控恢复：客户端进程重开后，对**未开始过反馈**且当前约束仍有效的原绑定操作做一次已绑定首次尝试；它不能证明服务重启后仍保有反馈资格。服务端资格丢失、反馈被拒绝或响应未知时，不重新 resolve 造资格，也不重发已开始的反馈。receipt 查询不重建服务端反馈资格。`accepted` 只表示服务接受了这份匿名报告，不等于人类采纳。分母固定同一批次，未观测整数不上传。

## 七、原生首值优先

容量满、请求被拒、服务不可用或用户未选远端时，直接继续原生任务；不清 pending、不删服务端回执、不改 endpoint、不伪装 270/300。HTTP 拒绝与业务结果（`no_match` / `needs_selection` / `local_path`）分开表述，不一律标为技术故障。

本地路径、无匹配、待选择是正常业务/信息结果，不是技术错误；真实状态码与安全响应头保留；重定向目标 URL 不带出诊断。诊断摘要绝不含原请求 ID、正文、路径、URL、查询或用户稿件。

## 八、边界声明

**历史（2026.11.0200 时点）**：配套服务 `paper-20261105-0200-r3` 曾由独立服务路部署并公网读回（部署证据由服务 lane 持有）；前置 0200 版本字节的三件客户端源码曾在原时点通过一次受控合成 Python HTTPS 链（resolve / 原号 receipt / 明确同意 feedback，结果 selected / recorded / accepted），该历史结果绑定当时字节、保留不改。**当前（2026.11.5）**：新版服务 release `paper-20261105-115-r1` 已部署；本版固定字节的三件客户端以精确 `2026.11.5` consumer 完成一次受控合成 Python HTTPS 配对（selected / recorded / accepted）——新合成 Python 请求证据，非 Multica 原生远端用户任务、非用户采用或业务结果，也不证明服务持续可用性或线上持续通过。本包默认远端与反馈关闭、不自动发起真实网络调用；默认配置值不自动代表某次实际执行结论。普通研究不因服务状态降级而阻断；v3 / foundation preview / feedback v3 未启用。客户端实现见 `scripts/strategy_client_0200.py`（仅标准库）。
