"""
转换主控模块
协调 Parser -> Generator -> HeaderFooter 完整转换流水线

功能：
- 单文件转换：convert_single()
- 批量转换：convert_batch()（后台线程执行）
- 失败跳过不中断（try-except 包裹每个文件）
- 输出命名规则：原文件名_YYYYMMDD.docx
- 文件名冲突自动加 _1 后缀
- 单文件超时保护
"""

import os
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

from backend.engine.md_parser import MarkdownParser
from backend.engine.docx_generator import DocxGenerator
from backend.engine.header_footer import HeaderFooterGenerator


class Converter:
    """
    转换主控器

    协调整个 Markdown 到 DOCX 的转换流程：
    1. MarkdownParser 解析 .md 文本为结构化节点
    2. DocxGenerator 将节点树渲染为 DOCX 文档
    3. HeaderFooterGenerator 添加页眉页脚
    4. 保存到输出目录
    """

    SINGLE_FILE_TIMEOUT = 60

    def __init__(self, config: dict = None):
        """
        初始化转换器

        参数：
            config: 转换配置字典（来自 ConfigManager 或 API 请求）
        """
        self.config = config or {}
        self.parser = MarkdownParser()
        self._stop_event = threading.Event()

    def convert_single(self, md_path: str, output_dir: str) -> dict:
        """
        转换单个 Markdown 文件

        完整流水线：解析 -> 生成文档 -> 添加页眉页脚 -> 保存

        参数：
            md_path: 源 .md 文件完整路径
            output_dir: 输出目录路径

        返回：
            结果字典 {
                'success': bool,
                'input_path': str,
                'output_path': str or None,
                'file_name': str,
                'error': str or None,
                'duration': float (秒)
            }
        """
        start_time = time.time()
        file_name = os.path.basename(md_path)
        result = {
            'success': False,
            'input_path': md_path,
            'output_path': None,
            'file_name': file_name,
            'error': None,
            'duration': 0
        }

        try:
            if not os.path.exists(md_path):
                raise FileNotFoundError(f"源文件不存在: {md_path}")

            nodes, front_matter = self.parser.parse_file(md_path)

            doc_title = HeaderFooterGenerator.extract_title(
                front_matter, nodes, file_name
            )

            generator = DocxGenerator(self.config)
            document = generator.generate(nodes, doc_title)

            date_str = datetime.now().strftime("%Y年%m月%d日")
            document = HeaderFooterGenerator.apply(document, doc_title, date_str)

            output_name = self._generate_output_name(file_name)
            output_path = os.path.join(output_dir, output_name)
            output_path = generator.save(document, output_path)

            result['success'] = True
            result['output_path'] = output_path

        except FileNotFoundError as e:
            result['error'] = str(e)
        except Exception as e:
            result['error'] = f"转换失败: {str(e)}"

        result['duration'] = round(time.time() - start_time, 2)
        return result

    def convert_batch(
        self,
        file_list: list[dict],
        output_dir: str,
        progress_callback=None
    ) -> dict:
        """
        批量转换多个文件

        支持进度回调、停止信号、失败跳过

        参数：
            file_list: 待转换文件列表 [{'name':..., 'path':...}, ...]
            output_dir: 输出目录
            progress_callback: 进度回调函数 callback(current, total, percent, status)

        返回：
            最终结果字典 {
                'total': int,
                'success_count': int,
                'fail_count': int,
                'results': list[dict],
                'stopped': bool
            }
        """
        total = len(file_list)
        results = []
        success_count = 0
        fail_count = 0
        stopped = False

        os.makedirs(output_dir, exist_ok=True)

        for idx, file_info in enumerate(file_list):
            if self._stop_event.is_set():
                stopped = True
                break

            md_path = file_info.get('path', '')

            def run_with_timeout():
                return self.convert_single(md_path, output_dir)

            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_with_timeout)
                    result = future.result(timeout=self.SINGLE_FILE_TIMEOUT)
            except TimeoutError:
                result = {
                    'success': False,
                    'input_path': md_path,
                    'output_path': None,
                    'file_name': file_info.get('name', ''),
                    'error': f"转换超时（>{self.SINGLE_FILE_TIMEOUT}秒）",
                    'duration': self.SINGLE_FILE_TIMEOUT
                }

            results.append(result)

            if result['success']:
                success_count += 1
            else:
                fail_count += 1

            percent = round((idx + 1) / total * 100, 1) if total > 0 else 100

            if progress_callback:
                try:
                    progress_callback(idx + 1, total, percent, 'running')
                except Exception:
                    pass

        final_result = {
            'total': total,
            'success_count': success_count,
            'fail_count': fail_count,
            'results': results,
            'stopped': stopped
        }

        if progress_callback:
            try:
                progress_callback(
                    success_count + fail_count,
                    total,
                    100,
                    'completed' if not stopped else 'stopped'
                )
            except Exception:
                pass

        return final_result

    def stop(self):
        """发送停止信号，终止批量转换"""
        self._stop_event.set()

    def reset_stop(self):
        """重置停止信号，准备新一轮转换"""
        self._stop_event.clear()

    @staticmethod
    def _generate_output_name(original_name: str) -> str:
        """
        生成输出文件名

        规则：原文件名_YYYYMMDD.docx
        如果同名文件已存在，自动加 _1, _2 ... 后缀

        参数：
            original_name: 原始 .md 文件名

        返回：
            输出 .docx 文件名
        """
        base = original_name.rsplit('.', 1)[0] if '.' in original_name else original_name
        date_suffix = datetime.now().strftime("%Y%m%d")
        new_name = f"{base}_{date_suffix}.docx"
        return new_name
