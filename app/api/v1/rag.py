import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.tools.dependencies import get_current_user, get_current_admin_user
from app.models.rag import QuestionRequest, AnswerResponse, PDFUploadResponse
from app.services.rag_service import RAGService

# 创建 RAGService 实例
rag_service = RAGService()

# 支持的文件类型
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.xlsx'}

router = APIRouter()

@router.post("/upload-document", response_model=PDFUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """上传文档文件（支持PDF、DOCX、XLSX格式）"""
    # 获取文件扩展名
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    # 检查文件格式
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式: {file_extension}。支持格式: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    # 创建存储目录
    os.makedirs("data/documents", exist_ok=True)
    file_path = f"data/documents/{file.filename}"
    
    # 保存文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 处理文档
    try:
        result = await rag_service.process_documents(file_path, title, description)
        return result
    except Exception as e:
        # 清理文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask", response_model=AnswerResponse)
async def ask_question(
    question_data: QuestionRequest,
    current_user: dict = Depends(get_current_user)
):
    """提问关于《增删卜易》的问题"""
    try:
        # 注意：你的 generate_answer 方法不需要 pdf_ids 参数
        # 它内部会调用 search_similar_documents 进行检索
        result = await rag_service.generate_answer(question_data.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回答问题失败: {str(e)}")

@router.get("/documents")
async def get_documents(current_user: dict = Depends(get_current_admin_user)):
    """获取向量数据库中的文档统计信息"""
    try:
        document_count = rag_service.get_document_count()
        return {
            "document_count": document_count,
            "message": f"向量数据库中共有 {document_count} 个文档块"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档信息失败: {str(e)}")

@router.delete("/clear")
async def clear_documents(current_user: dict = Depends(get_current_admin_user)):
    """清空向量数据库"""
    try:
        success = rag_service.clear_vector_store()
        if success:
            return {"message": "向量数据库已清空"}
        else:
            raise HTTPException(status_code=500, detail="清空向量数据库失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空向量数据库失败: {str(e)}")

@router.post("/search")
async def search_documents(
    query: str,
    k: int = 5,
    current_user: dict = Depends(get_current_admin_user)  # 需要管理员权限
):
    """搜索相似文档（调试用）"""
    try:
        documents = rag_service.search_similar_documents(query, k)
        results = []
        for doc in documents:
            results.append({
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "source": doc.metadata.get("source", "未知"),
                "title": doc.metadata.get("title", "未知"),
                "doc_id": doc.metadata.get("doc_id", "未知")
            })
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索文档失败: {str(e)}")
    

@router.post("/api/v1/rag/init-zengshan")
async def init_zengshan_document(
    file_path: str, 
    title: str, 
    description: str = None,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    上传《增删卜易》文档
    
    参数:
    - file: 上传的文件
    - title: 文档标题
    - description: 文档描述（可选）

    返回: 文档处理结果

    """
    if not title:
        raise HTTPException(status_code=400, detail="文档标题不能为空")

    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")

    response = await rag_service.process_zengshan_document(file_path, title, description)
    
    return response

@router.post("/api/v1/rag/ask-zengshan")
async def ask_zengshan_question(
    question: str, 
    volume: str = None, 
    chapter: str = None,
    current_user: dict = Depends(get_current_user)    
):
    """提问《增删卜易》相关问题"""
    
    response = await rag_service.generate_zengshan_answer(
        question=question,
        volume_filter=volume,
        chapter_filter=chapter
    )
    
    return response
