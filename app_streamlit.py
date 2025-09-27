import streamlit as st
from pathlib import Path
from src.pipeline import Pipeline, max_config
from src.questions_processing import QuestionsProcessor
import json
import tempfile
import os
from complete_upload_processor import upload_and_process_file, get_upload_status, list_files
from data_processor import get_processing_status
from pdf_validator import validate_pdf_file

# 初始化pipeline
root_path = Path("data/stock_data")
pipeline = Pipeline(root_path, run_config=max_config)

st.set_page_config(page_title="RAG Challenge 2", layout="wide", page_icon="🚀")

# 页面标题
st.markdown("""
<div style='background: linear-gradient(90deg, #7b2ff2 0%, #f357a8 100%); padding: 20px 0; border-radius: 12px; text-align: center;'>
    <h2 style='color: white; margin: 0;'>🚀 RAG Challenge 2</h2>
    <div style='color: #fff; font-size: 16px;'>基于深度RAG系统，由RTX 5080 GPU加速 | 支持多公司年报问答 | 向量检索+LLM推理+GPT-4o</div>
</div>
""", unsafe_allow_html=True)

# 创建标签页
tab1, tab2, tab3 = st.tabs(["📝 智能问答", "📁 文件管理", "⚙️ 系统状态"])

# 标签页1：智能问答
with tab1:
    st.markdown("<h3 style='margin-top: 24px;'>智能问答</h3>", unsafe_allow_html=True)
    
    # 左侧输入区
    with st.sidebar:
        st.header("查询设置")
        # 仅单问题输入
        user_question = st.text_area("输入问题", "请简要总结公司2022年主营业务的主要内容。", height=80)
        submit_btn = st.button("生成答案", use_container_width=True)

    # 右侧主内容区
    if submit_btn and user_question.strip():
        with st.spinner("正在生成答案，请稍候..."):
            try:
                answer = pipeline.answer_single_question(user_question, kind="string")
                # 兼容 answer 可能为 str 或 dict
                if isinstance(answer, str):
                    try:
                        answer_dict = json.loads(answer)
                    except Exception:
                        st.error("返回内容无法解析为结构化答案：" + str(answer))
                        answer_dict = {}
                else:
                    answer_dict = answer
                
                # 直接从answer_dict获取各项内容
                step_by_step = answer_dict.get("step_by_step_analysis", "-")
                reasoning_summary = answer_dict.get("reasoning_summary", "-")
                relevant_pages = answer_dict.get("relevant_pages", [])
                final_answer = answer_dict.get("final_answer", "-")
                
                # 打印调试
                print("[DEBUG] step_by_step_analysis:", step_by_step)
                print("[DEBUG] reasoning_summary:", reasoning_summary)
                print("[DEBUG] relevant_pages:", relevant_pages)
                print("[DEBUG] final_answer:", final_answer)
                st.markdown("**分步推理：**")
                st.info(step_by_step)
                st.markdown("**推理摘要：**")
                st.success(reasoning_summary)
                st.markdown("**相关页面：** ")
                if relevant_pages and len(relevant_pages) > 0:
                    # 将页面列表转换为更友好的显示格式
                    pages_text = ", ".join([f"第{page}页" for page in relevant_pages])
                    st.info(f"📄 {pages_text}")
                else:
                    st.info("📄 未找到相关页面信息")
                st.markdown("**最终答案：**")
                st.markdown(f"<div style='background:#f6f8fa;padding:16px;border-radius:8px;font-size:18px;'>{final_answer}</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"生成答案时出错: {e}")
    else:
        st.info("请在左侧输入问题并点击【生成答案】")

# 标签页2：文件管理
with tab2:
    st.markdown("<h3 style='margin-top: 24px;'>文件管理</h3>", unsafe_allow_html=True)
    
    # 文件上传区域
    st.subheader("📤 上传新文件")
    
    uploaded_file = st.file_uploader(
        "选择PDF文件",
        type=['pdf'],
        help="支持PDF格式，文件大小不超过100MB"
    )
    
    company_name = st.text_input(
        "公司名称",
        value="中芯国际",
        help="请输入文件所属的公司名称"
    )
    
    if uploaded_file is not None and company_name.strip():
        # 显示文件信息
        file_details = {
            "文件名": uploaded_file.name,
            "文件大小": f"{uploaded_file.size / 1024 / 1024:.2f} MB",
            "文件类型": uploaded_file.type
        }
        
        st.write("**文件信息：**")
        for key, value in file_details.items():
            st.write(f"- {key}: {value}")
        
        # 验证PDF文件
        with st.spinner("正在验证PDF文件..."):
            # 保存临时文件进行验证
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            # 验证PDF文件
            validation_result = validate_pdf_file(tmp_file_path)
            
            # 删除临时文件
            os.unlink(tmp_file_path)
        
        # 显示验证结果
        if validation_result["valid"]:
            st.success(f"✅ {validation_result['message']}")
            st.write(f"📊 验证详情:")
            st.write(f"- 页面数量: {validation_result['pages']} 页")
            st.write(f"- 文本长度: {validation_result['text_length']} 字符")
            
            if validation_result["text_length"] < 100:
                st.warning("⚠️ 警告：PDF文件文本内容较少，可能影响解析效果")
        else:
            st.error(f"❌ {validation_result['message']}")
            st.stop()
        
        # 上传按钮
        if st.button("🚀 上传文件", type="primary"):
            with st.spinner("正在上传文件..."):
                try:
                    # 保存上传的文件到临时目录
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                    
                    # 上传并处理文件
                    result = upload_and_process_file(tmp_file_path, company_name.strip())
                    
                    # 删除临时文件
                    os.unlink(tmp_file_path)
                    
                    if result["success"]:
                        st.success(f"✅ {result['message']}")
                        st.write(f"**文件ID:** {result['stock_id']}")
                        st.write(f"**文件名:** {result['filename']}")
                        
                        # 显示处理步骤
                        if "steps" in result:
                            st.info("📋 处理步骤:")
                            for step in result["steps"]:
                                st.write(f"  {step}")
                        
                        st.success("✅ 文件上传和处理完成！现在可以开始问答了。")
                    else:
                        st.error(f"❌ 上传失败: {result['message']}")
                        
                except Exception as e:
                    st.error(f"❌ 上传过程中出错: {str(e)}")
    
    # 文件列表
    st.subheader("📋 已上传文件")
    
    # 刷新按钮
    if st.button("🔄 刷新文件列表"):
        st.rerun()
    
    files = list_files()
    
    if files:
        # 创建文件列表
        for i, file_info in enumerate(files):
            with st.expander(f"📄 {file_info['filename']} ({file_info['company_name']})"):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**文件ID:** {file_info['stock_id']}")
                    st.write(f"**公司:** {file_info['company_name']}")
                    
                    # 显示详细处理状态
                    status_colors = {
                        "处理完成": "✅",
                        "未向量化": "⚠️",
                        "未分块": "⚠️", 
                        "PDF未解析": "❌",
                        "文件缺失": "❌"
                    }
                    
                    status_icon = status_colors.get(file_info.get('processing_status', '未知'), "❓")
                    st.write(f"**处理状态:** {status_icon} {file_info.get('processing_status', '未知')}")
                    
                    # 显示各阶段状态
                    st.write("**处理阶段:**")
                    st.write(f"  - PDF文件: {'✅' if file_info.get('pdf_exists', False) else '❌'}")
                    st.write(f"  - Markdown: {'✅' if file_info.get('markdown_exists', False) else '❌'}")
                    st.write(f"  - 分块文件: {'✅' if file_info.get('chunk_exists', False) else '❌'}")
                    st.write(f"  - 向量文件: {'✅' if file_info.get('vector_exists', False) else '❌'}")
                
                with col2:
                    if st.button(f"🗑️ 删除", key=f"delete_{i}"):
                        with st.spinner("正在删除文件..."):
                            try:
                                from complete_upload_processor import complete_processor
                                delete_result = complete_processor.delete_file(file_info['stock_id'])
                                
                                if delete_result["success"]:
                                    st.success("✅ 文件删除成功！")
                                    st.write(f"删除了 {len(delete_result['deleted_files'])} 个文件")
                                    st.rerun()  # 刷新页面
                                else:
                                    st.error(f"❌ 删除失败: {delete_result['message']}")
                            except Exception as e:
                                st.error(f"❌ 删除时发生错误: {str(e)}")
                
                with col3:
                    if st.button(f"🔄 重新处理", key=f"reprocess_{i}"):
                        with st.spinner("正在重新处理文件..."):
                            try:
                                from complete_upload_processor import complete_processor
                                reprocess_result = complete_processor.reprocess_file(file_info['stock_id'])
                                
                                if reprocess_result["success"]:
                                    st.success("✅ 重新处理完成！")
                                    st.write("**处理步骤:**")
                                    for step in reprocess_result["steps"]:
                                        st.write(f"  {step}")
                                    st.rerun()  # 刷新页面
                                else:
                                    st.error(f"❌ 重新处理失败: {reprocess_result['message']}")
                                    if reprocess_result.get("steps"):
                                        st.write("**已完成的步骤:**")
                                        for step in reprocess_result["steps"]:
                                            st.write(f"  {step}")
                            except Exception as e:
                                st.error(f"❌ 重新处理时发生错误: {str(e)}")
    else:
        st.info("📭 暂无上传的文件")

# 标签页3：系统状态
with tab3:
    st.markdown("<h3 style='margin-top: 24px;'>系统状态</h3>", unsafe_allow_html=True)
    
    # 获取状态信息
    upload_status = get_upload_status()
    processing_status = get_processing_status()
    
    # 显示状态卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📁 总文件数",
            value=upload_status.get("total_files", 0)
        )
    
    with col2:
        st.metric(
            label="📄 PDF文件",
            value=processing_status.get("pdf_reports", 0)
        )
    
    with col3:
        st.metric(
            label="🔧 已处理文件",
            value=processing_status.get("chunked_reports", 0)
        )
    
    with col4:
        st.metric(
            label="🧠 向量数据库",
            value=processing_status.get("vector_dbs", 0)
        )
    
    # 公司列表
    st.subheader("🏢 支持的公司")
    companies = upload_status.get("companies", [])
    if companies:
        for company in companies:
            st.write(f"• {company}")
    else:
        st.info("暂无公司数据")
    
    # 系统操作
    st.subheader("⚙️ 系统操作")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 处理新文件", type="primary"):
            st.info("ℹ️ 新文件会在上传时自动处理")
    
    with col2:
        if st.button("🔄 强制重新处理"):
            st.info("ℹ️ 请重新上传文件以重新处理")
    
    # 检查处理状态
    pdf_count = processing_status.get("pdf_reports", 0)
    chunk_count = processing_status.get("chunked_reports", 0)
    vector_count = processing_status.get("vector_dbs", 0)
    
    # 检查是否有处理问题
    status_issues = []
    if pdf_count > chunk_count:
        status_issues.append(f"⚠️ 有 {pdf_count - chunk_count} 个PDF文件未处理")
    if chunk_count > vector_count:
        status_issues.append(f"⚠️ 有 {chunk_count - vector_count} 个分块文件未向量化")
    
    if status_issues:
        st.subheader("🔧 处理问题")
        for issue in status_issues:
            st.warning(issue)
        
        # 提供修复按钮
        if st.button("🔧 修复处理问题", type="secondary"):
            with st.spinner("正在修复..."):
                try:
                    from local_pdf_parser import process_failed_pdfs
                    process_failed_pdfs()
                    st.success("✅ 修复完成！请刷新页面查看最新状态。")
                    st.rerun()
                except Exception as e:
                    st.error(f"修复失败: {e}")
    else:
        if pdf_count > 0:
            st.success("✅ 所有文件都已正确处理")
    
    # API状态检查
    st.subheader("🌐 API状态")
    try:
        from smart_vector_processor import SmartVectorProcessor
        processor = SmartVectorProcessor()
        api_status = processor.check_api_status()
        
        if api_status["available"]:
            st.success("✅ DashScope API 正常")
        else:
            st.warning(f"⚠️ DashScope API 不可用: {api_status['reason']}")
            st.info("系统将使用降级方案进行向量化")
            
    except Exception as e:
        st.error(f"检查API状态失败: {e}")
    
    # 显示详细信息
    with st.expander("📊 详细信息"):
        st.json({
            "upload_status": upload_status,
            "processing_status": processing_status
        }) 