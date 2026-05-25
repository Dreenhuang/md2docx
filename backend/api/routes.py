"""
Flask API 路由模块
提供 md2docx 项目的全部 RESTful API 接口

路由分组：
- 文件操作 API：浏览目录、管理待转换文件列表
- 转换控制 API：启动/停止转换、查询进度
- 配置 API：读取/更新/重置配置
- 日志 API：查看/导出日志

全局状态：
- file_list: 待转换文件列表
- conversion_state: 转换状态（运行中/已完成等）
- log_entries: 日志记录列表
"""

import os
import json
import glob as glob_module
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file

from backend.config import ConfigManager
from backend.engine.converter import Converter


api_bp = Blueprint('api', __name__)

file_list: list[dict] = []
conversion_state: dict = {
    'running': False,
    'current': 0,
    'total': 0,
    'percent': 0,
    'status': 'idle',
    'results': []
}
log_entries: list[dict] = []
_converter_instance: Converter = None
_conversion_thread = None
_output_dir: str = ''


def _log(level: str, message: str):
    """添加日志条目"""
    entry = {
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'level': level.upper(),
        'message': message
    }
    log_entries.append(entry)
    if len(log_entries) > 500:
        log_entries[:] = log_entries[-500:]


@api_bp.route('/browse/input', methods=['POST'])
def browse_input():
    """
    扫描指定目录下的 .md 文件

    请求体：{"path": "目录路径"}
    返回：{files: [{name, path, size}, ...]}
    """
    try:
        data = request.get_json(silent=True) or {}
        target_path = data.get('path', '').strip()

        if not target_path:
            return jsonify({'error': '请提供目录路径'}), 400

        if not os.path.isdir(target_path):
            return jsonify({'error': f'目录不存在: {target_path}'}), 400

        pattern = os.path.join(target_path, '*.md')
        md_files = glob_module.glob(pattern)

        files_info = []
        for f in sorted(md_files):
            try:
                stat = os.stat(f)
                files_info.append({
                    'name': os.path.basename(f),
                    'path': f,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception:
                files_info.append({
                    'name': os.path.basename(f),
                    'path': f,
                    'size': 0,
                    'modified': ''
                })

        _log('INFO', f"扫描目录 {target_path}，找到 {len(files_info)} 个 .md 文件")
        return jsonify({'files': files_info, 'count': len(files_info)})

    except Exception as e:
        _log('ERROR', f"扫描目录失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/browse/output', methods=['POST'])
def set_output_dir():
    """
    设置输出目录路径

    请求体：{"path": "输出目录路径"}
    返回：{success: true, path: "..."}
    """
    global _output_dir
    try:
        data = request.get_json(silent=True) or {}
        output_path = data.get('path', '').strip()

        if not output_path:
            return jsonify({'error': '请提供输出目录路径'}), 400

        os.makedirs(output_path, exist_ok=True)
        _output_dir = output_path
        _log('INFO', f"设置输出目录: {output_path}")
        return jsonify({'success': True, 'path': output_path})

    except Exception as e:
        _log('ERROR', f"设置输出目录失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/files', methods=['GET'])
def get_files():
    """返回当前待转换文件列表"""
    return jsonify({'files': file_list, 'count': len(file_list)})


@api_bp.route('/files', methods=['POST'])
def add_files():
    """
    添加文件到待转换列表

    请求体：{"files": [{name, path}, ...]}
    返回：{success: true, addedCount: N, files: [...]}
    """
    global file_list
    try:
        data = request.get_json(silent=True) or {}
        new_files = data.get('files', [])

        if not new_files:
            return jsonify({'error': '未提供文件列表', 'addedCount': 0}), 400

        existing_names = {f['name'] for f in file_list}
        added_count = 0
        added_files = []

        for f in new_files:
            name = f.get('name', '')
            path = f.get('path', '')
            if not name:
                continue
            if name in existing_names:
                continue

            file_obj = {
                'id': f.get('id', str(len(file_list)) + '_' + name),
                'name': name,
                'path': path,
                'status': 'pending'
            }
            file_list.append(file_obj)
            existing_names.add(name)
            added_files.append(file_obj)
            added_count += 1

        _log('INFO', f"添加 {added_count} 个文件到转换列表（当前共 {len(file_list)} 个）")
        return jsonify({
            'success': True,
            'addedCount': added_count,
            'files': file_list,
            'count': len(file_list)
        })

    except Exception as e:
        _log('ERROR', f"添加文件失败: {str(e)}")
        return jsonify({'error': str(e), 'addedCount': 0}), 500


@api_bp.route('/files', methods=['DELETE'])
def clear_files():
    """清空待转换文件列表"""
    global file_list
    count = len(file_list)
    file_list = []
    _log('INFO', f"清空文件列表（原 {count} 个文件）")
    return jsonify({'success': True, 'cleared': count})


@api_bp.route('/convert/start', methods=['POST'])
def start_conversion():
    """
    开始批量转换（后台线程执行）

    请求体：{
        "config": {...可选配置覆盖...},
        "output_dir": "输出目录（可选）"
    }
    返回：{started: true, total: N}
    """
    global conversion_state, _conversion_thread, _converter_instance

    if conversion_state.get('running'):
        return jsonify({'error': '转换任务正在进行中，请先停止'}), 409

    try:
        data = request.get_json(silent=True) or {}
        config_override = data.get('config', {})
        output_dir = data.get('output_dir') or _output_dir

        if not output_dir:
            output_dir = os.environ.get('OUTPUT_DIR', 'output')

        if not file_list:
            return jsonify({'error': '待转换文件列表为空，请先添加文件'}), 400

        final_config = ConfigManager.get()
        if config_override and isinstance(config_override, dict):
            final_config = ConfigManager.validate({**final_config, **config_override})

        conversion_state = {
            'running': True,
            'current': 0,
            'total': len(file_list),
            'percent': 0,
            'status': 'running',
            'results': [],
            'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        _converter_instance = Converter(final_config)

        def _run_batch():
            global conversion_state
            def on_progress(current, total, percent, status):
                conversion_state['current'] = current
                conversion_state['total'] = total
                conversion_state['percent'] = percent
                conversion_state['status'] = status

            result = _converter_instance.convert_batch(
                file_list, output_dir, progress_callback=on_progress
            )
            conversion_state['running'] = False
            conversion_state['results'] = result.get('results', [])
            conversion_state['status'] = 'stopped' if result.get('stopped') else 'completed'
            conversion_state['end_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            success_count = result.get('success_count', 0)
            fail_count = result.get('fail_count', 0)
            _log(
                'INFO',
                f"批量转换完成: 成功 {success_count} / 失败 {fail_count} / 总计 {result.get('total', 0)}"
            )

        _conversion_thread = threading = __import__('threading', fromlist=['Thread']).Thread(
            target=_run_batch, daemon=True
        )
        _conversion_thread.start()

        _log('INFO', f"启动批量转换: {len(file_list)} 个文件 -> {output_dir}")
        return jsonify({
            'success': True,
            'taskId': str(id(_conversion_thread)),
            'totalFiles': len(file_list),
            'outputDir': output_dir
        })

    except Exception as e:
        conversion_state['running'] = False
        conversion_state['status'] = 'error'
        _log('ERROR', f"启动转换失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


import threading


@api_bp.route('/convert/stop', methods=['POST'])
def stop_conversion():
    """
    停止当前转换任务

    返回：{success: true, stopped: true, completedCount: N}
    """
    global _converter_instance
    try:
        if not conversion_state.get('running'):
            return jsonify({'success': True, 'stopped': False, 'warning': '当前没有正在运行的转换任务'})

        completed = conversion_state.get('current', 0)

        if _converter_instance:
            _converter_instance.stop()

        conversion_state['status'] = 'stopping'
        _log('INFO', "用户请求停止转换任务")
        return jsonify({
            'success': True,
            'stopped': True,
            'completedCount': completed
        })

    except Exception as e:
        _log('ERROR', f"停止转换失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/convert/progress', methods=['GET'])
def get_progress():
    """
    返回当前转换进度（格式与前端 app.js 期望完全对齐）

    前端期望字段：
    - progress: int (0-100)
    - currentIndex: int (当前处理到第几个，从0开始)
    - totalCount: int (总文件数)
    - completedFiles: string[] (已完成文件名列表)
    - failedFiles: string[]|{name, error}[] (失败文件列表)
    - logs: {level, message}[] (新增日志条目)
    - status: str
    - running: bool
    """
    base_response = {
        'progress': conversion_state.get('percent', 0),
        'currentIndex': max(0, conversion_state.get('current', 0) - 1),
        'totalCount': conversion_state.get('total', 0),
        'status': conversion_state.get('status', 'idle'),
        'running': conversion_state.get('running', False),
        'completedFiles': [],
        'failedFiles': [],
        'logs': []
    }

    if conversion_state.get('status') in ('completed', 'stopped'):
        results = conversion_state.get('results', [])
        for r in results:
            if r.get('success'):
                base_response['completedFiles'].append(r.get('name', ''))
            else:
                base_response['failedFiles'].append({
                    'name': r.get('name', ''),
                    'error': r.get('error', '未知错误')
                })

    return jsonify(base_response)


@api_bp.route('/config', methods=['GET'])
def get_config():
    """返回当前配置 JSON（包装为前端期望格式）"""
    config = ConfigManager.get()
    return jsonify({'success': True, 'config': config})


@api_bp.route('/config', methods=['PUT'])
def update_config():
    """
    更新配置参数

    请求体：{任意配置键值对}
    返回：{success: true, config: 更新后的完整配置}
    """
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400

        validated = ConfigManager.validate(data)
        updated = ConfigManager.update(validated)
        _log('INFO', f"更新配置: {list(data.keys())}")
        return jsonify({'success': True, 'config': updated})

    except Exception as e:
        _log('ERROR', f"更新配置失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/config/reset', methods=['POST'])
def reset_config():
    """
    恢复默认配置

    返回：{success: true, defaultConfig: 重置后的默认配置}
    """
    config = ConfigManager.reset()
    _log('INFO', "配置已恢复为默认值")
    return jsonify({'success': True, 'defaultConfig': config})


@api_bp.route('/logs', methods=['GET'])
def get_logs():
    """
    返回最近 N 条日志

    参数：?n=50 （默认 100 条）
    """
    n = request.args.get('n', '100')
    try:
        n = int(n)
        n = max(1, min(500, n))
    except (ValueError, TypeError):
        n = 100

    recent = log_entries[-n:] if log_entries else []
    return jsonify({'logs': recent, 'total': len(log_entries)})


@api_bp.route('/logs/export', methods=['GET', 'POST'])
def export_logs():
    """
    导出日志为 TXT 文件

    请求体：{"path": "导出路径（可选）"}
    返回：TXT 文件下载
    """
    try:
        data = request.get_json(silent=True) or {}
        export_path = data.get('path', '')

        if not export_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = os.path.join(os.environ.get('LOG_DIR', 'logs'), f'md2docx_log_{timestamp}.txt')

        dir_name = os.path.dirname(export_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(f"md2docx 日志导出 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            for entry in log_entries:
                f.write("[{time}] {level}: {message}\n".format(**entry))

        _log('INFO', f"日志已导出到: {export_path}")
        return send_file(export_path, as_attachment=True, download_name='md2docx_logs.txt')

    except Exception as e:
        _log('ERROR', f"导出日志失败: {str(e)}")
        return jsonify({'error': str(e)}), 500
