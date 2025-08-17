import fitz
import pdfplumber
import camelot
from PIL import Image
import pandas as pd
from typing import Dict, List, Any, Optional
import base64
import io
import logging
from pathlib import Path

class DocumentProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def process_document(self, file_path: str) -> Dict[str, Any]:
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.pdf':
            return self._process_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
    
    def _process_pdf(self, file_path: Path) -> Dict[str, Any]:
        doc_data = {
            "file_path": str(file_path),
            "text_content": [],
            "tables": [],
            "images": [],
            "metadata": {}
        }
        
        try:
            doc_data["text_content"] = self._extract_text_pymupdf(file_path)
            doc_data["tables"] = self._extract_tables_camelot(file_path)
            doc_data["images"] = self._extract_images_pymupdf(file_path)
            doc_data["metadata"] = self._extract_metadata_pymupdf(file_path)
            
        except Exception as e:
            self.logger.error(f"Error processing PDF {file_path}: {e}")
            
        return doc_data
    
    def _extract_text_pymupdf(self, file_path: Path) -> List[Dict[str, Any]]:
        text_blocks = []
        
        try:
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if "lines" in block:
                        text_content = ""
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text_content += span["text"] + " "
                        
                        if text_content.strip():
                            text_blocks.append({
                                "page": page_num + 1,
                                "content": text_content.strip(),
                                "bbox": block["bbox"],
                                "type": "text"
                            })
            
            doc.close()
            
        except Exception as e:
            self.logger.error(f"Error extracting text: {e}")
            
        return text_blocks
    
    def _extract_tables_camelot(self, file_path: Path) -> List[Dict[str, Any]]:
        tables_data = []
        
        try:
            tables = camelot.read_pdf(str(file_path), pages='all', flavor='lattice')
            
            for i, table in enumerate(tables):
                if not table.df.empty:
                    tables_data.append({
                        "table_id": i,
                        "page": table.page,
                        "data": table.df.to_dict('records'),
                        "raw_data": table.df,
                        "accuracy": table.accuracy,
                        "type": "table"
                    })
                    
        except Exception as e:
            self.logger.warning(f"Camelot table extraction failed: {e}")
            try:
                tables_data = self._extract_tables_pdfplumber(file_path)
            except Exception as e2:
                self.logger.error(f"Pdfplumber table extraction also failed: {e2}")
                
        return tables_data
    
    def _extract_tables_pdfplumber(self, file_path: Path) -> List[Dict[str, Any]]:
        tables_data = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                
                for i, table in enumerate(tables):
                    if table:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        tables_data.append({
                            "table_id": f"{page_num}_{i}",
                            "page": page_num + 1,
                            "data": df.to_dict('records'),
                            "raw_data": df,
                            "type": "table"
                        })
                        
        return tables_data
    
    def _extract_images_pymupdf(self, file_path: Path) -> List[Dict[str, Any]]:
        images_data = []
        
        try:
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha < 4:
                        img_data = pix.tobytes("png")
                        img_base64 = base64.b64encode(img_data).decode()
                        
                        images_data.append({
                            "image_id": f"page_{page_num+1}_img_{img_index}",
                            "page": page_num + 1,
                            "base64": img_base64,
                            "format": "png",
                            "size": (pix.width, pix.height),
                            "type": "image"
                        })
                    
                    pix = None
                    
            doc.close()
            
        except Exception as e:
            self.logger.error(f"Error extracting images: {e}")
            
        return images_data
    
    def _extract_metadata_pymupdf(self, file_path: Path) -> Dict[str, Any]:
        metadata = {}
        
        try:
            doc = fitz.open(file_path)
            metadata = doc.metadata
            metadata["page_count"] = len(doc)
            doc.close()
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {e}")
            
        return metadata
    
    def chunk_text(self, text_blocks: List[Dict[str, Any]], 
                   chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        chunks = []
        
        for block in text_blocks:
            content = block["content"]
            
            if len(content) <= chunk_size:
                chunks.append({
                    **block,
                    "chunk_id": len(chunks),
                    "chunk_text": content
                })
            else:
                words = content.split()
                current_chunk = []
                current_length = 0
                
                for word in words:
                    if current_length + len(word) + 1 > chunk_size and current_chunk:
                        chunk_text = " ".join(current_chunk)
                        chunks.append({
                            **block,
                            "chunk_id": len(chunks),
                            "chunk_text": chunk_text
                        })
                        
                        overlap_words = current_chunk[-overlap//10:] if overlap > 0 else []
                        current_chunk = overlap_words + [word]
                        current_length = sum(len(w) for w in current_chunk) + len(current_chunk)
                    else:
                        current_chunk.append(word)
                        current_length += len(word) + 1
                
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunks.append({
                        **block,
                        "chunk_id": len(chunks),
                        "chunk_text": chunk_text
                    })
        
        return chunks
