#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

class FileConverter:
    def __init__(self):
        self.supported_formats = {
            'doc': self._convert_doc_to_pdf,
            'docx': self._convert_docx_to_pdf,
            'xls': self._convert_xls_to_pdf,
            'xlsx': self._convert_xlsx_to_pdf,
            'ppt': self._convert_ppt_to_pdf,
            'pptx': self._convert_pptx_to_pdf,
            'jpg': self._convert_image_to_pdf,
            'jpeg': self._convert_image_to_pdf,
            'png': self._convert_image_to_pdf,
            'gif': self._convert_image_to_pdf,
        }
    
    def convert_to_pdf(self, filepath):
        try:
            if not os.path.exists(filepath):
                logger.error(f"文件不存在: {filepath}")
                return None
            file_ext = Path(filepath).suffix.lower().lstrip('.')
            if file_ext == 'pdf':
                return filepath
            if file_ext == 'txt':
                return filepath
            if file_ext not in self.supported_formats:
                logger.warning(f"不支持的文件格式: {file_ext}")
                return None
            converter = self.supported_formats[file_ext]
            return converter(filepath)
        except Exception as e:
            logger.error(f"文件转换失败: {str(e)}")
            return None
    
    def _convert_doc_to_pdf(self, filepath):
        """使用LibreOffice将文档转换为PDF"""
        try:
            parts = filepath.rsplit('.', 1)
            if len(parts) < 2:
                return None
            
            # LibreOffice转换
            output_dir = os.path.dirname(filepath)
            cmd = [
                'libreoffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', output_dir,
                filepath
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            output_pdf = parts[0] + '.pdf'
            if result.returncode == 0 and os.path.exists(output_pdf):
                logger.info(f"转换成功: {output_pdf}")
                return output_pdf
            else:
                logger.error(f"LibreOffice转换失败: {result.stderr}")
                # 回退到pandoc
                return self._pandoc_fallback(filepath)
        except Exception as e:
            logger.error(f"转换出错: {str(e)}")
            return self._pandoc_fallback(filepath)
    
    def _convert_docx_to_pdf(self, filepath):
        return self._convert_doc_to_pdf(filepath)
    
    def _convert_xls_to_pdf(self, filepath):
        return self._convert_doc_to_pdf(filepath)
    
    def _convert_xlsx_to_pdf(self, filepath):
        return self._convert_doc_to_pdf(filepath)
    
    def _convert_ppt_to_pdf(self, filepath):
        return self._convert_doc_to_pdf(filepath)
    
    def _convert_pptx_to_pdf(self, filepath):
        return self._convert_doc_to_pdf(filepath)
    
    def _pandoc_fallback(self, filepath):
        """pandoc回退方案"""
        try:
            parts = filepath.rsplit('.', 1)
            if len(parts) < 2:
                return None
            
            ext = parts[1]
            html_file = parts[0] + '.html'
            
            # 先转HTML
            cmd = ['pandoc', filepath, '-o', html_file]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(html_file):
                logger.info(f"Pandoc转换HTML成功: {html_file}")
                return html_file
            else:
                logger.error(f"Pandoc转换失败: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"Pandoc回退失败: {str(e)}")
            return None
    
    def _convert_image_to_pdf(self, filepath):
        try:
            parts = filepath.rsplit('.', 1)
            if len(parts) < 2:
                return None
            output_pdf = parts[0] + '.pdf'
            cmd = ['convert', filepath, output_pdf]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_pdf):
                return output_pdf
            else:
                logger.error(f"图片转PDF失败: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"图片转换出错: {str(e)}")
            return None
    
    def get_supported_formats(self):
        return list(self.supported_formats.keys()) + ['pdf', 'txt']
