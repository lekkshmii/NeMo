import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from pathlib import Path

from ingestion.document_processor import DocumentProcessor
from extraction.financial_extractor import FinancialExtractor
from embeddings.vector_store import VectorStore
from utils.financial_utils import clean_financial_value, calculate_financial_ratios

class TestDocumentProcessor(unittest.TestCase):
    
    def setUp(self):
        self.processor = DocumentProcessor()
    
    def test_chunk_text(self):
        text_blocks = [
            {'content': 'This is a test document with financial information.', 'page': 1, 'type': 'text'}
        ]
        
        chunks = self.processor.chunk_text(text_blocks, chunk_size=20, overlap=5)
        
        self.assertGreater(len(chunks), 0)
        self.assertIn('chunk_text', chunks[0])
        self.assertIn('chunk_id', chunks[0])

class TestFinancialExtractor(unittest.TestCase):
    
    def setUp(self):
        self.extractor = FinancialExtractor()
    
    def test_numerical_metrics_extraction(self):
        test_text = "Total revenue was $100.5 million for the year. Net income reached $25.3 million."
        
        metrics = self.extractor._extract_numerical_metrics(test_text)
        
        self.assertIn('revenue', metrics)
        self.assertIn('net_income', metrics)
        
        if metrics['revenue']:
            self.assertAlmostEqual(metrics['revenue'][0]['value'], 100500000, places=-3)

class TestFinancialUtils(unittest.TestCase):
    
    def test_clean_financial_value(self):
        test_cases = [
            ("$100.5 million", 100.5),
            ("(25.3)", -25.3),
            ("1,234.56", 1234.56),
            ("invalid", None)
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = clean_financial_value(input_val)
                if expected is None:
                    self.assertIsNone(result)
                else:
                    self.assertAlmostEqual(result, expected, places=1)
    
    def test_calculate_financial_ratios(self):
        metrics = {
            'revenue': 1000000,
            'net_income': 100000,
            'total_assets': 500000,
            'total_debt': 200000
        }
        
        ratios = calculate_financial_ratios(metrics)
        
        self.assertIn('profit_margin', ratios)
        self.assertIn('roa', ratios)
        self.assertIn('debt_ratio', ratios)
        
        self.assertAlmostEqual(ratios['profit_margin'], 0.1, places=2)
        self.assertAlmostEqual(ratios['roa'], 0.2, places=2)
        self.assertAlmostEqual(ratios['debt_ratio'], 0.4, places=2)

class TestIntegration(unittest.TestCase):
    
    @patch('src.embeddings.vector_store.chromadb')
    def setUp(self, mock_chromadb):
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_client.create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client
        
        self.vector_store = VectorStore()
        self.processor = DocumentProcessor()
        self.extractor = FinancialExtractor()
    
    def test_end_to_end_processing(self):
        sample_document_data = {
            'text_content': [
                {
                    'content': 'Revenue for Q4 2023 was $50 billion, an increase of 15% year-over-year.',
                    'page': 1,
                    'type': 'text'
                }
            ],
            'tables': [],
            'images': [],
            'metadata': {'title': 'Test Financial Report'}
        }
        
        financial_metrics = self.extractor.extract_financial_metrics(
            sample_document_data['text_content']
        )
        
        self.assertIn('financial_data', financial_metrics)
        self.assertIn('sentiment_analysis', financial_metrics)
        
        doc_id = self.vector_store.add_document(sample_document_data)
        self.assertIsNotNone(doc_id)

class TestErrorHandling(unittest.TestCase):
    
    def test_invalid_document_processing(self):
        processor = DocumentProcessor()
        
        with self.assertRaises(ValueError):
            processor.process_document("nonexistent_file.pdf")
    
    def test_empty_metrics_extraction(self):
        extractor = FinancialExtractor()
        
        empty_content = []
        metrics = extractor.extract_financial_metrics(empty_content)
        
        self.assertIsInstance(metrics, dict)
        self.assertIn('financial_data', metrics)

def run_performance_tests():
    print("🚀 Running Performance Tests...")
    
    import time
    
    processor = DocumentProcessor()
    extractor = FinancialExtractor()
    
    sample_text = "Revenue was $100 million. " * 1000
    sample_blocks = [
        {'content': sample_text, 'page': 1, 'type': 'text'}
    ]
    
    start_time = time.time()
    chunks = processor.chunk_text(sample_blocks)
    chunk_time = time.time() - start_time
    print(f"  ✅ Text chunking: {chunk_time:.3f}s for {len(chunks)} chunks")
    
    start_time = time.time()
    metrics = extractor.extract_financial_metrics(sample_blocks[:100])
    extract_time = time.time() - start_time
    print(f"  ✅ Metrics extraction: {extract_time:.3f}s")
    
    print(f"  📊 Processing rate: ~{len(sample_blocks)/extract_time:.1f} blocks/second")

if __name__ == '__main__':
    print("🧪 Running NeMo Test Suite...\n")
    
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "="*50)
    run_performance_tests()
    print("\n✅ All tests completed!")
