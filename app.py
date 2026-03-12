#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker打印服务器 - Flask应用
支持文件上传、格式转换和打印功能
"""

import os
import subprocess
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import mimetypes

# 导入格式转换工具
from utils.file_converter import FileConverter
from utils.printer_manager import PrinterManager
from utils.print_history import PrintHistory

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# 配置
UPLOAD_FOLDER = '/app/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 初始化工具
file_converter = FileConverter()
printer_manager = PrinterManager()
print_history = PrintHistory()


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    logger.info(f"allowed_file检查: filename={filename}")
    if not filename:
        logger.info(f"文件名无效: filename为空")
        return False
    # 使用rsplit('.', 1)更安全地获取扩展名（处理docx, xlsx等）
    parts = filename.rsplit('.', 1)
    if len(parts) < 2:
        logger.info(f"文件名没有扩展名")
        return False
    file_ext = parts[1].lower()
    logger.info(f"提取的扩展名: file_ext={file_ext}")
    result = file_ext in ALLOWED_EXTENSIONS
    logger.info(f"扩展名检查结果: {result}")
    return result


@app.route('/')
def index():
    """主页 - 显示上传界面"""
    return render_template('index.html')


@app.route('/api/printers', methods=['GET'])
def get_printers():
    """获取可用打印机列表"""
    try:
        printers = printer_manager.list_printers()
        return jsonify({
            'success': True,
            'printers': printers
        })
    except Exception as e:
        logger.error(f"获取打印机列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件并打印（支持多文件）"""
    try:
        # 检查是否有文件
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400

        files = request.files.getlist('files')
        printer_name = request.form.get('printer', '')
        copies = request.form.get('copies', '1')
        sides = request.form.get('sides', 'one-sided')
        page_range = request.form.get('pageRange', '').strip()
        
        if not files or files[0].filename == '':
            return jsonify({
                'success': False,
                'error': '未选择文件'
            }), 400
        
        # 验证打印份数
        try:
            copies = int(copies)
            if copies < 1 or copies > 100:
                return jsonify({
                    'success': False,
                    'error': '打印份数必须在1-100之间'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'error': '打印份数必须是有效的数字'
            }), 400
        
        # 验证双面打印选项
        valid_sides = ['one-sided', 'two-sided-long-edge', 'two-sided-short-edge']
        if sides not in valid_sides:
            sides = 'one-sided'
        
        results = []
        import uuid
        
        # 处理每个文件
        for file in files:
            # 使用原始文件名检查扩展名
            if not allowed_file(file.filename):
                results.append({
                    'filename': file.filename,
                    'success': False,
                    'error': f'不支持的文件类型'
                })
                continue
            
            # 获取文件扩展名（使用原始文件名）
            file_ext = os.path.splitext(file.filename)[1].lower().lstrip('.')
            
            logger.info(f"原始文件名: {file.filename}")
            logger.info(f"文件扩展名: {file_ext}")
            
            # 生成安全的文件名（使用UUID避免中文文件名问题）
            safe_filename = f"{uuid.uuid4().hex}.{file_ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
            file.save(filepath)
            
            logger.info(f"安全文件名: {safe_filename}")
            logger.info(f"文件已保存: {filepath}")
            
            # 如果不是PDF或TXT，需要转换
            converted_filepath = filepath
            if file_ext not in ['pdf', 'txt']:
                logger.info(f"文件格式转换: {file_ext} -> PDF")
                converted_filepath = file_converter.convert_to_pdf(filepath)
                
                if not converted_filepath:
                    print_history.add_record(file.filename, printer_name, copies, success=False, error=f'无法将 {file_ext} 格式转换为PDF', filepath=filepath)
                    results.append({
                        'filename': file.filename,
                        'success': False,
                        'error': f'无法将 {file_ext} 格式转换为PDF'
                    })
                    continue
                
                logger.info(f"转换完成: {converted_filepath}")

            # 发送到打印机
            if printer_name:
                result = printer_manager.print_file(converted_filepath, printer_name, copies, sides, page_range)
            else:
                # 使用默认打印机
                result = printer_manager.print_file(converted_filepath, copies=copies, sides=sides, page_range=page_range)

            # 添加到打印历史
            if result['success']:
                print_history.add_record(file.filename, printer_name, copies, sides=sides, success=True, filepath=converted_filepath)
            else:
                print_history.add_record(file.filename, printer_name, copies, sides=sides, success=False, error=result.get('error'), filepath=converted_filepath)
            
            results.append({
                'filename': file.filename,
                'success': result['success'],
                'printer': result.get('printer', '默认打印机'),
                'copies': copies,
                'error': result.get('error') if not result['success'] else None
            })

        # 返回所有文件的处理结果
        success_count = sum(1 for r in results if r['success'])
        return jsonify({
            'success': success_count > 0,
            'message': f'已处理 {len(results)} 个文件，成功 {success_count} 个',
            'results': results
        })

    except Exception as e:
        logger.error(f"上传文件时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """获取打印历史"""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = print_history.get_history(limit)
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        logger.error(f"获取打印历史失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """清空打印历史"""
    try:
        print_history.clear_history()
        return jsonify({
            'success': True,
            'message': '打印历史已清空'
        })
    except Exception as e:
        logger.error(f"清空打印历史失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/history/reprint', methods=['POST'])
def reprint_from_history():
    """从历史记录重新打印文件"""
    try:
        data = request.get_json()
        record_id = int(data.get('id'))
        
        if not record_id:
            return jsonify({
                'success': False,
                'error': '缺少记录ID'
            }), 400
        
        # 获取历史记录
        history = print_history.get_history()
        
        # 查找记录
        record = None
        for r in history:
            if r['id'] == record_id:
                record = r
                break
        
        if not record:
            return jsonify({
                'success': False,
                'error': '未找到该记录'
            }), 404
        
        if not record['success']:
            return jsonify({
                'success': False,
                'error': '该打印任务失败，无法重新打印'
            }), 400
        
        # 重新打印文件
        filename = record.get('filename')
        printer = record.get('printer', '')
        copies = record.get('copies', 1)
        sides = record.get('sides', 'one-sided')
        
        # 获取文件扩展名（使用原始文件名）
        file_ext = os.path.splitext(filename)[1].lower().lstrip('.')
        
        # 优先使用已转换的PDF文件
        original_filepath = record.get('filepath')
        if original_filepath and os.path.exists(original_filepath):
            converted_filepath = original_filepath
            logger.info(f"使用已转换的文件: {converted_filepath}")
        elif file_ext not in ['pdf', 'txt']:
            # 需要转换
            logger.info(f"文件格式转换: {file_ext} -> PDF")
            converted_filepath = file_converter.convert_to_pdf(original_filepath)
            
            if not converted_filepath:
                return jsonify({
                    'success': False,
                    'error': f'无法将 {file_ext} 格式转换为PDF'
                }), 400
        else:
            converted_filepath = original_filepath
            converted_filepath = record.get('filepath')
        
        # 发送到打印机
        if printer:
            result = printer_manager.print_file(converted_filepath, printer, copies, sides, '')
        else:
            result = printer_manager.print_file(converted_filepath, copies=copies, sides=sides, page_range='')
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f'文件 "{filename}" 已重新发送到打印机 ({copies} 份)',
                'printer': result.get('printer', '默认打印机'),
                'copies': copies
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '打印失败')
            }), 500
            
    except Exception as e:
        logger.error(f"重新打印失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/preview', methods=['POST'])
def preview_file():
    """预览文件（将Office文档转换为PDF）"""
    try:
        import uuid
        
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '未选择文件'
            }), 400

        # 检查文件扩展名
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': '不支持的文件类型'
            }), 400

        # 获取文件扩展名
        file_ext = os.path.splitext(file.filename)[1].lower().lstrip('.')
        
        logger.info(f"预览文件: {file.filename}, 扩展名: {file_ext}")

        # 生成安全的文件名
        safe_filename = f"{uuid.uuid4().hex}.{file_ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(filepath)
        
        logger.info(f"文件已保存: {filepath}")

        # 如果是PDF或TXT，直接返回
        if file_ext in ['pdf', 'txt', 'jpg', 'jpeg', 'png', 'gif']:
            return jsonify({
                'success': True,
                'type': file_ext,
                'filename': safe_filename,
                'original_filename': file.filename
            })

        # 如果是Office文档，转换为PDF
        if file_ext in ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']:
            logger.info(f"转换Office文档: {file_ext} -> PDF")
            converted_filepath = file_converter.convert_to_pdf(filepath)
            
            if not converted_filepath:
                return jsonify({
                    'success': False,
                    'error': f'无法将 {file_ext} 格式转换为PDF'
                }), 400

            # 转换后的文件名
            converted_filename = os.path.basename(converted_filepath)
            logger.info(f"转换完成: {converted_filename}")

            return jsonify({
                'success': True,
                'type': 'html' if converted_filepath.endswith('.html') else 'pdf',
                'filename': converted_filename,
                'original_filename': file.filename
            })

        return jsonify({
            'success': False,
            'error': '此文件格式不支持预览'
        }), 400

    except Exception as e:
        logger.error(f"预览文件失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    """提供上传文件的访问"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        logger.error(f"访问文件失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '文件不存在'
        }), 404


@app.route('/api/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    try:
        printers = printer_manager.list_printers()
        return jsonify({
            'success': True,
            'status': {
                'cups_running': printer_manager.check_cups_status(),
                'printers_count': len(printers),
                'printers': printers
            }
        })
    except Exception as e:
        logger.error(f"获取状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """处理文件过大错误"""
    return jsonify({
        'success': False,
        'error': '文件过大，请检查服务器配置'
    }), 413


@app.errorhandler(500)
def internal_server_error(error):
    """处理服务器错误"""
    logger.error(f"服务器错误: {str(error)}")
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500


if __name__ == '__main__':
    logger.info("启动Flask应用...")
    app.run(host='0.0.0.0', port=5000, debug=False)
