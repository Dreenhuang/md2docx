"""
Markdown 解析器模块
将 Markdown 文本解析为结构化的 DocumentNode 树
支持 GFM 语法、YAML Front Matter、表格、列表、代码块等
"""

import re
import yaml
from dataclasses import dataclass, field
from typing import Optional
import markdown
from markdown.extensions.tables import TableExtension


@dataclass
class DocumentNode:
    """文档节点数据类，表示解析后的结构化文档元素"""

    node_type: str = ""
    level: int = 0
    content: str = ""
    children: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class MarkdownParser:
    """
    Markdown 解析器

    功能：
    - 解析 GFM（GitHub Flavored Markdown）语法
    - 提取 YAML Front Matter（title/author/date）
    - 识别 H1-H6 标题层级
    - 识别 **加粗** 重点内容
    - 解析表格、有序/无序列表
    - 解析代码块（```language）
    - 解析图片 ![alt](path)
    - 输出结构化 DocumentNode 数据类列表
    """

    def __init__(self):
        self.md = markdown.Markdown(
            extensions=[
                "tables",
                "fenced_code",
                "nl2br",
                "sane_lists",
            ],
            extension_configs={
                "tables": {},
            }
        )

    def parse(self, md_text: str) -> tuple[list[DocumentNode], dict]:
        """
        解析 Markdown 文本，返回节点列表和元信息

        参数：
            md_text: 原始 Markdown 文本内容

        返回：
            (nodes, front_matter): 节点列表和 YAML 前置元数据字典
        """
        front_matter = self._extract_front_matter(md_text)
        body_text = self._strip_front_matter(md_text)
        nodes = self._parse_body(body_text)
        return nodes, front_matter

    def parse_file(self, file_path: str) -> tuple[list[DocumentNode], dict]:
        """
        解析 Markdown 文件

        参数：
            file_path: Markdown 文件路径

        返回：
            (nodes, front_matter): 节点列表和元数据
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.parse(content)

    def _extract_front_matter(self, text: str) -> dict:
        """
        提取 YAML Front Matter

        支持 --- 包裹的 YAML 块，提取 title/author/date 等字段
        """
        front_matter = {}
        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(pattern, text, re.DOTALL)
        if match:
            try:
                front_matter = yaml.safe_load(match.group(1)) or {}
                if not isinstance(front_matter, dict):
                    front_matter = {}
            except yaml.YAMLError:
                front_matter = {}
        return front_matter

    def _strip_front_matter(self, text: str) -> str:
        """移除 Front Matter，返回正文部分"""
        pattern = r'^---\s*\n.*?\n---\s*\n'
        return re.sub(pattern, '', text, count=1, flags=re.DOTALL)

    def _parse_body(self, text: str) -> list[DocumentNode]:
        """
        解析正文，按行分析生成节点树

        处理顺序：
        1. 标题（# ## ### 等）
        2. 分隔线（--- *** ___）
        3. 表格（| 列 | 格 |）
        4. 代码块（```language ... ```）
        5. 无序列表（- * + 开头）
        6. 有序列表（1. 2. 3. 开头）
        7. 图片（![alt](path)）
        8. 普通段落
        """
        lines = text.split('\n')
        nodes = []
        i = 0

        while i < len(lines):
            line = lines[i].rstrip()

            if not line or line.strip() == '':
                i += 1
                continue

            node, consumed = self._parse_line(lines, i)
            if node:
                nodes.append(node)
            i += consumed if consumed > 0 else 1

        return nodes

    def _parse_line(self, lines: list[str], start_idx: int) -> tuple[Optional[DocumentNode], int]:
        """
        从指定行开始解析，返回节点和消耗的行数

        返回：(node, consumed_lines)
        """
        line = lines[start_idx]

        if line.startswith('#'):
            return self._parse_heading(line), 1

        if re.match(r'^[-*_]{3,}\s*$', line):
            return DocumentNode(node_type='horizontal_rule', content='---'), 1

        if '|' in line and line.startswith('|'):
            return self._parse_table(lines, start_idx)

        if line.startswith('```'):
            return self._parse_code_block(lines, start_idx)

        if re.match(r'^\s*[-*+]\s', line):
            return self._parse_list(lines, start_idx, ordered=False)

        if re.match(r'^\s*\d+[\.\)]\s', line):
            return self._parse_list(lines, start_idx, ordered=True)

        if '![' in line and '](' in line:
            img_node = self._parse_image(line)
            if img_node:
                return img_node, 1

        if line.strip().startswith('>'):
            return self._parse_blockquote(lines, start_idx)

        if line.strip():
            return self._parse_paragraph(line), 1

        return None, 1

    def _parse_heading(self, line: str) -> DocumentNode:
        """解析标题行 # ## ### #### ##### ######"""
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            level = len(match.group(1))
            content = match.group(2).strip()
            return DocumentNode(
                node_type='heading',
                level=level,
                content=content,
                metadata={'raw': line}
            )
        return DocumentNode(node_type='heading', level=1, content=line.lstrip('#').strip())

    def _parse_table(self, lines: list[str], start_idx: int) -> tuple[DocumentNode, int]:
        """
        解析 GFM 表格

        支持格式：
        | 列1 | 列2 | 列3 |
        |-----|-----|-----|
        | 内容 | 内容 | 内容 |
        """
        table_rows = []
        i = start_idx
        header_parsed = False

        while i < len(lines):
            line = lines[i].strip()
            if not line.startswith('|'):
                break
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if re.match(r'^[\s\-:|]+$', line.replace(' ', '')):
                i += 1
                header_parsed = True
                continue
            table_rows.append(cells)
            i += 1

        if len(table_rows) >= 1:
            headers = table_rows[0] if table_rows else []
            body_rows = table_rows[1:] if len(table_rows) > 1 else []
            return DocumentNode(
                node_type='table',
                level=0,
                content='',
                children=[
                    DocumentNode(node_type='table_header', content='', metadata={'cells': headers}),
                    *[DocumentNode(node_type='table_row', content='', metadata={'cells': row})
                      for row in body_rows]
                ],
                metadata={'headers': headers, 'row_count': len(body_rows)}
            ), i - start_idx

        return DocumentNode(node_type='table', content=''), i - start_idx

    def _parse_code_block(self, lines: list[str], start_idx: int) -> tuple[DocumentNode, int]:
        """
        解析围栏代码块

        支持格式：
        ```python
        code here
        ```
        """
        first_line = lines[start_idx]
        language = first_line[3:].strip()
        code_lines = []
        i = start_idx + 1

        while i < len(lines):
            if lines[i].startswith('```'):
                i += 1
                break
            code_lines.append(lines[i])
            i += 1

        return DocumentNode(
            node_type='code_block',
            level=0,
            content='\n'.join(code_lines),
            metadata={'language': language or 'text'}
        ), i - start_idx

    def _parse_list(self, lines: list[str], start_idx: int, ordered: bool) -> tuple[DocumentNode, int]:
        """
        解析有序/无序列表

        支持嵌套列表（通过缩进判断层级）
        """
        items = []
        i = start_idx

        while i < len(lines):
            line = lines[i]
            if ordered:
                match = re.match(r'^(\s*)(\d+)[\.\)]\s+(.+)$', line)
            else:
                match = re.match(r'^(\s*)[-*+]\s+(.+)$', line)

            if match:
                indent = len(match.group(1))
                content = match.group(2 if not ordered else 3).strip()
                items.append({
                    'content': content,
                    'indent': indent,
                    'ordered': ordered
                })
                i += 1
            elif line.strip() == '' and items:
                i += 1
                continue
            else:
                break

        children = [
            DocumentNode(
                node_type='list_item',
                level=item.get('indent', 0) // 2,
                content=item['content'],
                metadata={'ordered': item['ordered']}
            ) for item in items
        ]

        list_type = 'ordered_list' if ordered else 'unordered_list'
        return DocumentNode(
            node_type=list_type,
            level=0,
            content='',
            children=children,
            metadata={'item_count': len(items)}
        ), i - start_idx

    def _parse_image(self, line: str) -> Optional[DocumentNode]:
        """解析图片语法 ![alt](path)"""
        match = re.search(r'!\[([^\]]*)\]\(([^)]+)\)', line)
        if match:
            alt_text = match.group(1)
            path = match.group(2)
            return DocumentNode(
                node_type='image',
                level=0,
                content=alt_text,
                metadata={'src': path}
            )
        return None

    def _parse_blockquote(self, lines: list[str], start_idx: int) -> tuple[DocumentNode, int]:
        """
        解析引用块（blockquote）

        支持多行引用，自动去除 > 前缀
        格式：
        > 这是第一行引用
        > 这是第二行引用
        """
        quote_lines = []
        i = start_idx

        while i < len(lines):
            line = lines[i]
            if line.strip().startswith('>'):
                # 去除 > 和前面的空格
                cleaned = re.sub(r'^\s*>\s?', '', line).strip()
                quote_lines.append(cleaned)
                i += 1
            elif line.strip() == '':
                # 空行可能表示引用块结束或内部空行
                if i + 1 < len(lines) and lines[i + 1].strip().startswith('>'):
                    quote_lines.append('')
                    i += 1
                else:
                    break
            else:
                break

        content = '\n'.join(quote_lines)
        return DocumentNode(
            node_type='blockquote',
            level=0,
            content=content
        ), i - start_idx

    def _parse_paragraph(self, line: str) -> DocumentNode:
        """
        解析普通段落，同时检测内联加粗标记 **text**

        将加粗内容记录到 metadata 中供 DOCX 生成器使用
        """
        bold_parts = re.findall(r'\*\*(.+?)\*\*', line)
        return DocumentNode(
            node_type='paragraph',
            level=0,
            content=line,
            metadata={
                'has_bold': len(bold_parts) > 0,
                'bold_parts': bold_parts
            }
        )
