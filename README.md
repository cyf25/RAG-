# RAG企业知识库问答系统

🚀 **基于深度RAG技术的企业知识库智能问答系统**

这是一个功能完整的企业知识库问答系统，专门用于处理PDF年报等文档，支持智能问答功能。系统采用先进的RAG（检索增强生成）技术，结合向量检索、LLM重排序和结构化输出，为企业提供高效的知识问答服务。

## ✨ 核心特性

- 📄 **智能PDF解析**：使用Docling进行高质量PDF文档解析
- 🔍 **多模态检索**：支持向量检索和BM25检索
- 🧠 **LLM重排序**：使用大语言模型提升检索质量
- 💬 **智能问答**：基于Qwen-Turbo的智能问答系统
- 🌐 **Web界面**：基于Streamlit的友好用户界面
- 📊 **文件管理**：支持文件上传、删除、重新处理
- 🔧 **系统监控**：实时监控处理状态和系统健康度

## 🏗️ 技术架构

- **PDF解析**：Docling + PDF MinerU
- **文本分块**：智能文本分割算法
- **向量化**：DashScope API (text-embedding-v1)
- **向量存储**：FAISS向量数据库
- **检索系统**：向量检索 + BM25检索
- **重排序**：LLM重排序提升检索质量
- **问答引擎**：Qwen-Turbo + 结构化输出
- **Web界面**：Streamlit + 现代化UI设计

## 🚀 快速开始

### 环境要求

- Python 3.9+
- 8GB+ 内存（推荐16GB）
- GPU（可选，用于加速PDF解析）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/cyf25/RAG-.git
cd RAG-
```

2. **创建虚拟环境**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置API密钥**
```bash
# 将env文件重命名为.env
mv env .env
# 编辑.env文件，添加您的API密钥
```

### 配置说明

在`.env`文件中配置以下API密钥：
```env
# DashScope API密钥（必需）
DASHSCOPE_API_KEY=您的dashscope_api密钥

# OpenAI API密钥（可选）
OPENAI_API_KEY=您的openai_api密钥
```

## 📖 使用说明

### 方式一：Web界面（推荐）

启动Streamlit Web界面，提供友好的用户交互：

```bash
streamlit run app_streamlit.py
```

访问 `http://localhost:8501` 即可使用Web界面。

**功能特性：**
- 📝 **智能问答**：输入问题，获得结构化答案
- 📁 **文件管理**：上传、删除、重新处理PDF文件
- ⚙️ **系统状态**：监控处理状态和系统健康度

### 方式二：命令行工具

使用命令行工具进行批量处理：

```bash
# 查看帮助
python main.py --help

# 下载模型
python main.py download-models

# 解析PDF文件
python main.py parse-pdfs --parallel --max-workers 10

# 处理报告
python main.py process-reports --config no_ser_tab

# 处理问题
python main.py process-questions --config max
```

### 方式三：直接运行Pipeline

```bash
# 直接运行完整流程
python -m src.pipeline
```

## ⚙️ 配置说明

### 运行配置

系统提供多种预设配置，可根据需求选择：

- **`max`** - 最佳配置，使用Qwen-Turbo + 向量检索 + 重排序
- **`base`** - 基础配置，适合快速测试
- **`pdr`** - 使用父文档检索的配置

### 数据目录结构

```
data/stock_data/
├── pdf_reports/          # 原始PDF文件
├── databases/
│   ├── chunked_reports/  # 分块后的JSON文件
│   └── vector_dbs/       # FAISS向量数据库
├── debug_data/
│   └── 03_reports_markdown/  # Markdown格式文件
├── questions.json        # 问题文件
└── subset.csv           # 元数据文件
```

### 环境变量

| 变量名 | 必需 | 说明 |
|--------|------|------|
| `DASHSCOPE_API_KEY` | ✅ | 阿里云DashScope API密钥，用于文本嵌入和问答 |
| `OPENAI_API_KEY` | ❌ | OpenAI API密钥，用于备用问答服务 |
| `GEMINI_API_KEY` | ❌ | Google Gemini API密钥，用于备用问答服务 |

## 🔧 高级功能

### 自定义配置

您可以在 `src/pipeline.py` 中自定义配置：

```python
custom_config = RunConfig(
    use_serialized_tables=False,
    parent_document_retrieval=True,
    llm_reranking=True,
    parallel_requests=4,
    answering_model="qwen-turbo-latest"
)
```

### 批量处理

支持批量处理多个PDF文件：

```bash
# 并行处理PDF文件
python main.py parse-pdfs --parallel --max-workers 10 --chunk-size 2
```

## 📊 系统流程

### 数据处理流程

```
PDF文档 → PDF解析 → Markdown转换 → 文本分块 → 向量化 → 向量数据库 → 检索 → 重排序 → LLM生成答案
```

### 详细步骤

1. **PDF解析**：使用Docling将PDF转换为结构化JSON
2. **Markdown转换**：将JSON转换为Markdown格式便于处理
3. **文本分块**：将长文档分割成适合检索的文本块
4. **向量化**：使用DashScope API将文本块转换为向量
5. **存储**：将向量存储到FAISS向量数据库中
6. **检索**：根据用户问题检索相关文本块
7. **重排序**：使用LLM对检索结果进行重排序
8. **生成答案**：使用Qwen-Turbo模型生成最终答案

## 🛠️ 开发说明

### 项目结构

```
RAG-cy/
├── src/                    # 核心源代码
│   ├── pipeline.py         # 主流程控制
│   ├── pdf_parsing.py      # PDF解析模块
│   ├── ingestion.py        # 向量化模块
│   ├── retrieval.py        # 检索模块
│   ├── questions_processing.py  # 问答处理模块
│   └── ...
├── app_streamlit.py        # Web界面
├── main.py                 # 命令行工具
├── requirements.txt        # 依赖包
└── README.md              # 项目说明
```

### 主要模块

- **PDF解析模块**：负责PDF文档的解析和结构化
- **文本分块模块**：将长文档分割成适合检索的块
- **向量化模块**：使用DashScope API生成文本嵌入
- **检索模块**：支持向量检索和BM25检索
- **重排序模块**：LLM重排序提升检索质量
- **问答处理模块**：处理用户问题并生成答案
- **Web界面**：Streamlit构建的用户界面

## 🚨 注意事项

1. **API密钥**：请确保配置正确的DashScope API密钥
2. **内存要求**：建议至少8GB内存，16GB更佳
3. **文件格式**：目前主要支持PDF格式的年报文件
4. **网络连接**：需要稳定的网络连接访问API服务

## 📝 更新日志

- **v1.0.0** - 初始版本，支持基本的RAG问答功能
- 支持PDF文档解析和向量化
- 提供Web界面和命令行工具
- 集成Qwen-Turbo问答引擎

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目！

## 📄 许可证

MIT License

## 📞 联系方式

如有问题，请通过GitHub Issues联系我们。