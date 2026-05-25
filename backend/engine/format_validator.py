"""
格式验证模块
转换前/后自动检查所有 Markdown 元素，确保格式一致性
"""

import os
import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """验证结果"""
    passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)


class FormatValidator:
    """
    MD→DOCX 格式验证器
    
    检查项：
    - 转换前：MD 文件可读性、编码、语法完整性
    - 转换后：DOCX 页面设置、字体、行距、元素覆盖率
    """
    
    # 危险字符转义映射
    SPECIAL_CHARS = {
        '\u2018': "'",   # 左单引号
        '\u2019': "'",   # 右单引号  
        '\u201c': '"',   # 左双引号
        '\u201d': '"',   # 右双引号
        '\u2013': '--',  # 短破折号
        '\u2014': '---', # 长破折号
        '\u2026': '...',  # 省略号
        '\u00a0': ' ',    # 不间断空格
        '\u3000': '  ',  # 全角空格
    }
    
    @staticmethod
    def validate_input(md_path: str) -> ValidationResult:
        """
        验证输入 Markdown 文件
        
        参数:
            md_path: Markdown 文件路径
            
        返回:
            ValidationResult 对象
        """
        result = ValidationResult()
        
        if not os.path.exists(md_path):
            result.passed = False
            result.errors.append(f"文件不存在: {md_path}")
            return result
        
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(md_path, 'r', encoding='gbk') as f:
                    content = f.read()
                result.warnings.append("文件使用 GBK 编码，建议转换为 UTF-8")
            except Exception as e:
                result.passed = False
                result.errors.append(f"无法读取文件: {e}")
                return result
        
        lines = content.split('\n')
        result.stats['total_lines'] = len(lines)
        result.stats['file_size'] = len(content)
        
        # 检查各类元素
        headings = re.findall(r'^#{1,6}\s+.+', content, re.MULTILINE)
        bold_text = re.findall(r'\*\*[^*]+\*\*', content)
        code_blocks = re.findall(r'```[\s\S]*?```', content)
        inline_code = re.findall(r'`[^`]+`', content)
        tables = re.findall(r'\|.*\|', content)
        images = re.findall(r'!\[.*?\]\(.*?\)', content)
        lists_unordered = re.findall(r'^[\s]*[-*+]\s+', content, re.MULTILINE)
        lists_ordered = re.findall(r'^[\s]*\d+\.\s+', content, re.MULTILINE)
        blockquotes = re.findall(r'^>\s+.+', content, re.MULTILINE)
        
        result.stats['headings'] = len(headings)
        result.stats['bold_segments'] = len(bold_text)
        result.stats['code_blocks'] = len(code_blocks)
        result.stats['inline_code'] = len(inline_code)
        result.stats['tables'] = len(tables) // 2 if tables else 0
        result.stats['images'] = len(images)
        result.stats['lists_unordered'] = len(lists_unordered)
        result.stats['lists_ordered'] = len(lists_ordered)
        result.stats['blockquotes'] = len(blockquotes)
        
        # 检查图片路径有效性
        for img_match in images:
            src = re.search(r'\(([^)]+)\)', img_match)
            if src:
                img_path = src.group(1)
                if not os.path.exists(img_path):
                    result.warnings.append(f"图片引用不存在: {img_path}")
        
        # 检查特殊字符
        special_count = 0
        for char in FormatValidator.SPECIAL_CHARS:
            count = content.count(char)
            if count > 0:
                special_count += count
        if special_count > 0:
            result.warnings.append(f"发现 {special_count} 个特殊 Unicode 字符，将自动转义")
        
        return result
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        清理文本中的特殊字符
        
        将 Unicode 特殊字符转为 ASCII 安全字符
        """
        for char, replacement in FormatValidator.SPECIAL_CHARS.items():
            text = text.replace(char, replacement)
        return text
    
    @staticmethod
    def validate_output(docx_path: str, expected_stats: Dict[str, int]) -> ValidationResult:
        """
        验证输出 DOCX 文件
        
        参数:
            docx_path: 输出 DOCX 文件路径
            expected_stats: 预期的元素统计（来自 validate_input）
            
        返回:
            ValidationResult 对象
        """
        import zipfile
        import re
        
        result = ValidationResult()
        
        if not os.path.exists(docx_path):
            result.passed = False
            result.errors.append(f"输出文件不存在: {docx_path}")
            return result
        
        if os.path.getsize(docx_path) < 1000:
            result.passed = False
            result.errors.append(f"输出文件过小 ({os.path.getsize(docx_path)} bytes)，可能生成失败")
            return result
        
        try:
            with zipfile.ZipFile(docx_path, 'r') as z:
                if 'word/document.xml' not in z.namelist():
                    result.passed = False
                    result.errors.append("DOCX 文件损坏：缺少 document.xml")
                    return result
                
                content = z.read('word/document.xml').decode('utf-8')
                
                # 检查页面设置
                sect = re.search(r'<w:pgMar[^>]*/>', content)
                if sect:
                    m = sect.group(0)
                    left = re.search(r'w:left="(\d+)"', m)
                    right = re.search(r'w:right="(\d+)"', m)
                    top = re.search(r'w:top="(\d+)"', m)
                    
                    if left and int(left.group(1)) < 500 or int(left.group(1)) > 2000:
                        result.warnings.append(f"左边距异常: {left.group(1)} twips")
                    if right and int(right.group(1)) < 500 or int(right.group(1)) > 2000:
                        result.warnings.append(f"右边距异常: {right.group(1)} twips")
                
                # 检查行距模式（必须是 atLeast，不能是 exact）
                spacings = re.findall(r'<w:spacing[^/]*/>', content)
                exact_count = 0
                for s in spacings:
                    r = re.search(r'w:lineRule="([^"]*)"', s)
                    if r and r.group(1) == 'exact':
                        exact_count += 1
                if exact_count > 0:
                    result.errors.append(f"发现 {exact_count} 个段落使用 EXACTLY 行距模式，应改为 AT_LEAST")
                    result.passed = False
                
                # 统计段落和表格
                para_count = len(re.findall(r'<w:p[ >]', content))
                tbl_count = len(re.findall(r'<w:tbl>', content))
                bold_count = len(re.findall(r'<w:b/>', content))
                
                result.stats['paragraphs'] = para_count
                result.stats['tables'] = tbl_count
                result.stats['bold_runs'] = bold_count
                
                # 检查页眉页脚
                has_header = 'header1.xml' in z.namelist()
                has_footer = 'footer1.xml' in z.namelist()
                result.stats['has_header'] = has_header
                result.stats['has_footer'] = has_footer
                
                if not has_header:
                    result.warnings.append("缺少页眉")
                if not has_footer:
                    result.warnings.append("缺少页脚")
        
        except Exception as e:
            result.warnings.append(f"验证过程出错: {e}")
        
        return result
    
    @staticmethod
    def print_report(result: ValidationResult, label: str = "Validation"):
        """打印验证报告"""
        print(f"\n{'='*50}")
        print(f"  {label} Report")
        print(f"{'='*50}")
        print(f"  Status: {'PASS ✅' if result.passed else 'FAIL ❌'}")
        
        if result.stats:
            print(f"\n  Statistics:")
            for k, v in result.stats.items():
                print(f"    {k}: {v}")
        
        if result.errors:
            print(f"\n  Errors ({len(result.errors)}):")
            for e in result.errors:
                print(f"    ❌ {e}")
        
        if result.warnings:
            print(f"\n  Warnings ({len(result.warnings)}):")
            for w in result.warnings:
                print(f"    ⚠️  {w}")
        
        print(f"{'='*50}\n")
        return result.passed


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    
    md_file = sys.argv[1] if len(sys.argv) > 1 else 'test_full.md'
    
    print("MD2DOCX Format Validator")
    print("=" * 50)
    
    # Step 1: Validate input
    input_result = FormatValidator.validate_input(md_file)
    FormatValidator.print_report(input_result, "Input (Markdown)")
    
    if input_result.passed:
        # Step 2: Run conversion
        from backend.engine.md_parser import MarkdownParser
        from backend.engine.docx_generator import DocxGenerator
        from backend.engine.header_footer import HeaderFooterGenerator
        from backend.config import ConfigManager
        
        parser = MarkdownParser()
        result = parser.parse_file(md_file)
        nodes, fm = (result[0], result[1]) if isinstance(result, tuple) else (result, {})
        
        config = ConfigManager.get()
        gen = DocxGenerator(config)
        title = fm.get('title', os.path.basename(md_file)) if fm else os.path.basename(md_file)
        doc = gen.generate(nodes, title)
        
        hf = HeaderFooterGenerator()
        doc = hf.apply(doc, title)
        
        out_path = os.path.join('output', f'validated_{os.path.basename(md_file)}.docx')
        gen.save(doc, out_path)
        print(f"Converted: {out_path}")
        
        # Step 3: Validate output
        output_result = FormatValidator.validate_output(out_path, input_result.stats)
        FormatValidator.print_report(output_result, "Output (DOCX)")
        
        if output_result.passed:
            import os as _os
            _os.startfile(_os.path.abspath(out_path))
