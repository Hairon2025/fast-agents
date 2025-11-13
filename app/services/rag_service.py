from typing import List, Optional
from langchain_community.document_loaders import UnstructuredExcelLoader, Docx2txtLoader, PyPDFLoader
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain_core.documents import Document
from app.utils.doc_preprocessor import ZengShanBuYiPreprocessor
from app.models.rag import PDFUploadResponse, AnswerResponse
from datetime import datetime
from app.config import settings
import logging
import time
import os
import uuid


class RAGService:
    """
    RAG (Retrieval-Augmented Generation) 服务类
    负责文档加载、文本分割、向量化存储和检索增强生成
    """
    
    def __init__(self):
        """初始化RAG服务，设置嵌入模型、LLM和向量数据库"""
        # 初始化嵌入模型
        self.embeddings_model = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.EMBEDDING_MODEL_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        
        # 初始化大语言模型
        self.llm = ChatTongyi(
            model=settings.LLM_MODEL,
            api_key=settings.TONYIQWEN_API_KEY,
            temperature=0.1
        )
        
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        # 初始化向量数据库
        self.vector_store = self._initialize_vector_store()

        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("RAGService")

        self.zengshan_preprocessor = ZengShanBuYiPreprocessor()

    def _initialize_vector_store(self) -> Chroma:
        """
        初始化并返回向量数据库实例
        
        Returns:
            Chroma: 向量数据库实例
        """
        return Chroma(
            collection_name="rag_vector_store",
            persist_directory=settings.VECTOR_STORE_PATH,
            embedding_function=self.embeddings_model
        )

    def _load_document(self, file_path: str, title: str, description: Optional[str] = None) -> List[Document]:
        """
        根据文件扩展名加载文档内容
        
        Args:
            file_path: 文件路径
            title: 文档标题
            description: 文档描述（可选）
            
        Returns:
            List[Document]: 加载的文档列表
            
        Raises:
            ValueError: 文件不存在或格式不支持时抛出
        """
        if not os.path.exists(file_path):
            raise ValueError(f"文件不存在: {file_path}")
            
        file_name = os.path.basename(file_path)
        file_extension = file_name.split(".")[-1].lower()
        
        # 支持的文档类型映射
        loaders = {
            "docx": Docx2txtLoader,
            "pdf": PyPDFLoader,
            "xlsx": UnstructuredExcelLoader,
        }
        
        loader_class = loaders.get(file_extension)
        if not loader_class:
            raise ValueError(f"不支持的文件格式: {file_extension}")
        
        try:
            self.logger.info(f"正在加载文档: {file_name}")
            loader = loader_class(file_path)
            documents = loader.load()
            
            # 为文档添加元数据
            for doc in documents:
                doc.metadata.update({
                    "title": title,
                    "description": description or "",
                    "source": file_name,
                    "load_time": datetime.now().isoformat()
                })
                
            self.logger.info(f"成功加载文档: {file_name}, 共 {len(documents)} 页")
            return documents
            
        except Exception as e:
            self.logger.error(f"加载文档失败 {file_name}: {str(e)}")
            raise Exception(f"文档加载失败: {str(e)}")

    def _split_documents(self, documents: List[Document]) -> List[Document]:
        """
        将文档分割成较小的文本块
        
        Args:
            documents: 待分割的文档列表
            
        Returns:
            List[Document]: 分割后的文本块列表
        """
        if not documents:
            return []
            
        self.logger.info("开始文档分割")
        chunks = self.text_splitter.split_documents(documents)
        self.logger.info(f"文档分割完成，共生成 {len(chunks)} 个文本块")
        
        return chunks

    def _add_documents_to_vector_store(self, chunks: List[Document], doc_id: str) -> None:
        """
        将文本块添加到向量数据库
        
        Args:
            chunks: 文本块列表
            doc_id: 文档唯一标识符
        """
        if not chunks:
            self.logger.warning("没有文本块可添加到向量数据库")
            return
            
        # 为每个chunk添加文档ID
        # for chunk in chunks:
        #     chunk.metadata["doc_id"] = doc_id
        
        # ids = [str(uuid.uuid4()) for _ in range(len(chunks))]
        # self.logger.info("正在将文档添加到向量数据库")
        # self.vector_store.add_documents(documents=chunks, ids=ids)
        # self.logger.info(f"文档已成功添加到向量数据库，共添加 {len(chunks)} 个文档块")

        if not chunks:
            self.logger.warning("没有文本块可添加到向量数据库")
            return
            
        # 为每个chunk添加文档ID
        for i, chunk in enumerate(chunks):
            chunk.metadata["doc_id"] = doc_id
            chunk.metadata["chunk_id"] = f"{doc_id}_{i}"
        
        self.logger.info(f"正在将 {len(chunks)} 个文本块添加到向量数据库")
        
        try:
            # 分批处理，避免一次性处理太多数据
            batch_size = 64
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                self.vector_store.add_documents(batch)
                self.logger.info(f"已添加批次 {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")
                
            self.logger.info("文档已成功添加到向量数据库")
            
        except Exception as e:
            self.logger.error(f"添加文档到向量数据库失败: {str(e)}")
            # 重新抛出异常，让上层处理
            raise


    async def process_documents(self, file_path: str, title: str, description: Optional[str] = None) -> PDFUploadResponse:
        """
        处理上传的文档：加载、分割并存储到向量数据库
        
        Args:
            file_path: 文件路径
            title: 文档标题
            description: 文档描述（可选）
            
        Returns:
            PDFUploadResponse: 处理结果响应
            
        Raises:
            Exception: 处理过程中出现错误时抛出
        """
        if not file_path:
            return PDFUploadResponse(
                status="warning",
                message="没有文档需要处理"
            )

        try:
            # 生成文档唯一ID
            doc_id = str(uuid.uuid4())
            
            # 1. 加载文档
            documents = self._load_document(file_path, title, description)
            
            # 2. 分割文档
            chunks = self._split_documents(documents)
            
            # 3. 存储到向量数据库
            self._add_documents_to_vector_store(chunks, doc_id)
            
            # 返回处理结果
            return PDFUploadResponse(
                id=doc_id,
                title=title,
                filename=os.path.basename(file_path),
                upload_time=datetime.now(),
                status="success",
                message=f"文档处理成功，生成 {len(chunks)} 个文本块"
            )
            
        except Exception as e:
            self.logger.error(f"文档处理失败: {str(e)}")
            raise Exception(f"文档处理失败: {str(e)}")

    def search_similar_documents(self, query: str, k: int = 5) -> List[Document]:
        """
        在向量数据库中搜索相似的文档
        
        Args:
            query: 查询文本
            k: 返回的最相似文档数量
            
        Returns:
            List[Document]: 相似的文档列表
        """
        try:
            self.logger.info(f"搜索相似文档: {query}")
            results = self.vector_store.similarity_search(query, k=k)
            self.logger.info(f"找到 {len(results)} 个相关文档")
            return results
        except Exception as e:
            self.logger.error(f"文档搜索失败: {str(e)}")
            return []

    async def generate_answer(self, question: str, context_documents: List[Document] = None) -> AnswerResponse:
        """
        基于检索到的文档生成答案
        
        Args:
            question: 用户问题
            context_documents: 上下文文档列表（可选）
            
        Returns:
            AnswerResponse: 生成的答案响应
        """
        start_time = time.time()
        try:
            # 如果没有提供上下文文档，则进行检索
            if not context_documents:
                context_documents = self.search_similar_documents(question, settings.SIMILARITY_TOP_K)
            
            # 构建上下文
            context_text = "\n\n".join([doc.page_content for doc in context_documents])
            
            # 构建提示词
            prompt = f"""
            你是清代野鹤老人所著《增删卜易》的专业知识问答专家，仅以该书的原文内容、理论体系、术语定义、规则阐释为唯一知识库来源，不掺杂任何其他六爻流派（如《卜筮正宗》《火珠林》）、现代改编观点或实际占问断卦行为。

### 你的核心职责：
1. 严格基于提供的《增删卜易》资料内容回答
2. 关键观点必须引用原文，标注具体出处
3. 对专业术语（如用神、世应、空亡等）要进行通俗解释
4. 保持客观学术立场，不涉及实际占卜

### 回答结构要求：
1. **核心结论**：直接回答问题的要点
2. **原文依据**：引用相关原文支撑观点
3. **理论解析**：解释涉及的六爻理论和概念
4. **知识边界**：说明该内容在原著中的位置和意义

### 禁忌规则：
- 不得引入《增删卜易》之外的任何六爻理论、民间说法或现代观点；
- 不得回应实际占问断卦类问题（如“我占了一卦，帮忙看看吉凶”），需引导用户聚焦原著知识本身；
- 不得将知识解读与封建迷信挂钩，需客观呈现《增删卜易》作为传统民俗文化著作的理论内容，注明“相关知识为原著理论表述，仅供文化研究和知识了解参考”；
- 不得在无原文依据的情况下随意推导、编造理论，确保所有回答都有原著支撑。

现在，请接收用户关于《增删卜易》的知识类问题，严格按照上述要求提供准确、专业、合规的解答。

上下文：
{context_text}

问题：{question}

根据上下文提供准确、相关的答案。如果上下文信息不足以回答问题，请如实说明。"""

            # 调用LLM生成答案
            self.logger.info("正在生成答案")
            response = await self.llm.ainvoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            
            # answer = "已经生成了答案（此处为示例回答）"

            # 计算处理时间
            processing_time = time.time() - start_time
            
            # 提取来源信息
            sources = []
            for doc in context_documents:
                source_info = {
                    "source": doc.metadata.get("source", "未知来源"),
                    "content": doc.page_content[:50] + "..." if len(doc.page_content) > 50 else doc.page_content,  # 截取前50字符
                    "page": doc.metadata.get("page", 0),
                    "title": doc.metadata.get("title", "")
                }
                sources.append(source_info)
            
            return AnswerResponse(
                question=question,
                answer=answer,
                sources=sources,  # 添加必需的 sources 字段
                processing_time=processing_time,  # 添加必需的 processing_time 字段
                status="success"
            )
            
        except Exception as e:
            self.logger.error(f"答案生成失败: {str(e)}")
            return AnswerResponse(
                question=question,
                answer="抱歉，生成答案时出现错误。",
                source_documents=[],
                status="error",
                error_message=str(e)
            )

    def get_document_count(self) -> int:
        """
        获取向量数据库中的文档数量
        
        Returns:
            int: 文档数量
        """
        try:
            return self.vector_store._collection.count()
        except Exception as e:
            self.logger.error(f"获取文档数量失败: {str(e)}")
            return 0

    def clear_vector_store(self) -> bool:
        """
        清空向量数据库
        
        Returns:
            bool: 操作是否成功
        """
        try:
            self.vector_store.delete_collection()
            self.vector_store = self._initialize_vector_store()
            self.logger.info("向量数据库已清空")
            return True
        except Exception as e:
            self.logger.error(f"清空向量数据库失败: {str(e)}")
            return False
        
    async def process_zengshan_document(self, file_path: str, title: str, 
                                      description: Optional[str] = None) -> PDFUploadResponse:
        """
        专门处理《增删卜易》文档
        
        Args:
            file_path: 文件路径
            title: 文档标题
            description: 文档描述
            
        Returns:
            PDFUploadResponse: 处理结果
        """
        try:
            doc_id = str(uuid.uuid4())
            
            self.logger.info(f"开始处理《增删卜易》文档: {title}")
            
            # 1. 使用专用预处理器提取和解析文本
            document_data = self.zengshan_preprocessor.extract_text_from_pdf(file_path)
            
            # 2. 创建语义完整的知识块
            chunks = self.zengshan_preprocessor.create_semantic_chunks(document_data)
            
            # 3. 添加文档元数据
            for chunk in chunks:
                chunk.metadata.update({
                    "doc_id": doc_id,
                    "book": "增删卜易",
                    "original_title": title,
                    "description": description or "",
                    "content_language": "文言文",
                    "content_era": "清代",
                    "document_type": "易学经典"
                })
            
            # 4. 存储到向量数据库
            self._add_documents_to_vector_store(chunks, doc_id)
            
            # 统计信息
            volume_count = len(document_data["structure"]["volumes"])
            chapter_count = sum(len(vol["chapters"]) for vol in document_data["structure"]["volumes"])
            
            return PDFUploadResponse(
                id=doc_id,
                title=title,
                filename=os.path.basename(file_path),
                upload_time=datetime.now(),
                status="success",
                message=f"《增删卜易》处理成功：{volume_count}卷 {chapter_count}章，生成 {len(chunks)} 个语义块"
            )
            
        except Exception as e:
            self.logger.error(f"《增删卜易》处理失败: {str(e)}")
            raise Exception(f"文档处理失败: {str(e)}")
        
    def _split_documents(self, documents: List[Document]) -> List[Document]:
        """
        智能文档分割
        
        Args:
            documents: 待分割的文档列表
            
        Returns:
            List[Document]: 分割后的文本块列表
        """
        if not documents:
            return []
            
        # 检查是否为《增删卜易》
        is_zengshan = any("增删卜易" in doc.metadata.get("title", "") or 
                         "增删卜易" in doc.page_content for doc in documents)
        
        if is_zengshan:
            self.logger.info("检测到《增删卜易》文档，使用专用分块策略")
            # 对于已经预处理过的文档，直接返回
            return documents
        else:
            self.logger.info("使用通用分块策略")
            return self.text_splitter.split_documents(documents)
        
    def search_zengshan_documents(self, query: str, k: int = 5, 
                            volume_filter: str = None,
                            chapter_filter: str = None,
                            content_type: str = None) -> List[Document]:
        """
        搜索《增删卜易》文档，支持多种过滤条件
        
        Args:
            query: 查询文本
            k: 返回数量
            volume_filter: 卷过滤
            chapter_filter: 章节过滤
            content_type: 内容类型过滤（目录、序言、章节等）
            
        Returns:
            List[Document]: 相似的文档列表
        """
        try:
            # 构建过滤器
            filter_dict = {"book": "增删卜易"}
            if volume_filter:
                filter_dict["volume_index"] = volume_filter
            if chapter_filter:
                filter_dict["chapter_index"] = chapter_filter
            if content_type:
                filter_dict["content_type"] = content_type
                
            self.logger.info(f"搜索《增删卜易》，过滤器: {filter_dict}")
            
            if filter_dict:
                results = self.vector_store.similarity_search(
                    query, k=k, filter=filter_dict
                )
            else:
                results = self.vector_store.similarity_search(query, k=k)
                
            self.logger.info(f"找到 {len(results)} 个相关文档片段")
            
            # 按结构排序：卷 -> 章 -> 段落
            results.sort(key=lambda x: (
                x.metadata.get("volume_index", "999"),
                x.metadata.get("chapter_index", "999"),
                x.metadata.get("paragraph_index", 999),
                x.metadata.get("content_type", "z")
            ))
            
            return results
            
        except Exception as e:
            self.logger.error(f"文档搜索失败: {str(e)}")
            return []

    async def generate_zengshan_answer(self, question: str, 
                                    context_documents: List[Document] = None,
                                    volume_filter: str = None,
                                    chapter_filter: str = None) -> AnswerResponse:
        """
        基于《增删卜易》生成专业答案
        
        Args:
            question: 用户问题
            context_documents: 上下文文档列表
            volume_filter: 卷过滤
            chapter_filter: 章节过滤
            
        Returns:
            AnswerResponse: 生成的答案响应
        """
        start_time = time.time()
        
        try:
            # 检索相关文档
            if not context_documents:
                context_documents = self.search_zengshan_documents(
                    question, k=5, 
                    volume_filter=volume_filter,
                    chapter_filter=chapter_filter
                )
            
            # 构建详细的上下文信息
            context_parts = []
            sources_info = []
            
            for i, doc in enumerate(context_documents):
                # 构建来源信息
                source_desc = self._build_source_description(doc)
                
                source_info = {
                    "source": source_desc,
                    "volume": doc.metadata.get("volume_title"),
                    "chapter": doc.metadata.get("chapter_title"),
                    "content_type": doc.metadata.get("content_type"),
                    "block_type": doc.metadata.get("block_type"),
                    "content_preview": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content
                }
                sources_info.append(source_info)
                
                # 构建上下文内容
                context_part = f"[来源 {i+1}: {source_desc}]\n{doc.page_content}"
                context_parts.append(context_part)
            
            context_text = "\n\n".join(context_parts)
            
            # 构建针对《增删卜易》的专业提示词
            prompt = f"""你是一位精通《增删卜易》的易学专家。请基于以下上下文信息回答问题。

    《增删卜易》上下文信息：
    {context_text}

    问题：{question}

    要求：
    1. 基于《增删卜易》的原文内容给出准确答案
    2. 对于文言文内容，请提供适当的现代文解释
    3. 如果涉及卜卦方法，请详细说明操作步骤
    4. 如果上下文信息不足，请如实说明
    5. 回答要专业、准确、清晰，体现易学专家的水平

    请开始回答："""

            # 生成答案
            self.logger.info("正在调用LLM生成专业答案")
            response = await self.llm.ainvoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            
            # 计算处理时间
            processing_time = round(time.time() - start_time, 2)
            
            self.logger.info(f"《增删卜易》答案生成成功，处理时间: {processing_time}秒")
            
            return AnswerResponse(
                question=question,
                answer=answer,
                sources=sources_info,
                processing_time=processing_time,
                status="success"
            )
            
        except Exception as e:
            processing_time = round(time.time() - start_time, 2)
            self.logger.error(f"答案生成失败: {str(e)}")
            
            return AnswerResponse(
                question=question,
                answer="抱歉，生成答案时出现错误，请稍后重试。",
                sources=[],
                processing_time=processing_time,
                status="error",
                error_message=str(e)
            )

    def _build_source_description(self, doc: Document) -> str:
        """构建来源描述"""
        parts = []
        
        if doc.metadata.get("volume_title"):
            parts.append(doc.metadata["volume_title"])
        
        if doc.metadata.get("chapter_title"):
            parts.append(doc.metadata["chapter_title"])
        
        if doc.metadata.get("content_type"):
            content_type_map = {
                "目录": "目录",
                "序言": "序言", 
                "卷标题": "卷首",
                "章节": "正文",
                "章节段落": "段落"
            }
            parts.append(content_type_map.get(doc.metadata["content_type"], doc.metadata["content_type"]))
        
        return " · ".join(parts)