#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印历史管理器
存储和管理打印历史记录
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PrintHistory:
    """打印历史管理类"""
    
    def __init__(self, history_file='/app/data/print_history.json'):
        """初始化打印历史管理器
        
        Args:
            history_file: 历史记录文件路径
        """
        self.history_file = history_file
        self.history_dir = os.path.dirname(history_file)
        
        # 确保目录存在
        os.makedirs(self.history_dir, exist_ok=True)
        
        # 加载历史记录
        self.history = self._load_history()
    
    def _load_history(self):
        """从文件加载历史记录"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"加载打印历史失败: {str(e)}")
            return []
    
    def _save_history(self):
        """保存历史记录到文件"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存打印历史失败: {str(e)}")
    
    def add_record(self, filename, printer_name, copies, sides='one-sided', success=True, error=None, filepath=None):
        """添加打印记录
        
        Args:
            filename: 文件名
            printer_name: 打印机名称
            copies: 打印份数
            sides: 双面打印选项
            success: 是否成功
            error: 错误信息（如果有）
            filepath: 文件路径（用于重新打印）
        """
        record = {
            'id': len(self.history) + 1,
            'filename': filename,
            'printer': printer_name or '默认打印机',
            'copies': copies,
            'sides': sides,
            'success': success,
            'error': error,
            'filepath': filepath,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.history.insert(0, record)  # 新记录在最前面
        
        # 只保留最近100条记录
        if len(self.history) > 100:
            self.history = self.history[:100]
        
        self._save_history()
        logger.info(f"添加打印记录: {filename}")
        
        return record
    
    def get_history(self, limit=None):
        """获取打印历史
        
        Args:
            limit: 返回的最大记录数
            
        Returns:
            历史记录列表
        """
        if limit:
            return self.history[:limit]
        return self.history
    
    def clear_history(self):
        """清空打印历史"""
        self.history = []
        self._save_history()
        logger.info("清空打印历史")
