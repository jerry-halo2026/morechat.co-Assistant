# 企业资料获客四项：本地执行候选

精准获客 / 领英获客中的按产品、行业、相似度、标签找客户，分别使用 `task.type=company_discovery` 与 `product_profiles`、`industry_profiles`、`similar_profiles`、`tag_profiles`。同名的海关获客产品任务仍使用 `discovery/product_buyers`，上下文不清先澄清，不静默选海关路线。

主体分别为 `subject.product/industry/reference/tag` 的真实原词。产品、行业、标签必须给目标国家；相似任务不指定国家时保持全球，不按参考企业所在地缩小。约束为 `country`、`size_ranges`（A–I，可省略表示不限）、`limit`（默认20，1–500）；标签 `tag_scope` 只能 `public_business`。输出 O1 企业资料变体，默认聊天+Excel。未知条件或模板占位阻断；资料期未知，不能把企业页过滤成近一年。只有另行明确提出且具备授权的贸易核验才涉及近12个月，不在这四个任务自动调用。规划不调用数据源、零费、不要求委托方。

## 执行与续做

执行与续做按 SKILL.md 第 3 步写查询记录。每步钱包上限来自当前中央价格表，搜索每页≤50、详情每批≤20、关系每次≤50各1普通点；能力与行业字典免费。任务target500不能默改50；不足保留任务缺口。

执行和选择只用已取得的数据。已发出未记结果或费用未知的先告诉用户，不重发。失败、输入无效、服务忙、不可用不算成功空结果。换格式、续做或复用成功调用不新增查询、不丢历史费用。

## 四条流程与保存选择

先 `capabilities / describe_company_profiles(topic=capabilities)` 免费保存能力。

- 产品：`profiles / search_company_profiles` 的 `query` 使用业务词，保留目标国家和规模。
- 标签：同工具只使用 `business_tags` 公开主营标签，默认公开范围，私有客户标签未支持。
- 行业：`dictionary / describe_company_profiles(topic=industries, query=原行业, limit=50)` 保存真实字典。明确选择字典里的一行（调用编号、行号、该行真实有效编号）并记下依据，不能自动取首项。再按绑定 `industry_ids` 查询。字典续页须显式分页决定，只传同条件最后响应中的 `next_offset`。
- 相似：企业URL直接 `reference_profile / get_company_profiles(profiles=[原URL])`。真企业名先 `reference_candidates / search_company_profiles(query=原名, query_scope=[name], limit=20)`，不得用目标国家或规模筛参考候选。明确选择实际候选（调用编号、行号、企业页面）并记下依据，然后回查。只有唯一完整 `resolved` 才可 `related / find_related_companies(profile=已核对页面, relation_type=similar, limit=min(target,50))`。歧义或partial不选首项，不规则扩展、不自动补20。目标国家和规模依据逐目标回查资料过滤，不符排除、未知待核实，保留未解析关系、原序、截断和原调用缺口。

中文产品/公开标签由执行宿主提供保持原意的英文检索词，无外调或额外费用。先记下原词、采用的英文词、转换理由和依据，再用于后续查询参数；不能称数据库或字典完成语义翻译，不能为凑数扩展意思。已有英文直接采用，不重复确认。中文行业走真实字典，参考企业原名不翻译。

搜索续页只有用户明确要求更多才继续；游标必须来自相同完整条件、同页大小最后一次成功响应的 `next_cursor`。换词、改国家、删规模都须另建任务，不能套旧游标。

## 同源交付

分别调用 `get_render_spec(format=chat/xlsx, output_profile=O1, task_variant=company_profiles)`，聊天和 Excel 用同一批数据出成品并逐格回读。旧O1采购列与其他档案不改变。

至少展示公司名称、企业页面、官网、Logo、主页国家、地址、行业、规模、机构性质、业务标签、简介、匹配依据、关系类型与原序、回查状态、注册主体核对状态、营收原值、币种、资料期、核实状态、资料日期和来源；无员工数字列。收录简介可原样保留，人物片段或简介人数不能提为员工数字和筛选条件。Logo只保留真实URL，未打开不说已核验；仅Logo单元格可容纳已知图片域签名的随机版本形态，其他URL和后端词仍严格检查。

只称“符合本次资料筛选的候选”。页面条目不是注册主体去重，主页国家不是注册国；没有注册核对或贸易验证就始终待核实。相似报告列参考收录行业、规模与标签及逐目标比较，未知待核实；不造概率、竞对、采购或股权结论。跨页同规范页面去重、所有原关系证据保留；保留排除及待核实原因、实际来源、资料日期与查询时间、目标/取得/候选/缺口、原关系缺口/截断、未查范围与两钱包费用。10/20的实际部分成果可交付，成功零响应可empty，失败或未查询不能说没客户。

便携自检的四份合成请求、计划、响应和规范在 `self_check_data/company_profiles/`，`company_profiles_examples.py` 完整执行四条链，生成聊天、Excel并回放检查；它们都明确为合成演示、未查询真实数据，不作为用户响应。
