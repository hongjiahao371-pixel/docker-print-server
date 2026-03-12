#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印机管理工具
与CUPS交互，管理打印机列表和打印任务
"""

import subprocess
import logging
import json
import re

logger = logging.getLogger(__name__)


class PrinterManager:
    """打印机管理器"""
    
    def __init__(self):
        self.lp_command = '/usr/bin/lp'
        self.lpstat_command = '/usr/bin/lpstat'
    
    def check_cups_status(self):
        """检查CUPS服务状态"""
        try:
            # 方法1: 尝试使用lpstat命令测试CUPS是否响应
            result = subprocess.run(
                [self.lpstat_command, '-h', 'cups-server:631', '-r'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # lpstat -r 返回 "scheduler is running" 表示CUPS正在运行
            if 'scheduler is running' in result.stdout.lower():
                logger.info("CUPS状态: 运行中")
                return True
            
            # 方法2: 检查CUPS进程是否在运行
            result = subprocess.run(
                ['pgrep', '-f', 'cupsd'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info("CUPS状态: 运行中 (进程检测)")
                return True
            
            # 方法3: 检查CUPS socket文件是否存在
            import os
            if os.path.exists('/var/run/cups/cups.sock'):
                logger.info("CUPS状态: 运行中 (socket检测)")
                return True
            
            logger.warning("CUPS状态: 未运行")
            return False
            
        except Exception as e:
            logger.error(f"检查CUPS状态失败: {str(e)}")
            # 如果检测失败，尝试通过lpstat -p来判断
            try:
                result = subprocess.run(
                    [self.lpstat_command, '-h', 'cups-server:631', '-p'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # 如果lpstat -p能正常执行（即使没有打印机），说明CUPS在运行
                if result.returncode == 0 or 'no destinations' in result.stderr.lower():
                    logger.info("CUPS状态: 运行中 (lpstat测试)")
                    return True
            except:
                pass
            return False
    
    def list_printers(self):
        """
        获取可用打印机列表
        
        Returns:
            打印机信息列表
        """
        try:
            # 使用lpstat -p获取打印机列表
            result = subprocess.run(
                [self.lpstat_command, '-h', 'cups-server:631', '-p'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"获取打印机列表失败: {result.stderr}")
                return []
            
            printers = []
            lines = result.stdout.split('\n')
            
            for line in lines:
                if line.startswith('printer'):
                    # 解析打印机信息
                    # 格式: printer <name> is idle. enabled since <time>
                    # 或: printer <name> is printing xxx. enabled since <time>
                    match = re.search(r'printer\s+(\S+)', line)
                    if match:
                        printer_name = match.group(1)
                        status_match = re.search(r'is\s+(\w+)', line)
                        status = status_match.group(1) if status_match else 'unknown'
                        
                        printers.append({
                            'name': printer_name,
                            'status': status,
                            'enabled': 'enabled' in line
                        })
            
            logger.info(f"找到 {len(printers)} 台打印机")
            return printers
            
        except Exception as e:
            logger.error(f"获取打印机列表时出错: {str(e)}")
            return []
    
    def print_file(self, filepath, printer_name=None, copies=1, sides='one-sided', page_range=''):
        """
        打印文件
        
        Args:
            filepath: 要打印的文件路径
            printer_name: 打印机名称，如果为None则使用默认打印机
            copies: 打印份数，默认为1
            sides: 双面打印选项，默认为单面打印
            page_range: 页码范围，例如 "1,3-5,10"
            
        Returns:
            包含打印结果的字典
        """
        try:
            if not printer_name:
                # 获取默认打印机
                printers = self.list_printers()
                if printers and len(printers) > 0:
                    printer_name = printers[0]['name']
                else:
                    return {
                        'success': False,
                        'error': '没有可用的打印机'
                    }
            
            # 验证打印份数
            try:
                copies = int(copies)
                if copies < 1 or copies > 100:
                    return {
                        'success': False,
                        'error': '打印份数必须在1-100之间'
                    }
            except (ValueError, TypeError):
                copies = 1
            
            # 验证双面打印选项
            valid_sides = ['one-sided', 'two-sided-long-edge', 'two-sided-short-edge']
            if sides not in valid_sides:
                sides = 'one-sided'
            
            # 构建lp命令
            cmd = [self.lp_command, '-h', 'cups-server:631']
            cmd.extend(['-d', printer_name])  # 指定打印机
            cmd.extend(['-n', str(copies)])  # 指定打印份数
            cmd.extend(['-o', f'sides={sides}'])  # 指定双面打印选项
            
            # 添加页码范围
            if page_range:
                # 验证页码范围格式
                import re
                if re.match(r'^[\d,\-\s]+$', page_range):
                    cmd.extend(['-o', f'page-ranges={page_range}'])
            
            cmd.append(filepath)
            
            logger.info(f"发送打印任务: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # 解析任务ID
                # 输出格式: request id is <name>-<id> (1 file(s))
                match = re.search(r'request id is (\S+)', result.stdout)
                job_id = match.group(1) if match else 'unknown'
                
                logger.info(f"打印任务已提交: {job_id}")
                return {
                    'success': True,
                    'job_id': job_id,
                    'printer': printer_name,
                    'copies': copies,
                    'sides': sides,
                    'message': f'文件已发送到打印机 {printer_name} ({copies} 份)'
                }
            else:
                logger.error(f"打印失败: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr
                }
                
        except Exception as e:
            logger.error(f"打印文件时出错: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_printer_status(self, printer_name):
        """
        获取指定打印机的状态
        
        Args:
            printer_name: 打印机名称
            
        Returns:
            打印机状态信息
        """
        try:
            result = subprocess.run(
                [self.lpstat_command, '-p', printer_name],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': '打印机不存在或无法访问'
                }
            
            # 解析状态信息
            status_line = result.stdout.strip()
            
            return {
                'success': True,
                'printer': printer_name,
                'status': status_line
            }
            
        except Exception as e:
            logger.error(f"获取打印机状态时出错: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cancel_job(self, job_id):
        """
        取消打印任务
        
        Args:
            job_id: 任务ID
            
        Returns:
            操作结果
        """
        try:
            result = subprocess.run(
                ['/usr/bin/cancel', job_id],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"打印任务已取消: {job_id}")
                return {
                    'success': True,
                    'message': f'任务 {job_id} 已取消'
                }
            else:
                logger.error(f"取消任务失败: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr
                }
                
        except Exception as e:
            logger.error(f"取消打印任务时出错: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
