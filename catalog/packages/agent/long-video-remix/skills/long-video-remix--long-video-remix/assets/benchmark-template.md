# Detail Benchmark 记录

用于比较不同版本或方法在 E 阶段的真实成本。数字从会话日志 / 工具事件统计，不凭记忆估算；统计不到的写 `not_measured` 并说明原因。

## 运行条件

- 素材（新素材，未被参与者看过；时长、帧率、是否可变帧率）：
- 版本 / 方法：
- DI 数量与总时长：
- 上下文是否隔离（新会话、不带历史）：
- 执行顺序（多方法时交替先后以抵消顺序影响）：

## 指标

| 指标 | 数值 | 统计口径 |
|---|---|---|
| 总工具调用 |  |  |
| 读图次数（按 0.5 / 1 / 4fps / 逐帧条 / 单帧分列） |  |  |
| 读图占总调用比例 |  |  |
| 同一时间点被重复阅读的次数 |  |  |
| validate 调用次数 |  |  |
| 子代理失败与补做耗时 |  |  |
| 被否决后回写的 Detail 行数 |  |  |
| 切点返工次数（切点首次写定后又被修改） |  |  |
| 写入 Detail 耗时（最后一次读图到行写完） |  |  |
| AI 实际工作时长 |  |  |
| token / 图像输入量（平台可见时） |  |  |

## 质量审计

随机选一至两个 DI，把未读的时段与密度全量补读，比较：

| DI | 补读前事件数 | 补读后事件数 | 结论或切点是否改变 | 漏看原因（密度 / 变化检测 / 阈值） |
|---|---|---|---|---|
|  |  |  |  |  |

审计发现漏看时，调整 `references/detail-evidence.md` 中对应事实类型的密度或升级条件，并在此记录。

## 结论

- 已证实：
- 未证实：
- 下一步：

## Audio efficiency

- Candidate audio span reviewed: ___ s
- Targeted ASR seconds: ___ s
- Final selected audio verified in Execute Step 0: ___ s
- Full-interval ASR avoided: yes / no / not_applicable
