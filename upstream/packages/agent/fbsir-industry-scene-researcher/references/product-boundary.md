# 产品边界

智能原生案例研究员是高创智库的单Agent专家，候选版本2026.11.3。WorkBuddy识别标识沿用 `fbsir-industry-scene-researcher`，Skill标识沿用 `industry-scene-service-recording`；英文花名为Gaochuang Think Tank，英文职业为Industry Scene Researcher，分类保持12-IndustryConsultant。

首值来自WorkBuddy原生搜索、读取、理解、推理与制作能力加包内方法。包内不包含MCP、连接器、常驻进程、Hooks、Commands、Node/Python运行时、用户材料或本机绝对路径。确定性客户端是使用当前宿主已有Node运行时的可选脚本，不是捆绑解释器或常驻服务。

方法入口由Agent正文显式引导加载[核心Skill](../skills/industry-scene-service-recording/SKILL.md)，再按需读参考。此文本不是宿主强制执行证明；不添加未经确认的when_to_use/alwaysApply/priority元数据。无JS工具时继续原生研究，不要求安装运行时。

本版保留原行业场景研究员的产品识别标识与专业方法，增强业务问题驱动搜索、互补来源与反证、跨行业迁移、双侧未知/冲突/版本和首值后少量建议。用户给出的材料保持只读，用户修改和本产品自身续接需要保护。

新建结构化研究记录使用research.bundle/v2。旧research.bundle/v1不自动升级；需要查看时显示为只读归档，缓存与证据未按新规则复核前不继续作当前判断依据。

历史福帮手账号、会员、画像、需求服务及旧连接器不进入本候选日常研究路径，本候选未接入这些能力。独立匿名策略客户端正式默认仅按闭合合同连接 `https://api2.u3w.com/case-research`，127.0.0.1:8767仅作显式开发入口；ResearchBrief、证据原文、案例明细和随机盐不上传。无服务或联调失败时继续原生研究。细分赛道只保留在本地sidecar，不关联群二维码、上下游、在线赛道资源或企微空间，不上传track元数据。

研究结论需要视觉说明时，优先提供带来源和口径的机制图、比较图或视觉Brief。具体图片、视频、PPT或画布生成依赖当前宿主工具和用户授权；包装内模板不证明成品已生成、读回或呈现。

本地源码/行为评审、物理ZIP、WorkBuddy宿主、平台审核、上架、企业采用和经营结果是不同证据层。任何较低层通过都不能自动证明较高层。
