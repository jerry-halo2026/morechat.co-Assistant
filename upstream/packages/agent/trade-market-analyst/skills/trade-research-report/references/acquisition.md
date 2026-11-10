# 八项获客适配：原七项及有限产品S06

S05 同行、S07 品类、S08 HS 属海关获客；S13 产品及 S14 US SIC/S15 NACE/S16 NAICS 属工商获客。全部默认目标20家、聊天+Excel，删可选尾部仍补本任务默认；必填主体、目标国家（同行未给国家为全部可用市场）、单端日期、同名及编码歧义不猜。新 S06 保持原 discovery/product_buyers 入口、原产品、默认25家/规模不限/近12个日历月/chat+xlsx，采用 acquisition/1 的有限产品变体；旧七项默认20家不变。

用 `plan_report(task={type: acquisition, intent, subject, constraints, outputs})`，意图为 supplier_buyers/category_buyers/hs_buyers/product_companies/ussic_companies/nace_companies/naics_companies。主体分别 supplier/category/hs_code/product/industry_code，均原文字符串。trade默认截至当天近12个日历月；工商资料按实际资料期，休眠贸易核验默认不触发额外查询。需贸易核验须另建经明确预算授权的任务。

执行与续做按 SKILL.md 第 3 步写查询记录，两钱包预算分开。acquisition/1参数按计划上下文和明确的选择填，禁止动态绑定、游标、自造市场、全量采数或自动放宽。同参成功复用；已发出未记结果、失败或费用未知不自动重发，先告诉用户。失败的实扣照记。普通点与联系人点分开，预算缺失/超出在付费前合并确认一次，无默认授权。

`acquisition_scope` 明确绑定 subject/constraints/mapping。同行 mapping 保存 original/confirmed_supplier/identity_basis，主体确认不证明按唯一企业隔离同名记录。可见销售客户既可来自本国出口也可来自他国进口；发生国不是注册国。中文来源解析、抬头排除、同名及未核对范围提示必须保留；已知同名不能算指定同行合格关系，不自动加查明细。仅正常可见名称范围可部分交付，关系边界须显示。

品类 mapping 保存 original/meaning/category_scheme/category_level。先保存实际能力，用 acquisition_coverage 绑定调用及全部原兼容分组、明确一条direct_import或reverse_export（同行可两条）。S07先预算授权普通付费品类聚合，acquisition_category只可选择保存行，绑定call_id/row_index/category_id/category_scheme/category_level；任意文本不是已确认编号。不能用其他行业树代替。不同组单独预算；未查或排除范围保留，不说全球排名。

HS及行业代码 mapping 保存 original/code/code_system/level/meaning/reference_vintage/reference/source_version。HS保前零和层级，不能产品猜码。行业体系固定ussic/nace/naics，按原文前缀查询；明确用户释义 reference=user_confirmed 或该体系官方参考，释义版本与source_version=unknown分开。未知源版本不自动采用最新NACE/NAICS意义；有合法代码且释义待确认不等于工具不支持代码查询，不全量爬字典。工商产品 mapping 保存 original/effective/meaning/reference；英文业务词须明确对应原中文产品，不用中文名称召回冒充主营匹配，不伪造逐企业片段。

search_companies真实生效过滤列表与忽略列表都核对；行业行代码必须属于所选体系并匹配前缀，错体系/忽略筛选/全调用失败不得qualified。单页最多50，无游标；总数下限不能当完整覆盖。工商结果仅企业候选，不证明采购。稀疏字段不删主体；未知营收币种、年度、资料日期不得借美元或运行日。

必要基础画像和同名候选搜索按普通点实扣记账；画像关联值仅取保存名单或明确选择保存候选，不自动取第一项，不查full/联系人。acquisition_match绑定实际候选行与贸易原名；acquisition_selection显式保存选择行与依据，全公开名单合计不超目标。海关合格选择还须 qualification/fields 引用已保存主体的实际业务及规模事实，缺项为unknown；有采购证据但未知规模列待核实。工商有效候选不因缺采购事实被否定。

