from pydantic import BaseModel, Field, field_validator # , EmailStr
from typing import List, Optional
from datetime import datetime


class PDFUploadRequest(BaseModel):
    title: str = Field(..., description="PDF标题")
    description: Optional[str] = Field(None, description="PDF描述")

class PDFUploadResponse(BaseModel):
    id: str = Field(..., description="PDF ID")
    title: str = Field(..., description="PDF标题")
    filename: str = Field(..., description="文件名")
    upload_time: datetime = Field(..., description="上传时间")
    status: str = Field(..., description="上传状态")
    message: Optional[str] = Field(None, description="附加信息")

class QuestionRequest(BaseModel):
    question: str = Field(..., description="问题内容")
    pdf_ids: Optional[List[str]] = Field(None, description="指定在哪些PDF中搜索")

class AnswerResponse(BaseModel):
    question: str = Field(..., description="问题内容")
    answer: str = Field(..., description="回答")
    sources: List[dict] = Field(..., description="引用的文档片段")
    processing_time: float = Field(..., description="处理时间")
    status: str = Field(None, description="状态")
    error_message: Optional[str] = Field(None, description="错误信息（如果有）")

class PDFDocumentResponse(BaseModel):
    id: str = Field(..., description="PDF ID")
    title: str = Field(..., description="PDF标题")
    filename: str = Field(..., description="文件名")
    upload_time: datetime = Field(..., description="上传时间")
    chunk_count: int = Field(..., description="分块数量")
    status: str = Field(..., description="状态")