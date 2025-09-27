#!/usr/bin/env python3
"""
完整的上传处理脚本
包括PDF解析、分块、向量化的完整流程
"""

import os
import shutil
import hashlib
import pandas as pd
import json
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompleteUploadProcessor:
    def __init__(self, data_root: str = "data/stock_data"):
        self.data_root = Path(data_root)
        self.pdf_reports_dir = self.data_root / "pdf_reports"
        self.subset_path = self.data_root / "subset.csv"
        self.databases_path = self.data_root / "databases"
        self.vector_db_dir = self.databases_path / "vector_dbs"
        self.documents_dir = self.databases_path / "chunked_reports"
        self.debug_data_path = self.data_root / "debug_data"
        self.reports_markdown_path = self.debug_data_path / "03_reports_markdown"
        
        # 确保目录存在
        self.pdf_reports_dir.mkdir(parents=True, exist_ok=True)
        self.databases_path.mkdir(parents=True, exist_ok=True)
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.debug_data_path.mkdir(parents=True, exist_ok=True)
        self.reports_markdown_path.mkdir(parents=True, exist_ok=True)
    
    def calculate_sha1(self, file_path: Path) -> str:
        """计算文件的SHA1哈希值"""
        sha1_hash = hashlib.sha1()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha1_hash.update(chunk)
        return sha1_hash.hexdigest()
    
    def get_next_stock_id(self) -> str:
        """获取下一个可用的stock_id"""
        if not self.subset_path.exists():
            return "stock_10001"
        
        try:
            df = pd.read_csv(self.subset_path)
            existing_ids = []
            for _, row in df.iterrows():
                if isinstance(row['sha1'], str) and row['sha1'].startswith('stock_'):
                    try:
                        existing_ids.append(int(row['sha1'].replace('stock_', '')))
                    except ValueError:
                        continue
            
            if not existing_ids:
                return "stock_10001"
            
            next_id = max(existing_ids) + 1
            return f"stock_{next_id:05d}"
        except Exception as e:
            logger.error(f"获取下一个ID失败: {e}")
            return "stock_10001"
    
    def validate_file(self, file_path: Path) -> Tuple[bool, str]:
        """验证上传的文件"""
        if not file_path.exists():
            return False, "文件不存在"
        
        if file_path.suffix.lower() != '.pdf':
            return False, "只支持PDF格式文件"
        
        file_size = file_path.stat().st_size
        if file_size > 100 * 1024 * 1024:  # 100MB
            return False, "文件大小超过100MB限制"
        
        return True, "文件验证通过"
    
    def copy_file_to_reports_dir(self, source_path: Path, filename: str) -> Path:
        """复制文件到reports目录"""
        target_path = self.pdf_reports_dir / filename
        
        # 如果文件已存在，添加时间戳
        if target_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = filename.rsplit('.', 1)
            filename = f"{name}_{timestamp}.{ext}"
            target_path = self.pdf_reports_dir / filename
        
        shutil.copy2(source_path, target_path)
        return target_path
    
    def update_subset_csv(self, stock_id: str, filename: str, company_name: str) -> bool:
        """更新subset.csv文件"""
        new_row = {
            'sha1': stock_id,
            'file_name': filename,
            'company_name': company_name
        }
        
        try:
            if self.subset_path.exists():
                df = pd.read_csv(self.subset_path)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                df = pd.DataFrame([new_row])
            
            df.to_csv(self.subset_path, index=False)
            return True
        except Exception as e:
            logger.error(f"更新subset.csv失败: {e}")
            return False
    
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
    
    def parse_pdf_to_markdown(self, pdf_filename: str) -> Dict:
        """将PDF解析为markdown格式"""
        logger.info(f"开始解析PDF: {pdf_filename}")
        
        try:
            # 使用本地PDF解析器
            from local_pdf_parser import process_single_pdf
            from pathlib import Path
            
            pdf_path = Path(self.data_root) / "pdf_reports" / pdf_filename
            md_dir = Path(self.data_root) / "debug_data" / "03_reports_markdown"
            
            if process_single_pdf(pdf_path, md_dir):
                return {"success": True, "message": "PDF解析成功"}
            else:
                return {"success": False, "message": "PDF解析失败"}
                
        except Exception as e:
            logger.error(f"PDF解析异常: {e}")
            return {"success": False, "message": f"PDF解析异常: {str(e)}"}
    
    def chunk_reports(self) -> Dict:
        """分块处理报告"""
        logger.info("开始分块处理报告")
        
        command = f"python -c \"from src.pipeline import Pipeline; from src.pipeline import max_config; from pathlib import Path; p = Pipeline(Path('{self.data_root}'), run_config=max_config); p.chunk_reports()\""
        
        return self.run_command(command, "分块处理报告")
    
    def create_vector_dbs(self) -> Dict:
        """创建向量数据库"""
        logger.info("开始创建向量数据库")
        
        try:
            from smart_vector_processor import SmartVectorProcessor
            from pathlib import Path
            
            processor = SmartVectorProcessor()
            reports_dir = Path(self.data_root) / "databases" / "chunked_reports"
            output_dir = Path(self.data_root) / "databases" / "vector_dbs"
            
            result = processor.process_documents(reports_dir, output_dir)
            
            if result["success"] and result["processed"] > 0:
                return {"success": True, "message": f"向量数据库创建成功，处理了 {result['processed']} 个文件"}
            else:
                return {"success": False, "message": f"向量数据库创建失败: {result['errors']}"}
                
        except Exception as e:
            logger.error(f"向量数据库创建异常: {e}")
            return {"success": False, "message": f"向量数据库创建异常: {str(e)}"}
    
    def process_uploaded_file(self, file_path: Path, company_name: str, filename: str = None) -> Dict:
        """完整处理上传的文件"""
        result = {
            "success": False,
            "message": "",
            "stock_id": "",
            "filename": "",
            "file_path": "",
            "steps": []
        }
        
        try:
            # 步骤1: 验证文件
            is_valid, message = self.validate_file(file_path)
            if not is_valid:
                result["message"] = message
                return result
            
            result["steps"].append("✅ 文件验证通过")
            
            # 步骤2: 生成文件名
            if filename is None:
                filename = file_path.name
            
            # 步骤3: 复制文件到reports目录
            target_path = self.copy_file_to_reports_dir(file_path, filename)
            result["file_path"] = str(target_path)
            result["filename"] = target_path.name
            result["steps"].append("✅ 文件复制完成")
            
            # 步骤4: 计算SHA1
            sha1_value = self.calculate_sha1(target_path)
            logger.info(f"文件SHA1: {sha1_value}")
            
            # 步骤5: 获取stock_id
            stock_id = self.get_next_stock_id()
            result["stock_id"] = stock_id
            result["steps"].append("✅ 分配文件ID")
            
            # 步骤6: 更新subset.csv
            if not self.update_subset_csv(stock_id, target_path.name, company_name):
                result["message"] = "更新配置文件失败"
                return result
            result["steps"].append("✅ 更新配置文件")
            
            # 步骤7: 解析PDF为markdown
            parse_result = self.parse_pdf_to_markdown(target_path.name)
            if parse_result["success"]:
                result["steps"].append("✅ PDF解析完成")
                
                # 步骤8: 分块处理
                chunk_result = self.chunk_reports()
                if chunk_result["success"]:
                    result["steps"].append("✅ 文档分块完成")
                    
                    # 步骤9: 创建向量数据库
                    vector_result = self.create_vector_dbs()
                    if vector_result["success"]:
                        result["steps"].append("✅ 向量数据库创建完成")
                    else:
                        result["steps"].append(f"⚠️ 向量数据库创建失败: {vector_result['message']}")
                        result["steps"].append("ℹ️ 文件已上传，但向量化失败，可能影响问答功能")
                else:
                    result["steps"].append(f"⚠️ 文档分块失败: {chunk_result['message']}")
                    result["steps"].append("ℹ️ 文件已上传，但分块失败，可能影响问答功能")
            else:
                result["steps"].append(f"⚠️ PDF解析失败: {parse_result['message']}")
                result["steps"].append("ℹ️ 文件已上传，但PDF解析失败，请检查文件格式")
            
            result["success"] = True
            result["message"] = "文件上传完成"
            
            logger.info(f"文件上传成功: {filename} -> {stock_id}")
            
        except Exception as e:
            logger.error(f"处理上传文件失败: {e}")
            result["message"] = f"处理文件失败: {str(e)}"
        
        return result
    
    def get_upload_status(self) -> Dict:
        """获取上传状态信息"""
        try:
            if self.subset_path.exists():
                df = pd.read_csv(self.subset_path)
                total_files = len(df)
                companies = df['company_name'].unique().tolist()
            else:
                total_files = 0
                companies = []
            
            return {
                "total_files": total_files,
                "companies": companies,
                "pdf_dir": str(self.pdf_reports_dir),
                "vector_db_dir": str(self.vector_db_dir),
                "documents_dir": str(self.documents_dir)
            }
        except Exception as e:
            logger.error(f"获取上传状态失败: {e}")
            return {
                "total_files": 0,
                "companies": [],
                "error": str(e)
            }
    
    def list_uploaded_files(self) -> List[Dict]:
        """列出已上传的文件"""
        try:
            if not self.subset_path.exists():
                return []
            
            df = pd.read_csv(self.subset_path)
            files = []
            
            for _, row in df.iterrows():
                # 检查各种文件的存在状态
                pdf_file = self.pdf_reports_dir / row['file_name']
                md_file = self.reports_markdown_path / f"{Path(row['file_name']).stem}.md"
                chunk_file = self.documents_dir / f"{Path(row['file_name']).stem}.json"
                vector_file = self.vector_db_dir / f"{row['sha1']}.faiss"
                
                file_info = {
                    "stock_id": row['sha1'],
                    "filename": row['file_name'],
                    "company_name": row['company_name'],
                    "file_path": str(pdf_file),
                    "exists": pdf_file.exists(),
                    "pdf_exists": pdf_file.exists(),
                    "markdown_exists": md_file.exists(),
                    "chunk_exists": chunk_file.exists(),
                    "vector_exists": vector_file.exists(),
                    "processing_status": self._get_processing_status(pdf_file, md_file, chunk_file, vector_file)
                }
                files.append(file_info)
            
            return files
        except Exception as e:
            logger.error(f"列出上传文件失败: {e}")
            return []
    
    def _get_processing_status(self, pdf_file: Path, md_file: Path, chunk_file: Path, vector_file: Path) -> str:
        """获取文件处理状态"""
        if not pdf_file.exists():
            return "文件缺失"
        elif not md_file.exists():
            return "PDF未解析"
        elif not chunk_file.exists():
            return "未分块"
        elif not vector_file.exists():
            return "未向量化"
        else:
            return "处理完成"
    
    def delete_file(self, stock_id: str) -> Dict:
        """删除文件及其相关数据"""
        try:
            # 从subset.csv中获取文件信息
            if not self.subset_path.exists():
                return {"success": False, "message": "配置文件不存在"}
            
            df = pd.read_csv(self.subset_path)
            file_row = df[df['sha1'] == stock_id]
            
            if file_row.empty:
                return {"success": False, "message": "文件不存在"}
            
            filename = file_row.iloc[0]['file_name']
            file_stem = Path(filename).stem
            
            # 删除相关文件
            files_to_delete = [
                self.pdf_reports_dir / filename,  # PDF文件
                self.reports_markdown_path / f"{file_stem}.md",  # Markdown文件
                self.documents_dir / f"{file_stem}.json",  # 分块文件
                self.vector_db_dir / f"{stock_id}.faiss"  # 向量文件
            ]
            
            deleted_files = []
            for file_path in files_to_delete:
                if file_path.exists():
                    file_path.unlink()
                    deleted_files.append(file_path.name)
                    logger.info(f"删除文件: {file_path}")
            
            # 从subset.csv中删除记录
            df = df[df['sha1'] != stock_id]
            df.to_csv(self.subset_path, index=False)
            
            return {
                "success": True,
                "message": f"文件删除成功，删除了 {len(deleted_files)} 个文件",
                "deleted_files": deleted_files
            }
            
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return {"success": False, "message": f"删除文件失败: {str(e)}"}
    
    def reprocess_file(self, stock_id: str) -> Dict:
        """重新处理文件"""
        try:
            # 从subset.csv中获取文件信息
            if not self.subset_path.exists():
                return {"success": False, "message": "配置文件不存在"}
            
            df = pd.read_csv(self.subset_path)
            file_row = df[df['sha1'] == stock_id]
            
            if file_row.empty:
                return {"success": False, "message": "文件不存在"}
            
            filename = file_row.iloc[0]['file_name']
            file_stem = Path(filename).stem
            
            # 检查PDF文件是否存在
            pdf_file = self.pdf_reports_dir / filename
            if not pdf_file.exists():
                return {"success": False, "message": "PDF文件不存在"}
            
            result = {
                "success": False,
                "message": "",
                "steps": []
            }
            
            # 步骤1: 删除旧的markdown文件
            md_file = self.reports_markdown_path / f"{file_stem}.md"
            if md_file.exists():
                md_file.unlink()
                result["steps"].append("✅ 删除旧markdown文件")
            
            # 步骤2: 重新解析PDF
            parse_result = self.parse_pdf_to_markdown(filename)
            if parse_result["success"]:
                result["steps"].append("✅ PDF重新解析完成")
                
                # 步骤3: 重新分块
                chunk_result = self.chunk_reports()
                if chunk_result["success"]:
                    result["steps"].append("✅ 文档重新分块完成")
                    
                    # 步骤4: 重新创建向量数据库
                    vector_result = self.create_vector_dbs()
                    if vector_result["success"]:
                        result["steps"].append("✅ 向量数据库重新创建完成")
                        result["success"] = True
                        result["message"] = "文件重新处理完成"
                    else:
                        result["steps"].append(f"⚠️ 向量数据库创建失败: {vector_result['message']}")
                        result["message"] = "重新处理部分完成，向量化失败"
                else:
                    result["steps"].append(f"⚠️ 文档分块失败: {chunk_result['message']}")
                    result["message"] = "重新处理部分完成，分块失败"
            else:
                result["steps"].append(f"⚠️ PDF解析失败: {parse_result['message']}")
                result["message"] = "重新处理失败，PDF解析失败"
            
            return result
            
        except Exception as e:
            logger.error(f"重新处理文件失败: {e}")
            return {"success": False, "message": f"重新处理文件失败: {str(e)}"}

# 全局实例
complete_processor = CompleteUploadProcessor()

def upload_and_process_file(file_path: str, company_name: str, filename: str = None) -> Dict:
    """上传并处理文件的便捷函数"""
    return complete_processor.process_uploaded_file(Path(file_path), company_name, filename)

def get_upload_status() -> Dict:
    """获取上传状态的便捷函数"""
    return complete_processor.get_upload_status()

def list_files() -> List[Dict]:
    """列出文件的便捷函数"""
    return complete_processor.list_uploaded_files()

if __name__ == "__main__":
    # 测试代码
    print("完整上传处理器测试")
    print("=" * 50)
    
    # 获取状态
    status = get_upload_status()
    print(f"当前状态: {status}")
    
    # 列出文件
    files = list_files()
    print(f"已上传文件数量: {len(files)}")
    
    for file_info in files:
        print(f"- {file_info['stock_id']}: {file_info['filename']} ({file_info['company_name']})")
