#!/usr/bin/env python3
"""
本地PDF解析工具
使用PyPDF2解析本地PDF文件，不依赖mineru服务
"""

import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
import PyPDF2

# 加载环境变量
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_pdf_with_pypdf2(pdf_path: Path) -> dict:
    """
    使用PyPDF2解析PDF文件
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # 提取文本内容
            text_content = ""
            pages_info = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    text_content += f"\n\n--- 第 {page_num + 1} 页 ---\n\n"
                    text_content += page_text
                    
                    pages_info.append({
                        "page_number": page_num + 1,
                        "text_length": len(page_text),
                        "text": page_text
                    })
                    
                except Exception as e:
                    logger.warning(f"无法提取第{page_num + 1}页文本: {e}")
                    text_content += f"\n\n--- 第 {page_num + 1} 页 (提取失败) ---\n\n"
            
            return {
                "success": True,
                "total_pages": len(pdf_reader.pages),
                "total_text_length": len(text_content),
                "text_content": text_content,
                "pages_info": pages_info,
                "file_path": str(pdf_path),
                "file_size": pdf_path.stat().st_size
            }
            
    except Exception as e:
        logger.error(f"解析PDF文件失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "file_path": str(pdf_path)
        }

def save_markdown_file(content: str, output_path: Path, filename: str):
    """
    保存markdown文件
    """
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        markdown_file = output_path / f"{filename}.md"
        
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Markdown文件已保存: {markdown_file}")
        return True
        
    except Exception as e:
        logger.error(f"保存markdown文件失败: {e}")
        return False

def process_single_pdf(pdf_path: Path, output_dir: Path) -> bool:
    """
    处理单个PDF文件
    """
    logger.info(f"开始处理PDF: {pdf_path.name}")
    
    # 解析PDF
    result = parse_pdf_with_pypdf2(pdf_path)
    
    if not result["success"]:
        logger.error(f"PDF解析失败: {result['error']}")
        return False
    
    # 生成markdown内容
    filename = pdf_path.stem
    markdown_content = f"""# {filename}

## 文件信息
- 文件名: {pdf_path.name}
- 总页数: {result['total_pages']}
- 文本长度: {result['total_text_length']} 字符
- 文件大小: {result['file_size']} 字节

## 内容

{result['text_content']}
"""
    
    # 保存markdown文件
    success = save_markdown_file(markdown_content, output_dir, filename)
    
    if success:
        logger.info(f"✅ PDF处理成功: {filename}")
        return True
    else:
        logger.error(f"❌ PDF处理失败: {filename}")
        return False

def process_failed_pdfs():
    """
    处理所有失败的PDF文件
    """
    print("🔧 本地PDF解析工具")
    print("=" * 60)
    
    # 设置路径
    from pathlib import Path
    pdf_dir = Path("data/stock_data/pdf_reports")
    md_dir = Path("data/stock_data/debug_data/03_reports_markdown")
    
    if not pdf_dir.exists():
        print("❌ PDF目录不存在")
        return
    
    # 获取所有PDF文件
    pdf_files = set(f.stem for f in pdf_dir.glob("*.pdf"))
    
    # 获取已处理的markdown文件
    md_files = set(f.stem for f in md_dir.glob("*.md")) if md_dir.exists() else set()
    
    # 找出未处理的PDF文件
    failed_pdfs = pdf_files - md_files
    
    if not failed_pdfs:
        print("✅ 没有失败的PDF文件需要处理")
        return
    
    print(f"发现 {len(failed_pdfs)} 个未处理的PDF文件:")
    for pdf in failed_pdfs:
        print(f"  - {pdf}")
    
    print(f"\n🔄 开始使用本地解析器处理...")
    
    success_count = 0
    for pdf_name in failed_pdfs:
        pdf_path = pdf_dir / f"{pdf_name}.pdf"
        if process_single_pdf(pdf_path, md_dir):
            success_count += 1
        else:
            print(f"❌ 处理失败: {pdf_name}")
    
    print(f"\n🎯 处理完成:")
    print(f"  成功: {success_count}")
    print(f"  失败: {len(failed_pdfs) - success_count}")
    
    if success_count > 0:
        print(f"\n🔄 重新运行分块处理...")
        try:
            from src.pipeline import Pipeline, max_config
            from pathlib import Path
            
            root_path = Path("data/stock_data")
            pipeline = Pipeline(root_path, run_config=max_config)
            
            # 重新分块
            pipeline.chunk_reports()
            print("✅ 分块处理完成")
            
        except Exception as e:
            print(f"❌ 分块处理失败: {e}")

def main():
    """主函数"""
    print("🔧 本地PDF解析工具")
    print("=" * 60)
    
    # 检查当前状态
    from check_pdf_processing import check_processing_status
    check_processing_status()
    
    # 询问是否处理
    print("\n" + "=" * 60)
    response = input("是否要使用本地解析器处理失败的PDF文件? (y/n): ").strip().lower()
    
    if response in ['y', 'yes', '是']:
        process_failed_pdfs()
        
        # 重新检查状态
        print("\n" + "=" * 60)
        check_processing_status()
    else:
        print("取消处理")

if __name__ == "__main__":
    main()
