#!/usr/bin/env python3
"""
PDF文件验证工具
检查PDF文件是否有效，是否可以正常解析
"""

import os
import PyPDF2
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_pdf_file(file_path: str) -> dict:
    """验证PDF文件是否有效"""
    result = {
        "valid": False,
        "message": "",
        "pages": 0,
        "size_mb": 0,
        "text_length": 0,
        "details": {}
    }
    
    try:
        file_path = Path(file_path)
        
        # 检查文件是否存在
        if not file_path.exists():
            result["message"] = "文件不存在"
            return result
        
        # 检查文件扩展名
        if file_path.suffix.lower() != '.pdf':
            result["message"] = "文件不是PDF格式"
            return result
        
        # 获取文件大小
        file_size = file_path.stat().st_size
        result["size_mb"] = file_size / (1024 * 1024)
        
        # 检查文件大小
        if file_size == 0:
            result["message"] = "文件为空"
            return result
        
        if file_size > 100 * 1024 * 1024:  # 100MB
            result["message"] = "文件过大（超过100MB）"
            return result
        
        # 尝试打开PDF文件
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                result["pages"] = len(pdf_reader.pages)
                
                # 检查页数
                if result["pages"] == 0:
                    result["message"] = "PDF文件没有页面"
                    return result
                
                # 提取文本
                text_content = ""
                for page_num in range(min(3, result["pages"])):  # 只检查前3页
                    try:
                        page = pdf_reader.pages[page_num]
                        text_content += page.extract_text() or ""
                    except Exception as e:
                        logger.warning(f"无法提取第{page_num+1}页文本: {e}")
                
                result["text_length"] = len(text_content)
                
                # 检查是否有文本内容
                if result["text_length"] < 100:
                    result["message"] = "PDF文件文本内容过少，可能无法正常解析"
                    result["valid"] = True  # 仍然认为有效，但给出警告
                else:
                    result["valid"] = True
                    result["message"] = "PDF文件验证通过"
                
                # 添加详细信息
                result["details"] = {
                    "file_name": file_path.name,
                    "file_path": str(file_path),
                    "file_size_bytes": file_size,
                    "file_size_mb": result["size_mb"],
                    "total_pages": result["pages"],
                    "text_content_length": result["text_length"],
                    "sample_text": text_content[:200] + "..." if len(text_content) > 200 else text_content
                }
            
        except Exception as e:
            result["message"] = f"PDF文件损坏或无法读取: {str(e)}"
            return result
            
    except Exception as e:
        result["message"] = f"验证过程中出错: {str(e)}"
        return result
    
    return result

def print_validation_result(result: dict):
    """打印验证结果"""
    print("=" * 60)
    print("📄 PDF文件验证结果")
    print("=" * 60)
    
    if result["valid"]:
        print(f"✅ 状态: {result['message']}")
    else:
        print(f"❌ 状态: {result['message']}")
    
    print(f"📊 文件信息:")
    print(f"   - 文件名: {result['details'].get('file_name', 'N/A')}")
    print(f"   - 文件大小: {result['size_mb']:.2f} MB")
    print(f"   - 页面数量: {result['pages']} 页")
    print(f"   - 文本长度: {result['text_length']} 字符")
    
    if result["valid"] and result["text_length"] > 0:
        print(f"📝 文本预览:")
        sample_text = result["details"].get("sample_text", "")
        print(f"   {sample_text}")
    
    print("=" * 60)

if __name__ == "__main__":
    # 测试代码
    print("🔍 PDF文件验证工具")
    print("请输入PDF文件路径进行验证:")
    
    file_path = input("文件路径: ").strip()
    
    if file_path:
        result = validate_pdf_file(file_path)
        print_validation_result(result)
    else:
        print("❌ 未输入文件路径")