工商取格式规范时 output_profile=O1、task_variant=corporate_candidates；海关 O1。未选候选只留在工作目录，聊天和每个sheet均按明确展示目标，不借候选附表绕目标。全部费用仍按完整取数实扣。成品出完回读核对；失败保留旧成品，切格式零查询。

同行官网/所在地仅作 identity_basis 身份佐证，不能说已在贸易请求生效为城市过滤或唯一企业隔离。注册国、贸易发生国与交易抬头城市条件分别处理。显式要求 supplier_city 时当前闭合契约返回 pending，保留原限定待确认后独立设计；不忽略、不自动扩大查询。

安装兼容：通用报告套件只升级明确支持的历史通用技能；遇到已有WorkBuddy专用技能时保留原文件及平台信息，停止安装且不留下部分完成状态。WorkBuddy技能更新须走平台同步或上传路径。

高于六位的HS执行前须确认代码国别含义或选择仅前缀证据。计划保留待确认提示；必须明确确认范围后才执行。mapping额外hs_semantics仅两种闭合方式：prefix_only须acknowledgement明确为“仅数字前缀匹配，国别细分含义尚未核实”；single_market须code_country为原目标国及独立reference/evidence，不能从目标国自动生成。反查（即使只有一个来源国）或跨市场仅接受prefix_only，采购名单只能待核实，用户提供产品含义不作为已验证事实。single_market只允许直接单国，并公开源实际体系/版本未核实，不作官方税则判断。不截六位、不自动转换、不额外付费补查。六位及以下保留原流程及源版本未知说明。

规模仅按保存来源的明确规模标签核对：小型/小型公司、中型/中型公司、大型/大型公司、超大型/超大型公司分别同类，超大型不能当大型。保留用户原规模要求和来源原标签，不按员工人数或营收阈值推定，不新增查询规模筛选。已知不同类列排除；来源缺失、未知或无法识别列待核实；不限不设规模门。海关合格决定有规模要求时必须引用同一已确认主体的保存规模标签及业务事实。其他自由文字规模要求保留在待确认计划中，不执行；明确澄清后重新规划，不手改当前计划。

S06 新任务先确认 acquisition_scope：subject 与全部 constraints 必须绑定原请求，mapping 只含 original=原产品，不添加人工替换词、HS或分类。保存实际能力后用 acquisition_coverage 选择一条路线；目标国有兼容直接进口时优先直接查，确无该路线才可明确出口反查，反查须有实际目的国维度并保持 destination=原目标国。仅S06沿用原业务角色与产品适用部分分组，保留排除与未查组；其他七项不放宽。保存能力接受关单、提单、海运提单、铁路运输的采购商适用部分，能力代表摘要不证明各源或逐年实际参与。聚合行核对真实扩词、服务HS映射、计数及条件执行，不编造逐票货描；货描需实际扩词，纯HS需实际映射，混合全适用范围需两者。无映射但服务明确跳过HS部分、其余货描照常且实际非空时，只保留有效部分并partial。没有这类证据、真正忽略或失效过滤、来源失败不得升格；有跳过/未查/截断或模式缺口时即使达到25家也不complete，缺口空结果不证明全部empty，完整警告与实费保留。不得另发付费映射查询或擅补HS。展示行逐项作 acquisition_selection 决定，注册身份、来源规模与资格分别核验；不限规模不证明规模已知。


仅新S06/采购商S62：结构化期间或截止日已确认缺口、或尚未检查时，都只交付部分范围；可见零行不证明全部为空，实扣照记，未检查不等于已确认缺口。其余七项获客、21项明细的原判断不随本修正改变。


两新任务保存查询的期间/截止日声明若缺失、null、非数组或畸形，亦按尚未检查强制partial；明确归属的一项未知单独保留，无归属则两项未知。有效行、可见0行与实际费保留；合法已解除状态与普通金额/重叠盲区不因此全部失败。

## 保存空分类历史说明

