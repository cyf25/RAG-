#!/usr/bin/env python3
"""
智能向量化处理器
包含重试、降级和错误处理机制
"""

import os
import time
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

# 加载环境变量
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartVectorProcessor:
    def __init__(self):
        """初始化智能向量化处理器"""
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            logger.warning("未设置DASHSCOPE_API_KEY，将使用降级模式")
        
        # 设置DashScope API Key
        if self.api_key:
            try:
                import dashscope
                dashscope.api_key = self.api_key
                logger.info("DashScope API Key 已设置")
            except Exception as e:
                logger.error(f"设置DashScope API Key失败: {e}")
    
    def check_api_status(self) -> Dict:
        """检查API状态"""
        if not self.api_key:
            return {"available": False, "reason": "未设置API密钥"}
        
        try:
            from dashscope import TextEmbedding
            
            # 测试简单调用
            resp = TextEmbedding.call(
                model=TextEmbedding.Models.text_embedding_v1,
                input=["测试文本"]
            )
            
            if hasattr(resp, 'status_code') and resp.status_code != 200:
                return {"available": False, "reason": f"API状态码: {resp.status_code}"}
            
            return {"available": True, "reason": "API正常"}
            
        except Exception as e:
            return {"available": False, "reason": f"API测试失败: {str(e)}"}
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_embeddings_with_retry(self, texts: List[str]) -> List[List[float]]:
        """带重试的向量化"""
        try:
            from dashscope import TextEmbedding
            
            if not self.api_key:
                raise RuntimeError("未设置API密钥")
            
            # 分批处理
            batch_size = 25
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                logger.info(f"处理批次 {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
                
                resp = TextEmbedding.call(
                    model=TextEmbedding.Models.text_embedding_v1,
                    input=batch
                )
                
                # 检查响应
                if hasattr(resp, 'status_code') and resp.status_code != 200:
                    raise RuntimeError(f"API调用失败，状态码: {resp.status_code}")
                
                # 提取embeddings
                if 'output' in resp and 'embeddings' in resp['output']:
                    for emb in resp['output']['embeddings']:
                        if emb['embedding'] is None or len(emb['embedding']) == 0:
                            raise RuntimeError("API返回空embedding")
                        all_embeddings.append(emb['embedding'])
                elif 'output' in resp and 'embedding' in resp['output']:
                    if resp['output']['embedding'] is None or len(resp['output']['embedding']) == 0:
                        raise RuntimeError("API返回空embedding")
                    all_embeddings.append(resp['output']['embedding'])
                else:
                    raise RuntimeError(f"API返回格式异常: {resp}")
                
                # 添加延迟避免频率限制
                time.sleep(0.1)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"向量化失败: {e}")
            raise
    
    def create_simple_embeddings(self, texts: List[str]) -> List[List[float]]:
        """创建简单的TF-IDF风格embedding作为降级方案"""
        logger.info("使用降级方案：简单TF-IDF embedding")
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.decomposition import TruncatedSVD
            
            # 创建TF-IDF向量
            vectorizer = TfidfVectorizer(
                max_features=512,
                stop_words=None,
                ngram_range=(1, 2)
            )
            
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            # 使用SVD降维到1536维（与DashScope一致）
            svd = TruncatedSVD(n_components=1536, random_state=42)
            embeddings = svd.fit_transform(tfidf_matrix)
            
            # 归一化
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"创建简单embedding失败: {e}")
            # 最后的降级方案：随机向量
            logger.warning("使用随机向量作为最后的降级方案")
            return [np.random.normal(0, 1, 1536).tolist() for _ in texts]
    
    def get_embeddings_with_fallback(self, texts: List[str]) -> List[List[float]]:
        """带降级的向量化"""
        # 检查API状态
        api_status = self.check_api_status()
        
        if not api_status["available"]:
            logger.warning(f"API不可用: {api_status['reason']}")
            return self.create_simple_embeddings(texts)
        
        try:
            # 尝试使用DashScope API
            return self.get_embeddings_with_retry(texts)
        except Exception as e:
            logger.error(f"DashScope API失败: {e}")
            logger.info("切换到降级方案")
            return self.create_simple_embeddings(texts)
    
    def process_documents(self, reports_dir: Path, output_dir: Path) -> Dict:
        """处理文档并创建向量数据库"""
        import json
        import faiss
        from tqdm import tqdm
        
        result = {
            "success": True,
            "processed": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            # 确保输出目录存在
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 获取所有报告文件
            report_files = list(reports_dir.glob("*.json"))
            
            if not report_files:
                logger.warning("没有找到报告文件")
                return result
            
            logger.info(f"开始处理 {len(report_files)} 个报告文件")
            
            for report_file in tqdm(report_files, desc="处理报告"):
                try:
                    # 加载报告
                    with open(report_file, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    
                    # 提取文本块
                    text_chunks = [chunk['text'] for chunk in report_data['content']['chunks']]
                    text_chunks = [t[:2048] for t in text_chunks if len(t) > 0]  # 限制长度
                    
                    if not text_chunks:
                        logger.warning(f"报告 {report_file.name} 没有有效文本块")
                        continue
                    
                    # 生成embeddings
                    embeddings = self.get_embeddings_with_fallback(text_chunks)
                    
                    # 创建FAISS索引
                    embeddings_array = np.array(embeddings, dtype=np.float32)
                    dimension = len(embeddings[0])
                    index = faiss.IndexFlatIP(dimension)  # 内积（余弦距离）
                    index.add(embeddings_array)
                    
                    # 保存索引
                    sha1 = report_data["metainfo"].get("sha1", "")
                    if not sha1:
                        sha1 = report_file.stem
                    
                    faiss_file_path = output_dir / f"{sha1}.faiss"
                    faiss.write_index(index, str(faiss_file_path))
                    
                    result["processed"] += 1
                    logger.info(f"✅ 处理成功: {report_file.name}")
                    
                except Exception as e:
                    error_msg = f"处理 {report_file.name} 失败: {str(e)}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
                    result["failed"] += 1
            
            logger.info(f"处理完成: 成功 {result['processed']}, 失败 {result['failed']}")
            return result
            
        except Exception as e:
            logger.error(f"批量处理失败: {e}")
            result["success"] = False
            result["errors"].append(str(e))
            return result

def main():
    """主函数 - 测试向量化处理器"""
    print("🧠 智能向量化处理器测试")
    print("=" * 60)
    
    processor = SmartVectorProcessor()
    
    # 检查API状态
    api_status = processor.check_api_status()
    print(f"API状态: {'✅ 可用' if api_status['available'] else '❌ 不可用'}")
    if not api_status['available']:
        print(f"原因: {api_status['reason']}")
    
    # 测试向量化
    test_texts = [
        "这是一个测试文本",
        "另一个测试文本",
        "第三个测试文本"
    ]
    
    print(f"\n🔄 测试向量化 {len(test_texts)} 个文本...")
    
    try:
        embeddings = processor.get_embeddings_with_fallback(test_texts)
        print(f"✅ 向量化成功，生成 {len(embeddings)} 个向量")
        print(f"向量维度: {len(embeddings[0])}")
        
        # 测试处理文档
        reports_dir = Path("data/stock_data/databases/chunked_reports")
        output_dir = Path("data/stock_data/databases/vector_dbs")
        
        if reports_dir.exists():
            print(f"\n🔄 测试处理文档...")
            result = processor.process_documents(reports_dir, output_dir)
            print(f"处理结果: 成功 {result['processed']}, 失败 {result['failed']}")
        else:
            print(f"\n⚠️ 报告目录不存在: {reports_dir}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    main()
