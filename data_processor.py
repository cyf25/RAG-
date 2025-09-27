#!/usr/bin/env python3
"""
数据处理脚本
用于处理上传的文件：解析、分块、向量化
"""

import subprocess
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
import json

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self, data_root: str = "data/stock_data"):
        self.data_root = Path(data_root)
        self.pipeline_path = Path("src/pipeline.py")
        self.main_path = Path("main.py")
        
    def run_command(self, command: str, description: str) -> Dict:
        """运行命令并返回结果"""
        result = {
            "success": False,
            "message": "",
            "output": "",
            "error": ""
        }
        
        logger.info(f"🔄 {description}...")
        logger.info(f"执行命令: {command}")
        
        try:
            # 运行命令
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 实时输出
            output_lines = []
            error_lines = []
            
            while True:
                output = process.stdout.readline()
                error = process.stderr.readline()
                
                if output:
                    output_lines.append(output.strip())
                    logger.info(output.strip())
                
                if error:
                    error_lines.append(error.strip())
                    logger.error(error.strip())
                
                # 检查进程是否结束
                if process.poll() is not None:
                    break
            
            # 等待进程完成
            return_code = process.wait()
            
            if return_code == 0:
                result["success"] = True
                result["message"] = f"{description} 完成"
                result["output"] = "\n".join(output_lines)
            else:
                result["success"] = False
                result["message"] = f"{description} 失败"
                result["error"] = "\n".join(error_lines)
                
        except Exception as e:
            logger.error(f"执行命令失败: {e}")
            result["success"] = False
            result["message"] = f"执行命令失败: {str(e)}"
            result["error"] = str(e)
        
        return result
    
    def check_prerequisites(self) -> Dict:
        """检查前置条件"""
        result = {
            "success": False,
            "message": "",
            "missing": []
        }
        
        # 检查必要文件
        required_files = [
            self.pipeline_path,
            self.main_path,
            self.data_root
        ]
        
        missing_files = []
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(str(file_path))
        
        if missing_files:
            result["message"] = f"缺少必要文件: {', '.join(missing_files)}"
            result["missing"] = missing_files
            return result
        
        result["success"] = True
        result["message"] = "前置条件检查通过"
        return result
    
    def process_reports(self, config: str = "no_ser_tab") -> Dict:
        """处理报告（分块和向量化）"""
        logger.info("🚀 开始处理报告...")
        
        # 检查前置条件
        prereq_result = self.check_prerequisites()
        if not prereq_result["success"]:
            return prereq_result
        
        # 运行处理命令
        command = f"python main.py process-reports --config {config}"
        return self.run_command(command, "处理报告")
    
    def run_full_pipeline(self) -> Dict:
        """运行完整处理流程"""
        logger.info("🚀 开始运行完整处理流程...")
        
        # 检查前置条件
        prereq_result = self.check_prerequisites()
        if not prereq_result["success"]:
            return prereq_result
        
        # 运行完整流程
        command = "python src/pipeline.py"
        return self.run_command(command, "完整处理流程")
    
    def parse_pdfs(self, parallel: bool = True, max_workers: int = 4) -> Dict:
        """解析PDF文件"""
        logger.info("🚀 开始解析PDF文件...")
        
        # 检查前置条件
        prereq_result = self.check_prerequisites()
        if not prereq_result["success"]:
            return prereq_result
        
        # 构建命令
        parallel_flag = "--parallel" if parallel else "--sequential"
        command = f"python main.py parse-pdfs {parallel_flag} --max-workers {max_workers}"
        
        return self.run_command(command, "解析PDF文件")
    
    def serialize_tables(self, max_workers: int = 4) -> Dict:
        """序列化表格"""
        logger.info("🚀 开始序列化表格...")
        
        # 检查前置条件
        prereq_result = self.check_prerequisites()
        if not prereq_result["success"]:
            return prereq_result
        
        # 运行序列化命令
        command = f"python main.py serialize-tables --max-workers {max_workers}"
        return self.run_command(command, "序列化表格")
    
    def get_processing_status(self) -> Dict:
        """获取处理状态"""
        status = {
            "pdf_reports": 0,
            "chunked_reports": 0,
            "vector_dbs": 0,
            "companies": []
        }
        
        try:
            # 统计PDF文件
            pdf_dir = self.data_root / "pdf_reports"
            if pdf_dir.exists():
                status["pdf_reports"] = len(list(pdf_dir.glob("*.pdf")))
            
            # 统计分块文档
            chunked_dir = self.data_root / "databases" / "chunked_reports"
            if chunked_dir.exists():
                status["chunked_reports"] = len(list(chunked_dir.glob("*.json")))
            
            # 统计向量数据库
            vector_dir = self.data_root / "databases" / "vector_dbs"
            if vector_dir.exists():
                status["vector_dbs"] = len(list(vector_dir.glob("*.faiss")))
            
            # 获取公司列表
            subset_path = self.data_root / "subset.csv"
            if subset_path.exists():
                import pandas as pd
                df = pd.read_csv(subset_path)
                status["companies"] = df['company_name'].unique().tolist()
            
        except Exception as e:
            logger.error(f"获取处理状态失败: {e}")
            status["error"] = str(e)
        
        return status
    
    def process_new_files(self, force_reprocess: bool = False) -> Dict:
        """处理新文件（智能检测）"""
        logger.info("🚀 开始处理新文件...")
        
        # 获取状态
        status = self.get_processing_status()
        
        # 检查是否需要处理
        if not force_reprocess and status["pdf_reports"] == status["chunked_reports"]:
            return {
                "success": True,
                "message": "所有文件都已处理完成，无需重新处理",
                "status": status
            }
        
        # 运行处理
        result = self.process_reports()
        result["status"] = self.get_processing_status()
        
        return result

# 全局实例
data_processor = DataProcessor()

def process_reports(config: str = "no_ser_tab") -> Dict:
    """处理报告的便捷函数"""
    return data_processor.process_reports(config)

def run_full_pipeline() -> Dict:
    """运行完整流程的便捷函数"""
    return data_processor.run_full_pipeline()

def parse_pdfs(parallel: bool = True, max_workers: int = 4) -> Dict:
    """解析PDF的便捷函数"""
    return data_processor.parse_pdfs(parallel, max_workers)

def get_processing_status() -> Dict:
    """获取处理状态的便捷函数"""
    return data_processor.get_processing_status()

def process_new_files(force_reprocess: bool = False) -> Dict:
    """处理新文件的便捷函数"""
    return data_processor.process_new_files(force_reprocess)

if __name__ == "__main__":
    # 测试代码
    print("数据处理器测试")
    print("=" * 50)
    
    # 获取状态
    status = get_processing_status()
    print(f"当前处理状态: {status}")
    
    # 检查是否需要处理
    if status["pdf_reports"] > status["chunked_reports"]:
        print("发现新文件，开始处理...")
        result = process_new_files()
        print(f"处理结果: {result}")
    else:
        print("所有文件都已处理完成")
