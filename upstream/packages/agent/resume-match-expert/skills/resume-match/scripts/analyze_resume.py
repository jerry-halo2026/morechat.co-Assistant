#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简历 × JD 匹配分析器 —— 零依赖，仅用 Python 标准库。

帮求职者客观评估「简历和岗位的匹配度」，找出差距，给出可落地的修改方向。
核心能力（这是 AI 无法可靠完成的真计算）：
  1. 技能关键词提取 + 匹配度计算（命中率）；
  2. 差距分析（JD 要求但简历缺失的技能）；
  3. ATS 友好度检查（大厂机器筛简历的关键点）；
  4. 量化成果检查（成就是否有数据支撑）。

用法:
  python3 analyze_resume.py <简历文件> [JD文件]
  python3 analyze_resume.py <简历文件> --jd <JD文本>
"""
import argparse
import datetime
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# ==================== 技能词典（按行业组织，覆盖技术与非技术岗位）====================
TECH_SKILLS = (
    'python', 'java', 'javascript', 'typescript', 'golang', 'go语言', 'c++', 'c语言',
    'rust', 'kotlin', 'swift', 'php', 'ruby', 'sql', 'html', 'css', 'shell',
    'flask', 'django', 'fastapi', 'spring', 'springboot', 'node.js', 'nodejs', 'express',
    'react', 'vue', 'angular', '微信小程序', '小程序',
    'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'sqlite', 'oracle',
    'docker', 'kubernetes', 'k8s', 'linux', 'git', 'ci/cd', 'devops', 'aws', '阿里云', '腾讯云', 'nginx',
    '机器学习', '深度学习', '数据分析', '数据挖掘', '爬虫', 'nlp', '自然语言处理',
    '计算机视觉', 'pytorch', 'tensorflow', '大模型', 'llm', 'agent',
    '微服务', '分布式', '消息队列', 'kafka', 'rabbitmq', '多线程', '高并发', '性能优化',
    '后端开发', '前端开发', '全栈开发', '测试', '自动化测试', '单元测试', '接口测试',
    # AI Agent / 现代技术
    'nestjs', 'prisma', 'electron', 'chromium', 'next.js', 'nextjs', 'graphql', 'rag', 'mcp',
    '多智能体', '智能体', '会话管理', '上下文压缩', '工具调用', '工具调度', '流式输出',
    '向量检索', 'embedding', '语义检索', '知识库', '混合检索', '浏览器自动化', 'im机器人',
    '多模态', '语音识别', 'ocr', 'function calling', 'autogen', 'langchain', 'llamaindex',
)
MARKETING_SKILLS = (
    '数字营销', 'seo', 'sem', '内容营销', '品牌策划', '品牌营销', '增长黑客', '广告投放',
    '社群运营', '私域流量', '短视频运营', '直播运营', '市场调研', '竞品分析',
    '新媒体运营', '公众号运营', '文案策划', '活动策划', '整合营销', '品牌推广', '社交媒体运营',
)
DESIGN_SKILLS = (
    'ui设计', 'ux设计', '平面设计', 'figma', 'sketch', 'photoshop', 'illustrator',
    '插画', '品牌设计', '交互设计', '视觉设计', '动效设计', '三维设计', 'c4d', '包装设计',
)
FINANCE_SKILLS = (
    '财务分析', '会计', '审计', '税务', 'cpa', 'cfa', '风控', '投资分析', '预算管理',
    '成本控制', '财务报表', '财务建模', '资金管理', '内控', '财务核算', '总账',
)
HR_SKILLS = (
    '招聘', '绩效管理', '薪酬福利', '员工关系', '培训', '劳动法', 'hrbp', '组织发展',
    '人才盘点', '企业文化', '猎头', '薪酬设计', '人力资源', 'hr',
)
OPS_SKILLS = (
    '用户运营', '电商运营', '内容运营', '活动运营', '数据运营', '增长运营', '供应链',
    '商品运营', '类目运营', '转化率优化', '用户增长', '商家运营',
)
SALES_SKILLS = (
    '大客户销售', '渠道销售', '电话销售', 'crm', '客户关系', '谈判技巧', '商务拓展',
    'bd', '销售管理', '客户成功', '解决方案销售', '销售', '地推',
)
PRODUCT_SKILLS = (
    '产品经理', '需求分析', '原型设计', 'axure', '用户研究', '项目管理', '敏捷',
    'prd', '产品规划', '增长', '用户增长', '产品设计',
)
EDU_SKILLS = (
    '教学设计', '课程开发', '教育学', '心理学', '教师资格', '授课', '教研', '班主任', '教育',
)
LEGAL_SKILLS = (
    '合同法', '公司法', '知识产权', '诉讼', '法考', '法律文书', '合规', '尽职调查', '法律',
)
ADMIN_SKILLS = (
    '办公软件', 'excel', 'ppt', '公文写作', '会议组织', '档案管理', '行政', '文秘',
)
SOFT_SKILLS = (
    '沟通能力', '沟通协调', '团队协作', '项目管理', '领导力', '问题解决', '学习能力',
    '抗压能力', '英语', '文档撰写', '需求分析', '跨部门协作', '敏捷开发', 'scrum',
)
MANUFACTURING_SKILLS = (
    '精益生产', '精益改善', '持续改善', '六西格玛', 'spc', '统计过程控制',
    'iso9001', 'iso14001', 'iatf16949', '5s', '全面质量管理', 'tqm', 'fmea', '8d',
    '生产计划', '排产', '产能规划', '良率', '不良率', '质量管理', '质量控制',
    '安全生产', '设备管理', '设备维护', '工艺', '注塑', '冲压', '焊接', '装配',
    '产线', '车间', '制造', '生产管理', '制程', '供应商管理', '采购管理',
    '库存管理', '仓储管理', '物流管理', '库存周转', '交期', '降本增效',
    '工业工程', '机电一体化', 'cnc', '数控', 'plc', '汽车零部件',
)

# 所有行业技能（提取时遍历）
ALL_SKILLS = (TECH_SKILLS + MARKETING_SKILLS + DESIGN_SKILLS + FINANCE_SKILLS +
              HR_SKILLS + OPS_SKILLS + SALES_SKILLS + PRODUCT_SKILLS +
              EDU_SKILLS + LEGAL_SKILLS + ADMIN_SKILLS + SOFT_SKILLS +
              MANUFACTURING_SKILLS)


def norm_text(text):
    return text.lower().replace('-', ' ').replace('_', ' ')


# ==================== 文件读取 ====================
def read_text(path):
    p = Path(path)
    if p.suffix == '.docx':
        return read_docx(p)
    for enc in ('utf-8', 'gb18030'):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return p.read_text(encoding='utf-8', errors='replace')


def read_docx(path):
    zf = zipfile.ZipFile(path)
    ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    root = ET.fromstring(zf.read('word/document.xml'))
    lines = []
    for para in root.iter(ns + 'p'):
        line = ''.join(t.text or '' for t in para.iter(ns + 't'))
        if line.strip():
            lines.append(line)
    zf.close()
    return '\n'.join(lines)


# ==================== 技能提取 ====================
def extract_skills(text):
    """从文本提取命中的技能关键词（英文技能用词边界，避免 sql 误匹配 mysql）"""
    nt = norm_text(text)
    found = set()
    for s in ALL_SKILLS:
        ns = norm_text(s)
        if re.search(r'[a-z]', ns):
            # 英文技能：前后不能是英文字母
            if re.search(r'(?<![a-z])' + re.escape(ns) + r'(?![a-z])', nt):
                found.add(s)
        else:
            if s in text:
                found.add(s)
    return found


def extract_jd_requirements(jd_text):
    reqs = set(extract_skills(jd_text))
    expanded = re.sub(r'[（(]([^）)]*)[）)]', r'、\1、', jd_text)
    triggers = r'(?:熟悉|精通|掌握|了解|熟练|擅长|具备|拥有|要求|需要)'
    latin_stop = {'and', 'or', 'the', 'with', 'for', 'to', 'of'}
    generic = ('基础', '基本', '使用', '调用', '工程', '框架', '开发', '项目',
               '至少', '能力', '经验', '优先', '流程', '部署', '相关',
               '以上', '学历', '简单', '界面', '能做', '等', '了解', '熟悉',
               '掌握', '精通', '熟练', '擅长', '具备', '拥有', '要求', '需要')
    for m in re.findall(triggers + r'[：:，,、\s]*([^。；;\n]+)', expanded):
        for part in re.split(r'[、，,;；/\n]+', m.strip()):
            part = part.strip()
            if not part:
                continue
            for token in re.findall(r'[A-Za-z][A-Za-z0-9.+#-]*(?:\s+[A-Za-z][A-Za-z0-9.+#-]*)*', part):
                if len(token) >= 2 and token.lower() not in latin_stop:
                    reqs.add(token)
            zh = re.sub(r'[A-Za-z0-9.+#/()\s]+', '', part)
            if 2 <= len(zh) <= 8 and not any(w in zh for w in generic):
                reqs.add(zh)
    return reqs


def has_contact(text):
    return bool(re.search(r'1[3-9]\d{9}', text)) or bool(re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text))


def extract_years(text):
    """提取工作年限（"X 年经验" 或日期范围如 "2022-至今"/"2020-2023"）"""
    years = [int(x) for x in re.findall(r'(\d+)\s*年', text) if 0 < int(x) <= 40]
    current_year = datetime.datetime.now().year
    for m in re.findall(r'(20\d{2})\s*[-—~至]\s*(20\d{2}|至今|今)', text):
        start = int(m[0])
        end = current_year if m[1] in ('至今', '今') else int(m[1])
        if 0 < end - start <= 40:
            years.append(end - start)
    return max(years) if years else None


def extract_education(text):
    """提取最高学历（含技校信号）"""
    for level in ('博士', '硕士', '研究生', '本科', '大专', '专科', '高中'):
        if level in text:
            return level
    # 技校信号（无明确学历等级时，如「XX工业学校」「XX职业技术学院」）
    for sig in ('技校', '中专', '职高', '职业学校', '职业技术学院', '工业学校', '技师学院', '职业学院'):
        if sig in text:
            return '技校/中专'
    return None


# 弱动词（简历里最常见的「空泛」开头）
WEAK_VERBS = ('负责', '参与', '协助', '帮助', '处理', '维护', '进行', '完成',
              '使用', '管理', '支持', '配合', '跟进', '协调', '整理')

# 弱动词 → 强动词替换（具体优化建议）
STRONG_VERBS = {
    '负责': '主导 / 搭建 / 推进',
    '参与': '负责 / 推动',
    '协助': '支撑 / 配合',
    '帮助': '推动 / 促成',
    '处理': '解决 / 排查',
    '维护': '保障 / 优化',
    '进行': '执行 / 推进',
    '完成': '交付 / 达成',
    '使用': '运用 / 采用',
    '管理': '统筹 / 带领',
    '支持': '支撑 / 赋能',
    '配合': '协同 / 联动',
    '跟进': '推进 / 闭环',
    '协调': '统筹 / 调度',
    '整理': '梳理 / 沉淀',
}


def detect_weak_verbs(bullets):
    """检测以弱动词开头的 bullet（弱动词 = 只描述「做了」没描述「成果」）"""
    weak = []
    for b in bullets:
        for wv in WEAK_VERBS:
            if b.startswith(wv):
                weak.append((b, wv))
                break
    return weak


def resume_score(r, weak_count):
    bd = {}
    total_b = len(r['quantified']) + len(r['vague'])
    bd['量化'] = round(30 * (len(r['quantified']) / total_b)) if total_b else 0
    bd['ATS'] = max(0, 20 - len(r['ats_issues']) * 4)
    bd['弱动词'] = max(0, 10 - weak_count * 2)
    n = r['resume_chars']
    bd['长度'] = 10 if 300 <= n <= 2000 else (5 if n > 0 else 0)
    if r.get('match_rate') is not None:
        bd['匹配度'] = round(30 * r['match_rate'] / 100)
        max_score = 100
    else:
        bd['匹配度'] = None
        max_score = 70
    total = sum(v for v in bd.values() if v is not None)
    return round(min(100, total * 100 / max_score)), bd


# 常见用词问题（啰嗦表达 + 高频错别字，可靠的高频误用）
COMMON_ISSUES = (
    ('进行了', '啰嗦：建议去掉「进行」，直接说动作'),
    ('进行优化', '啰嗦：建议说「优化」'),
    ('进行管理', '啰嗦：建议说「管理」'),
    ('进行沟通', '啰嗦：建议说「沟通」'),
    ('进行开发', '啰嗦：建议说「开发」'),
    ('在见', '错别字：应为「再见」'),
    ('在来', '错别字：应为「再来」'),
    ('在一次', '错别字：应为「再一次」'),
)


def check_wording(text):
    """极简用词检查（啰嗦表达 + 高频错别字，非完整语法检查）"""
    return [(p, m) for p, m in COMMON_ISSUES if p in text]


# ==================== 量化检查 ====================
def extract_bullets(text):
    """提取经历条目：- 列表项 + 工作/项目经历章节下的段落（支持段落式简历）"""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # 经历章节标题（支持 markdown 前缀，如「## 工作经历」）
    exp_re = re.compile(r'^#{0,6}\s*(工作经历|项目经历|实习经历|工作经验)')
    stop_re = re.compile(r'^#{0,6}\s*(技能|教育|联系|自我评价|基本信息|照片|求职意向)')
    has_exp_section = any(exp_re.match(l) for l in lines)
    bullets = []
    in_section = False
    for line in lines:
        if exp_re.match(line):
            in_section = True
            continue
        if stop_re.match(line):
            in_section = False
            continue
        if in_section:
            cleaned = line.replace('**', '')
            # 跳过经历标题行（markdown 子标题或含时间范围，如「### 2021.03 - 至今」「（2023 - 2026.05」）
            if cleaned.startswith('#') or '（20' in cleaned or '（19' in cleaned:
                continue
            # 去掉列表标记（- • * 1. 等）
            cleaned = re.sub(r'^[-•*·、]+\s*|^\d{1,2}[.、]\s*', '', cleaned)
            # 段落式经历：去掉「时间 + 在 XX 担任 XX」前缀，保留动作描述（如「负责…」「参与…」）
            cleaned = re.sub(r'^\d{4}[.\-/]?\d{0,2}\s*[-—~至]?\s*(至今|今|\d{4}[.\-/]?\d{0,2})?\s*在.*?担任.*?[，,]', '', cleaned)
            if len(cleaned) > 5:
                bullets.append(cleaned)
        elif has_exp_section:
            # 文档含经历章节时，章节外的 dash bullet（如技能清单）不再当作经历
            continue
        else:
            # 无经历章节（旧行为兜底）：捕获所有 dash bullet
            if re.match(r'^[-•*·]', line) and len(line) > 5:
                bullets.append(re.sub(r'^[-•*·]\s*', '', line))
    return bullets


def is_quantified(bullet):
    # 含数字/百分比/量词，视为有量化
    return bool(re.search(r'\d|%|万|倍|个|项|次|人|元|条|款|版', bullet))


# ==================== ATS 检查 ====================
def ats_check(text, matched, jd_skills):
    checks = []
    # 标准模块
    sections = {
        '联系方式': has_contact(text),
        '教育背景': bool(re.search(r'教育|学历|学校|大学|本科|硕士|博士', text)),
        '工作/项目经历': bool(re.search(r'工作经历|工作经验|项目经历|实习', text)),
        '技能清单': bool(re.search(r'技能|技术栈|专业技能', text)),
    }
    for name, ok in sections.items():
        if not ok:
            checks.append(f'缺少「{name}」模块（ATS 可能无法识别）')
    # 长度
    n_chars = len(text)
    if n_chars < 300:
        checks.append('简历过短（<300 字），内容可能不完整')
    elif n_chars > 4000:
        checks.append('简历过长（>4000 字），建议精简到 1-2 页')
    # 关键词密度（用 matched：已做大小写不敏感匹配，避免词典小写 vs JD 原大小写导致恒为 0%）
    if jd_skills:
        density = len(matched) / len(jd_skills) * 100
        if density < 30:
            checks.append(f'JD 关键词密度过低（{density:.0f}%），ATS 机器筛选可能被过滤')
    return checks


# ==================== 主分析 ====================
def analyze(resume_path, jd_text=None, jd_path=None):
    resume = read_text(resume_path)
    jd = jd_text if jd_text else (read_text(jd_path) if jd_path else None)

    resume_skills = extract_skills(resume)
    if jd:
        jd_skills = extract_jd_requirements(jd) | extract_skills(jd)
        unique_by_lower = {}
        for skill in jd_skills:
            key = skill.lower()
            current = unique_by_lower.get(key)
            if current is None or (current == key and skill != key):
                unique_by_lower[key] = skill
        jd_skills = set(unique_by_lower.values())
    else:
        jd_skills = set()

    result = {
        'resume_chars': len(resume),
        'resume_skills': resume_skills,
        'jd_skills': jd_skills,
        'resume_years': extract_years(resume),
        'jd_years': extract_years(jd) if jd else None,
        'resume_edu': extract_education(resume),
        'jd_edu': extract_education(jd) if jd else None,
    }

    # 匹配度（JD 技能在简历文本中是否出现，覆盖固定词典之外的任何领域）
    if jd_skills:
        resume_nt = norm_text(resume)
        matched = set()
        for s in jd_skills:
            ns = norm_text(s)
            if ns in resume_nt or s in resume:
                matched.add(s)
        missing = jd_skills - matched
        result['match_rate'] = round(len(matched) / len(jd_skills) * 100)
        result['matched'] = matched
        result['missing'] = missing
    else:
        result['match_rate'] = None
        result['matched'] = set()
        result['missing'] = set()

    # 量化检查
    bullets = extract_bullets(resume)
    quantified = [b for b in bullets if is_quantified(b)]
    vague = [b for b in bullets if not is_quantified(b)]
    result['quantified'] = quantified
    result['vague'] = vague

    # 弱动词
    weak = detect_weak_verbs(bullets)
    result['weak_verbs'] = weak

    # ATS 检查
    result['ats_issues'] = ats_check(resume, result['matched'], jd_skills)

    # 综合评分
    result['score'], result['score_breakdown'] = resume_score(result, len(weak))

    # 用词检查
    result['wording_issues'] = check_wording(resume)

    return result


def print_report(r):
    print('===== 简历 × JD 匹配分析报告 =====')
    print(f'简历长度: {r["resume_chars"]} 字')
    print(f'识别到的技能数: {len(r["resume_skills"])}')
    if r.get('score') is not None:
        suffix = '' if r['match_rate'] is not None else '（无 JD，按其余维度折算）'
        print(f'📊 简历综合评分: {r["score"]} / 100{suffix}')
        bd = r['score_breakdown']
        if r['match_rate'] is not None:
            print(f'   （量化 {bd["量化"]}/30 · 匹配 {bd["匹配度"]}/30 · ATS {bd["ATS"]}/20 · 弱动词 {bd["弱动词"]}/10 · 长度 {bd["长度"]}/10）')
        else:
            print(f'   （量化 {bd["量化"]}/30 · ATS {bd["ATS"]}/20 · 弱动词 {bd["弱动词"]}/10 · 长度 {bd["长度"]}/10；无 JD，匹配度不计）')
    print()

    if r['match_rate'] is not None:
        print(f'[JD 匹配度] {r["match_rate"]}%')
        bar = '█' * (r['match_rate'] // 10) + '░' * (10 - r['match_rate'] // 10)
        print(f'  {bar}')
        if r['matched']:
            print(f'  ✅ 命中的技能（{len(r["matched"])} 个）: {", ".join(sorted(r["matched"]))}')
        if r['missing']:
            print(f'  ❌ JD 要求但简历缺失（{len(r["missing"])} 个）: {", ".join(sorted(r["missing"]))}')
            print('  → 这些是简历里该补的关键词，也是 ATS 筛简历会看重的')
    else:
        print('[JD 匹配度] 未提供 JD，跳过匹配分析（用 --jd 或传入 JD 文件）')
    print()

    # 年限与学历匹配
    if r.get('jd_years') or r.get('jd_edu'):
        print('[年限与学历匹配]')
        if r.get('jd_years'):
            ry = r.get('resume_years') or 0
            jy = r['jd_years']
            if ry >= jy:
                print(f'  年限: 简历 {ry} 年 ≥ JD 要求 {jy} 年 ✓')
            else:
                print(f'  年限: 简历约 {ry} 年 < JD 要求 {jy} 年 ✗（差 {jy - ry} 年）')
        if r.get('jd_edu'):
            if r.get('resume_edu') == r['jd_edu']:
                print(f'  学历: 简历 {r["resume_edu"]} = JD 要求 {r["jd_edu"]} ✓')
            elif r.get('resume_edu'):
                print(f'  学历: 简历 {r["resume_edu"]} vs JD 要求 {r["jd_edu"]}')
            else:
                print(f'  学历: JD 要求 {r["jd_edu"]}，简历未明确标注学历')
        print()

    # 量化检查
    total_b = len(r['quantified']) + len(r['vague'])
    if total_b:
        print(f'[量化成果检查] {len(r["quantified"])}/{total_b} 条经历有数据支撑')
        if r['vague']:
            print(f'  ⚠ {len(r["vague"])} 条经历无量化（空泛描述，说服力弱）:')
            for b in r['vague'][:5]:
                print(f'    - {b[:50]}')
            print('  → 量化模板：动作 + 对象 + 数字 + 结果')
            print('    例：「负责订单模块优化」→「主导订单流程优化，将下单耗时从 3s 降至 0.5s」')
    print()

    # 弱动词检查
    if r.get('weak_verbs'):
        print(f'[弱动词检查] {len(r["weak_verbs"])} 条经历用弱动词开头')
        for b, wv in r['weak_verbs'][:5]:
            replace = STRONG_VERBS.get(wv, '强动作动词')
            print(f'  ⚠ 「{b[:40]}」以「{wv}」开头 → 建议改为「{replace}」')
        print('  → 开头用强动词，直接体现你「做了什么、做出了什么成果」')
    print()

    # ATS 检查
    print(f'[ATS 友好度检查]')
    if r['ats_issues']:
        for issue in r['ats_issues']:
            print(f'  ⚠ {issue}')
    else:
        print('  未发现明显 ATS 问题')
    print()

    # 用词检查
    if r.get('wording_issues'):
        print(f'[用词检查]（极简检查，非完整语法）')
        for pattern, msg in r['wording_issues']:
            print(f'  ⚠ 「{pattern}」→ {msg}')
        print()

    print('===== 分析结束（深度解读与改写建议请结合 resume-guide 由 AI 完成）=====')


class _ArgParser(argparse.ArgumentParser):
    def error(self, message):
        print(f'[分析未完成] 参数不正确：{message}')
        print('用法：python3 analyze_resume.py <简历文件> [JD文件]，或 --jd "JD文本"')
        sys.exit(0)


def main():
    ap = _ArgParser(description='简历 × JD 匹配分析器')
    ap.add_argument('resume', help='简历文件路径（md/txt/docx）')
    ap.add_argument('jd', nargs='?', help='JD 文件路径（可选）')
    ap.add_argument('--jd', dest='jd_text', help='JD 文本（可选，直接传文字）')
    args = ap.parse_args()

    try:
        r = analyze(args.resume, jd_text=args.jd_text, jd_path=args.jd)
    except FileNotFoundError as e:
        print(f'[分析未完成] 找不到文件：{e.filename}')
        print('提示：如果简历/JD 是粘贴的文字，请先保存为 .md 或 .txt 文件；也可直接人工分析。')
        sys.exit(0)
    except IsADirectoryError:
        print('[分析未完成] 传入的是目录，请指定具体的简历文件。')
        sys.exit(0)
    except zipfile.BadZipFile:
        print('[分析未完成] .docx 文件损坏或不是有效的 Word 文档，请另存为 .md/.txt 后重试。')
        sys.exit(0)
    except UnicodeDecodeError:
        print('[分析未完成] 文件编码无法识别，请另存为 UTF-8 的 .txt 后重试。')
        sys.exit(0)
    except Exception as e:
        print(f'[分析未完成] {type(e).__name__}: {e}')
        print('提示：请改为人工分析，不要向用户报错。')
        sys.exit(0)

    print_report(r)


if __name__ == '__main__':
    main()
