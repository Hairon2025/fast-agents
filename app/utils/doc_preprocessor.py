import re
import pdfplumber
from typing import List, Dict, Any, Tuple, Optional
from langchain_core.documents import Document
import logging

class ZengShanBuYiPreprocessor:
    """《增删卜易》专用预处理和分块器"""
    
    def __init__(self):
        self.logger = logging.getLogger("ZengShanBuYiPreprocessor")
        
        # 定义结构模式
        self.structure_patterns = {
            'toc': r'^目\s*录',
            'volume': r'^【卷之[一二三四五六七八九十]+】',
            'chapter': [
                r'^[一二三四五六七八九十]、[^\.]+章',
                r'^[^\.]+章',
                r'^[①②③④⑤⑥⑦⑧⑨⑩]、[^\.]+',
            ],
            'annotation': [
                r'^\[乾按\].*',
                r'^\[注\].*',
                r'^\[居士按\].*',
            ],
            'page_number': r'^\d+$'
        }
        
        # 中文数字映射
        self.chinese_numbers = {
            '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
            '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'
        }

    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        从PDF提取文本并进行初步结构解析
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            Dict: 包含文本和结构信息
        """
        self.logger.info(f"开始提取PDF文本: {pdf_path}")
        
        full_text = ""
        pages_content = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        # 清理页面文本
                        cleaned_text = self._clean_page_text(text, page_num + 1)
                        full_text += cleaned_text + "\n"
                        pages_content.append({
                            "page_number": page_num + 1,
                            "content": cleaned_text
                        })
            
            self.logger.info(f"PDF提取完成，共 {len(pages_content)} 页")
            
            # 解析文档结构
            structure = self._parse_document_structure(full_text, pages_content)
            
            return {
                "full_text": full_text,
                "pages": pages_content,
                "structure": structure
            }
            
        except Exception as e:
            self.logger.error(f"PDF提取失败: {str(e)}")
            raise

    def _clean_page_text(self, text: str, page_num: int) -> str:
        """
        清理单页文本
        
        Args:
            text: 原始文本
            page_num: 页码
            
        Returns:
            str: 清理后的文本
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 过滤孤立页码
            if re.match(self.structure_patterns['page_number'], line) and len(line) < 4:
                continue
                
            # 清理多余空格
            line = re.sub(r'\s+', ' ', line)
            
            cleaned_lines.append(line)
            
        return '\n'.join(cleaned_lines)

    def _parse_document_structure(self, text: str, pages: List[Dict]) -> Dict[str, Any]:
        """
        解析文档结构
        
        Args:
            text: 完整文本
            pages: 页面内容列表
            
        Returns:
            Dict: 文档结构信息
        """
        lines = text.split('\n')
        structure = {
            "has_toc": False,
            "preface": None,
            "volumes": [],
            "current_volume": None,
            "current_chapter": None
        }
        
        current_section = "preface"  # preface, toc, volume, chapter
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 识别目录
            if re.match(self.structure_patterns['toc'], line):
                structure["has_toc"] = True
                current_section = "toc"
                continue
                
            # 识别序言
            if "增删卜易序" in line and current_section == "preface":
                structure["preface"] = {
                    "title": "增删卜易序",
                    "content": line
                }
                current_section = "preface_content"
                continue
                
            if current_section == "preface_content":
                structure["preface"]["content"] += "\n" + line
                # 序言结束条件（遇到第一个卷或章节）
                if re.match(self.structure_patterns['volume'], line):
                    current_section = "volume"
                continue
                
            # 识别卷
            volume_match = re.match(self.structure_patterns['volume'], line)
            if volume_match:
                volume_info = {
                    "title": line,
                    "volume_index": self._chinese_to_number(line[3:-1]),
                    "chapters": []
                }
                structure["volumes"].append(volume_info)
                structure["current_volume"] = volume_info
                current_section = "volume"
                continue
                
            # 识别章节
            chapter_found = False
            for pattern in self.structure_patterns['chapter']:
                if re.match(pattern, line):
                    chapter_found = True
                    if structure["current_volume"]:
                        chapter_info = {
                            "title": line,
                            "content": "",
                            "annotations": []
                        }
                        structure["current_volume"]["chapters"].append(chapter_info)
                        structure["current_chapter"] = chapter_info
                        current_section = "chapter_content"
                    break
                    
            # 处理章节内容
            if not chapter_found and structure["current_chapter"]:
                # 检查是否为注释
                is_annotation = False
                for pattern in self.structure_patterns['annotation']:
                    if re.match(pattern, line):
                        is_annotation = True
                        structure["current_chapter"]["annotations"].append(line)
                        break
                
                if not is_annotation:
                    structure["current_chapter"]["content"] += line + "\n"
                    
        return structure

    def create_semantic_chunks(self, document_data: Dict[str, Any]) -> List[Document]:
        """
        创建语义完整的知识块
        
        Args:
            document_data: 文档数据
            
        Returns:
            List[Document]: 语义块列表
        """
        chunks = []
        structure = document_data["structure"]
        
        # 1. 处理序言
        if structure["preface"]:
            preface_chunk = self._create_preface_chunk(structure["preface"])
            chunks.append(preface_chunk)
        
        # 2. 处理目录
        if structure["has_toc"]:
            toc_chunks = self._create_toc_chunks(document_data["full_text"])
            chunks.extend(toc_chunks)
        
        # 3. 处理各卷和章节
        for volume in structure["volumes"]:
            volume_chunks = self._process_volume_semantic(volume)
            chunks.extend(volume_chunks)
            
        self.logger.info(f"创建了 {len(chunks)} 个语义完整的知识块")
        return chunks

    def _create_preface_chunk(self, preface: Dict[str, Any]) -> Document:
        """创建序言块"""
        content = preface["title"] + "\n\n" + preface["content"]
        
        return Document(
            page_content=content,
            metadata={
                "content_type": "序言",
                "block_type": "preface",
                "volume_title": "序言",
                "volume_index": "0",
                "chapter_title": "增删卜易序",
                "chapter_index": "0",
                "language_style": "文言文",
                "era": "清代"
            }
        )

    def _create_toc_chunks(self, full_text: str) -> List[Document]:
        """创建目录块"""
        lines = full_text.split('\n')
        toc_lines = []
        in_toc = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 开始目录
            if re.match(self.structure_patterns['toc'], line):
                in_toc = True
                continue
                
            # 结束目录（遇到第一个卷）
            if in_toc and re.match(self.structure_patterns['volume'], line):
                break
                
            if in_toc and line:
                # 清理目录行（去除页码和点）
                cleaned_line = re.sub(r'\.{3,}\s*\d+', '', line).strip()
                if (cleaned_line and len(cleaned_line) > 1 and 
                    not re.match(r'^\d+$', cleaned_line)):
                    toc_lines.append(cleaned_line)
        
        if toc_lines:
            toc_content = "《增删卜易》目录\n\n" + "\n".join(toc_lines)
            toc_doc = Document(
                page_content=toc_content,
                metadata={
                    "content_type": "目录",
                    "block_type": "table_of_contents",
                    "volume_title": "全书目录",
                    "volume_index": "0",
                    "chapter_title": "目录",
                    "chapter_index": "0"
                }
            )
            return [toc_doc]
        
        return []

    def _process_volume_semantic(self, volume: Dict[str, Any]) -> List[Document]:
        """处理卷的语义分块"""
        chunks = []
        
        # 卷标题块
        volume_doc = Document(
            page_content=volume["title"],
            metadata={
                "content_type": "卷标题",
                "block_type": "volume_title",
                "volume_title": volume["title"],
                "volume_index": volume["volume_index"],
                "chapter_title": "卷标题",
                "chapter_index": "0"
            }
        )
        chunks.append(volume_doc)
        
        # 处理卷内章节
        for chapter in volume["chapters"]:
            chapter_chunks = self._process_chapter_semantic(chapter, volume)
            chunks.extend(chapter_chunks)
            
        return chunks

    def _process_chapter_semantic(self, chapter: Dict[str, Any], volume: Dict[str, Any]) -> List[Document]:
        """处理章节的语义分块"""
        chunks = []
        
        # 章节标题和内容合并为一个语义块
        chapter_content = self._build_chapter_content(chapter)
        
        # 如果章节内容过长，按语义分割
        if len(chapter_content) > 1500:  # 阈值可根据需要调整
            sub_chunks = self._split_large_chapter(chapter_content, chapter, volume)
            chunks.extend(sub_chunks)
        else:
            # 整个章节作为一个语义块
            chapter_doc = Document(
                page_content=chapter_content,
                metadata={
                    "content_type": "章节",
                    "block_type": "chapter",
                    "volume_title": volume["title"],
                    "volume_index": volume["volume_index"],
                    "chapter_title": chapter["title"],
                    "chapter_index": self._extract_chapter_index(chapter["title"]),
                    "language_style": "文言文",
                    "era": "清代"
                }
            )
            chunks.append(chapter_doc)
            
        return chunks

    def _build_chapter_content(self, chapter: Dict[str, Any]) -> str:
        """构建章节完整内容"""
        content = chapter["title"] + "\n\n"
        content += chapter["content"]
        
        # 添加注释
        if chapter["annotations"]:
            content += "\n\n" + "\n".join(chapter["annotations"])
            
        return content.strip()

    def _split_large_chapter(self, content: str, chapter: Dict[str, Any], 
                           volume: Dict[str, Any]) -> List[Document]:
        """分割大章节"""
        chunks = []
        
        # 按段落分割
        paragraphs = self._split_classical_paragraphs(content)
        
        for i, para in enumerate(paragraphs):
            if para.strip() and len(para.strip()) > 50:  # 过滤太短的段落
                doc = Document(
                    page_content=para.strip(),
                    metadata={
                        "content_type": "章节段落",
                        "block_type": "chapter_paragraph",
                        "volume_title": volume["title"],
                        "volume_index": volume["volume_index"],
                        "chapter_title": chapter["title"],
                        "chapter_index": self._extract_chapter_index(chapter["title"]),
                        "paragraph_index": i + 1,
                        "language_style": "文言文",
                        "era": "清代"
                    }
                )
                chunks.append(doc)
                
        return chunks

    def _split_classical_paragraphs(self, text: str) -> List[str]:
        """专门针对文言文的分割方法"""
        # 文言文分割点
        separators = ['\n\n', '。', '！', '？', '；', '\n']
        
        paragraphs = []
        current_para = ""
        
        for char in text:
            current_para += char
            if char in separators:
                if current_para.strip():
                    # 检查是否包含完整的语义单元
                    if self._is_semantic_unit(current_para):
                        paragraphs.append(current_para.strip())
                        current_para = ""
        
        # 处理最后一段
        if current_para.strip():
            paragraphs.append(current_para.strip())
            
        # 合并过短的段落
        merged_paragraphs = []
        temp_para = ""
        
        for para in paragraphs:
            if len(temp_para + para) < 800:  # 合并阈值
                temp_para += "\n" + para if temp_para else para
            else:
                if temp_para:
                    merged_paragraphs.append(temp_para)
                temp_para = para
                
        if temp_para:
            merged_paragraphs.append(temp_para)
            
        return merged_paragraphs

    def _is_semantic_unit(self, text: str) -> bool:
        """判断是否为完整的语义单元"""
        # 包含完整的句子结构
        if len(text) < 20:
            return False
            
        # 包含关键标点
        if not any(marker in text for marker in ['。', '！', '？', '；']):
            return False
            
        return True

    def _chinese_to_number(self, chinese_num: str) -> str:
        """中文数字转阿拉伯数字"""
        return self.chinese_numbers.get(chinese_num, chinese_num)

    def _extract_chapter_index(self, title: str) -> str:
        """从章节标题中提取章节编号"""
        # 匹配 "一、八卦章" 这种格式
        match = re.match(r'^([一二三四五六七八九十])、', title)
        if match:
            return self._chinese_to_number(match.group(1))
            
        # 匹配其他编号格式
        for pattern in [r'^（([一二三四五六七八九十])）', r'^([0-9]+)\.']:
            match = re.match(pattern, title)
            if match:
                return match.group(1)
                
        return "未知"