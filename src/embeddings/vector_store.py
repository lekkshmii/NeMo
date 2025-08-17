import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any, Optional
import logging
import json
import uuid
from pathlib import Path

class VectorStore:
    def __init__(self, persist_directory: str = "./data/chroma_db", 
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.logger = logging.getLogger(__name__)
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.embedding_model = SentenceTransformer(embedding_model)
        
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.text_collection = self._get_or_create_collection("financial_documents_text")
        self.table_collection = self._get_or_create_collection("financial_documents_tables")
        self.metadata_collection = self._get_or_create_collection("financial_documents_metadata")
        
    def _get_or_create_collection(self, name: str):
        try:
            return self.client.get_collection(name)
        except:
            return self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
    
    def add_document(self, document_data: Dict[str, Any], document_id: str = None) -> str:
        if not document_id:
            document_id = str(uuid.uuid4())
            
        try:
            self._add_text_chunks(document_data.get('text_content', []), document_id)
            self._add_tables(document_data.get('tables', []), document_id)
            self._add_metadata(document_data.get('metadata', {}), document_id)
            
            self.logger.info(f"Successfully added document {document_id}")
            return document_id
            
        except Exception as e:
            self.logger.error(f"Error adding document {document_id}: {e}")
            raise
    
    def _add_text_chunks(self, text_chunks: List[Dict[str, Any]], document_id: str):
        if not text_chunks:
            return
            
        texts = []
        metadatas = []
        ids = []
        
        for chunk in text_chunks:
            chunk_text = chunk.get('chunk_text') or chunk.get('content', '')
            
            if len(chunk_text.strip()) < 10:
                continue
                
            texts.append(chunk_text)
            
            metadata = {
                'document_id': document_id,
                'chunk_id': chunk.get('chunk_id', 0),
                'page': chunk.get('page', 0),
                'type': 'text',
                'bbox': json.dumps(chunk.get('bbox', [])) if chunk.get('bbox') else None
            }
            metadatas.append(metadata)
            
            chunk_id = f"{document_id}_text_{chunk.get('chunk_id', len(ids))}"
            ids.append(chunk_id)
        
        if texts:
            embeddings = self.embedding_model.encode(texts).tolist()
            
            self.text_collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
    
    def _add_tables(self, tables: List[Dict[str, Any]], document_id: str):
        if not tables:
            return
            
        texts = []
        metadatas = []
        ids = []
        
        for table in tables:
            table_data = table.get('data', [])
            
            if not table_data:
                continue
                
            table_text = self._table_to_text(table_data)
            
            if len(table_text.strip()) < 20:
                continue
                
            texts.append(table_text)
            
            metadata = {
                'document_id': document_id,
                'table_id': table.get('table_id', ''),
                'page': table.get('page', 0),
                'type': 'table',
                'accuracy': table.get('accuracy', 0),
                'row_count': len(table_data),
                'col_count': len(table_data[0]) if table_data else 0
            }
            metadatas.append(metadata)
            
            table_id = f"{document_id}_table_{table.get('table_id', len(ids))}"
            ids.append(table_id)
        
        if texts:
            embeddings = self.embedding_model.encode(texts).tolist()
            
            self.table_collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
    
    def _table_to_text(self, table_data: List[Dict[str, Any]]) -> str:
        if not table_data:
            return ""
            
        text_parts = []
        
        if table_data:
            headers = list(table_data[0].keys())
            text_parts.append("Table columns: " + ", ".join(headers))
            
            for i, row in enumerate(table_data[:5]):
                row_text = []
                for key, value in row.items():
                    if value is not None and str(value).strip():
                        row_text.append(f"{key}: {value}")
                
                if row_text:
                    text_parts.append(f"Row {i+1}: " + ", ".join(row_text))
        
        return "\n".join(text_parts)
    
    def _add_metadata(self, metadata: Dict[str, Any], document_id: str):
        if not metadata:
            return
            
        metadata_text = json.dumps(metadata, indent=2)
        
        embedding = self.embedding_model.encode([metadata_text]).tolist()[0]
        
        metadata_entry = {
            'document_id': document_id,
            'type': 'metadata',
            **metadata
        }
        
        self.metadata_collection.add(
            embeddings=[embedding],
            documents=[metadata_text],
            metadatas=[metadata_entry],
            ids=[f"{document_id}_metadata"]
        )
    
    def search(self, query: str, n_results: int = 10, 
               search_type: str = "all") -> List[Dict[str, Any]]:
        
        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        
        results = {
            'text_results': [],
            'table_results': [],
            'metadata_results': []
        }
        
        try:
            if search_type in ["all", "text"]:
                text_results = self.text_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results
                )
                results['text_results'] = self._format_results(text_results)
            
            if search_type in ["all", "table"]:
                table_results = self.table_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(n_results, 5)
                )
                results['table_results'] = self._format_results(table_results)
            
            if search_type in ["all", "metadata"]:
                metadata_results = self.metadata_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(n_results, 3)
                )
                results['metadata_results'] = self._format_results(metadata_results)
                
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            
        return results
    
    def _format_results(self, raw_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        formatted = []
        
        if not raw_results.get('documents'):
            return formatted
            
        documents = raw_results['documents'][0]
        metadatas = raw_results.get('metadatas', [[]])[0]
        distances = raw_results.get('distances', [[]])[0]
        ids = raw_results.get('ids', [[]])[0]
        
        for i, doc in enumerate(documents):
            formatted.append({
                'id': ids[i] if i < len(ids) else f"result_{i}",
                'content': doc,
                'metadata': metadatas[i] if i < len(metadatas) else {},
                'distance': distances[i] if i < len(distances) else 1.0,
                'relevance_score': 1 - distances[i] if i < len(distances) else 0.0
            })
            
        return formatted
    
    def get_document_chunks(self, document_id: str) -> Dict[str, List[Dict[str, Any]]]:
        results = {
            'text_chunks': [],
            'tables': [],
            'metadata': None
        }
        
        try:
            text_results = self.text_collection.get(
                where={"document_id": document_id}
            )
            results['text_chunks'] = self._format_results({
                'documents': [text_results['documents']],
                'metadatas': [text_results['metadatas']],
                'ids': [text_results['ids']]
            })
            
            table_results = self.table_collection.get(
                where={"document_id": document_id}
            )
            results['tables'] = self._format_results({
                'documents': [table_results['documents']],
                'metadatas': [table_results['metadatas']],
                'ids': [table_results['ids']]
            })
            
            metadata_results = self.metadata_collection.get(
                where={"document_id": document_id}
            )
            if metadata_results['documents']:
                results['metadata'] = json.loads(metadata_results['documents'][0])
                
        except Exception as e:
            self.logger.error(f"Error retrieving document chunks: {e}")
            
        return results
    
    def delete_document(self, document_id: str):
        try:
            self.text_collection.delete(where={"document_id": document_id})
            self.table_collection.delete(where={"document_id": document_id})
            self.metadata_collection.delete(where={"document_id": document_id})
            
            self.logger.info(f"Deleted document {document_id}")
            
        except Exception as e:
            self.logger.error(f"Error deleting document {document_id}: {e}")
    
    def list_documents(self) -> List[str]:
        try:
            metadata_results = self.metadata_collection.get()
            document_ids = [
                metadata.get('document_id') 
                for metadata in metadata_results.get('metadatas', [])
                if metadata.get('document_id')
            ]
            return list(set(document_ids))
            
        except Exception as e:
            self.logger.error(f"Error listing documents: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        try:
            return {
                'text_count': self.text_collection.count(),
                'table_count': self.table_collection.count(),
                'metadata_count': self.metadata_collection.count(),
                'total_documents': len(self.list_documents())
            }
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {}
