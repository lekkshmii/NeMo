from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import tempfile
import os
from pathlib import Path

from ..ingestion.document_processor import DocumentProcessor
from ..extraction.financial_extractor import FinancialExtractor
from ..embeddings.vector_store import VectorStore
from ..reasoning.query_engine import QueryEngine
from ..data_sources.sec_api import SECDataSource

app = FastAPI(title="NeMo Financial Research Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

doc_processor = DocumentProcessor()
financial_extractor = FinancialExtractor()
vector_store = VectorStore()
query_engine = QueryEngine()
sec_data_source = SECDataSource()

class QueryRequest(BaseModel):
    query: str
    model_preference: str = "claude"
    search_type: str = "all"

class CompanySearchRequest(BaseModel):
    company_identifier: str
    search_type: str = "ticker"

class FilingDownloadRequest(BaseModel):
    cik: str
    form_types: List[str] = ["10-K", "10-Q"]
    limit: int = 5

@app.get("/")
async def root():
    return {"message": "NeMo Financial Research Assistant API", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "components": {
            "vector_store": "operational",
            "query_engine": "operational",
            "sec_data_source": "operational"
        }
    }

@app.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
            
        document_data = doc_processor.process_document(tmp_file_path)
        
        financial_metrics = financial_extractor.extract_financial_metrics(
            document_data.get('text_content', [])
        )
        
        table_metrics = financial_extractor.extract_from_tables(
            document_data.get('tables', [])
        )
        
        document_data['financial_metrics'] = financial_metrics
        document_data['table_metrics'] = table_metrics
        
        document_id = vector_store.add_document(document_data)
        
        os.unlink(tmp_file_path)
        
        return {
            "document_id": document_id,
            "filename": file.filename,
            "pages_processed": len(document_data.get('text_content', [])),
            "tables_found": len(document_data.get('tables', [])),
            "images_found": len(document_data.get('images', [])),
            "financial_metrics": financial_metrics,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        if 'tmp_file_path' in locals():
            os.unlink(tmp_file_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_documents(request: QueryRequest):
    try:
        search_results = vector_store.search(
            request.query, 
            n_results=10,
            search_type=request.search_type
        )
        
        response = query_engine.answer_query(
            request.query,
            search_results,
            request.model_preference
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search-company")
async def search_company(request: CompanySearchRequest):
    try:
        if request.search_type == "ticker":
            company_info = sec_data_source.get_company_info_by_ticker(request.company_identifier)
        else:
            companies = sec_data_source.search_company(request.company_identifier)
            company_info = companies[0] if companies else None
            
        if not company_info:
            raise HTTPException(status_code=404, detail="Company not found")
            
        return company_info
        
    except Exception as e:
        logger.error(f"Company search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/download-filings")
async def download_filings(request: FilingDownloadRequest):
    try:
        filings = sec_data_source.get_company_filings(
            request.cik,
            request.form_types,
            request.limit
        )
        
        processed_filings = []
        
        for filing in filings:
            filing_content = sec_data_source.download_filing(filing['filing_url'])
            
            if filing_content:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp_file:
                    tmp_file.write(filing_content)
                    tmp_file_path = tmp_file.name
                
                try:
                    document_data = doc_processor.process_document(tmp_file_path)
                    
                    financial_metrics = financial_extractor.extract_financial_metrics(
                        document_data.get('text_content', [])
                    )
                    
                    document_data['financial_metrics'] = financial_metrics
                    document_data['sec_filing_info'] = filing
                    
                    document_id = vector_store.add_document(document_data, 
                                                          f"{request.cik}_{filing['accession_number']}")
                    
                    processed_filings.append({
                        "document_id": document_id,
                        "filing_info": filing,
                        "processing_status": "success",
                        "pages_processed": len(document_data.get('text_content', [])),
                        "financial_metrics_found": len(financial_metrics.get('financial_data', {}))
                    })
                    
                except Exception as processing_error:
                    logger.error(f"Error processing filing {filing['accession_number']}: {processing_error}")
                    processed_filings.append({
                        "filing_info": filing,
                        "processing_status": "error",
                        "error": str(processing_error)
                    })
                    
                finally:
                    os.unlink(tmp_file_path)
                    
        return {
            "cik": request.cik,
            "total_filings_requested": len(filings),
            "total_filings_processed": len(processed_filings),
            "filings": processed_filings
        }
        
    except Exception as e:
        logger.error(f"Filing download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents():
    try:
        documents = vector_store.list_documents()
        stats = vector_store.get_collection_stats()
        
        return {
            "documents": documents,
            "total_documents": len(documents),
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{document_id}")
async def get_document(document_id: str):
    try:
        document_chunks = vector_store.get_document_chunks(document_id)
        
        if not document_chunks['text_chunks'] and not document_chunks['tables']:
            raise HTTPException(status_code=404, detail="Document not found")
            
        return document_chunks
        
    except Exception as e:
        logger.error(f"Get document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    try:
        vector_store.delete_document(document_id)
        
        return {"message": f"Document {document_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-summary/{document_id}")
async def generate_summary(document_id: str, model_preference: str = "claude"):
    try:
        document_chunks = vector_store.get_document_chunks(document_id)
        
        if not document_chunks['text_chunks']:
            raise HTTPException(status_code=404, detail="Document not found")
            
        summary = query_engine.generate_summary(document_chunks, model_preference)
        
        return summary
        
    except Exception as e:
        logger.error(f"Generate summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sec/recent-filings")
async def get_recent_filings(form_type: str = "8-K", days_back: int = 7):
    try:
        recent_filings = sec_data_source.search_recent_filings(form_type, days_back)
        
        return {
            "form_type": form_type,
            "days_back": days_back,
            "total_filings": len(recent_filings),
            "filings": recent_filings
        }
        
    except Exception as e:
        logger.error(f"Recent filings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sec/financial-data/{cik}")
async def get_financial_data(cik: str, taxonomy: str = "us-gaap", tag: str = "Revenues"):
    try:
        financial_data = sec_data_source.get_financial_data(cik, taxonomy, tag)
        
        if not financial_data:
            raise HTTPException(status_code=404, detail="Financial data not found")
            
        return financial_data
        
    except Exception as e:
        logger.error(f"Financial data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def create_app():
    return app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
