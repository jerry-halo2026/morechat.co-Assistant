#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown 简历 → Word (.docx) 导出 —— 零依赖，仅用标准库。

把优化后的 Markdown 简历转成基础 Word 文档（标题加粗、列表项、正文）。
注意：这是「基础可编辑的 Word」，不是花哨排版（排版美化需依赖第三方库）。

用法:
  python3 export_docx.py <简历.md> [输出.docx]
"""
import argparse
import sys
import xml.sax.saxutils
import zipfile
from pathlib import Path


def esc(text):
    return xml.sax.saxutils.escape(text)


def md_to_docx(md_path, docx_path):
    lines = Path(md_path).read_text(encoding='utf-8', errors='replace').splitlines()

    body_parts = []
    for line in lines:
        line = line.rstrip()
        if not line.strip():
            continue
        if line.startswith('# '):
            body_parts.append(
                f'<w:p><w:r><w:rPr><w:b/><w:sz w:val="32"/></w:rPr><w:t>{esc(line[2:])}</w:t></w:r></w:p>')
        elif line.startswith('## '):
            body_parts.append(
                f'<w:p><w:r><w:rPr><w:b/><w:sz w:val="28"/></w:rPr><w:t>{esc(line[3:])}</w:t></w:r></w:p>')
        elif line.startswith(('- ', '* ', '• ')):
            body_parts.append(f'<w:p><w:r><w:t>• {esc(line[2:])}</w:t></w:r></w:p>')
        else:
            body_parts.append(f'<w:p><w:r><w:t>{esc(line)}</w:t></w:r></w:p>')

    body = ''.join(body_parts)
    document_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    f'<w:body>{body}'
                    '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr></w:body></w:document>')

    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                     '</Types>')

    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')

    with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types)
        zf.writestr('_rels/.rels', rels)
        zf.writestr('word/document.xml', document_xml)

    print(f'已生成 Word 简历: {docx_path}')


class _ArgParser(argparse.ArgumentParser):
    def error(self, message):
        print(f'[导出未完成] 参数不正确：{message}')
        print('用法：python3 export_docx.py <简历.md> [输出.docx]')
        sys.exit(0)


def main():
    ap = _ArgParser(description='Markdown 简历 → Word (.docx) 导出')
    ap.add_argument('md_path', help='Markdown 文件路径')
    ap.add_argument('docx_path', nargs='?', help='输出 .docx 路径（默认同名）')
    args = ap.parse_args()

    out = args.docx_path or str(Path(args.md_path).with_suffix('.docx'))
    try:
        md_to_docx(args.md_path, out)
    except FileNotFoundError as e:
        print(f'[导出未完成] 找不到文件：{e.filename}（请先把简历保存为 .md 文件）')
        sys.exit(0)
    except IsADirectoryError:
        print('[导出未完成] 传入的是目录，请指定 .md 文件。')
        sys.exit(0)
    except Exception as e:
        print(f'[导出未完成] {type(e).__name__}: {e}')
        sys.exit(0)


if __name__ == '__main__':
    main()
