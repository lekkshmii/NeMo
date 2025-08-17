#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

from data_sources.sec_api import SECDataSource
from ingestion.document_processor import DocumentProcessor
from extraction.financial_extractor import FinancialExtractor
from embeddings.vector_store import VectorStore
from reasoning.query_engine import QueryEngine
from utils.financial_utils import create_financial_summary, compare_financial_metrics

class CompetitiveAnalyzer:
    def __init__(self):
        self.sec_api = SECDataSource()
        self.processor = DocumentProcessor()
        self.extractor = FinancialExtractor()
        self.vector_store = VectorStore(persist_directory="./data/competitive_analysis")
        self.query_engine = QueryEngine()
        
    def analyze_companies(self, tickers: List[str], form_type: str = "10-K") -> Dict[str, Any]:
        print(f"🔍 Starting competitive analysis for: {', '.join(tickers)}")
        
        company_data = {}
        
        for ticker in tickers:
            print(f"\n📊 Analyzing {ticker}...")
            
            company_info = self.sec_api.get_company_info_by_ticker(ticker)
            if not company_info:
                print(f"  ❌ Could not find company info for {ticker}")
                continue
                
            print(f"  ✅ Found {company_info['name']} (CIK: {company_info['cik']})")
            
            filings = self.sec_api.get_company_filings(
                company_info['cik'], [form_type], limit=1
            )
            
            if not filings:
                print(f"  ❌ No {form_type} filings found for {ticker}")
                continue
                
            latest_filing = filings[0]
            print(f"  📄 Processing {form_type} from {latest_filing['filing_date']}")
            
            company_metrics = self._process_filing(ticker, latest_filing)
            
            if company_metrics:
                company_data[ticker] = {
                    'company_info': company_info,
                    'filing_info': latest_filing,
                    'financial_metrics': company_metrics,
                    'summary': create_financial_summary(company_metrics)
                }
                print(f"  ✅ {ticker} analysis complete")
            else:
                print(f"  ❌ Failed to process {ticker}")
        
        return self._generate_competitive_report(company_data)
    
    def _process_filing(self, ticker: str, filing_info: Dict[str, Any]) -> Dict[str, Any]:
        try:
            filing_content = self.sec_api.download_filing(filing_info['filing_url'])
            
            if not filing_content:
                return None
                
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp_file:
                tmp_file.write(filing_content)
                tmp_file_path = tmp_file.name
            
            try:
                document_data = self.processor.process_document(tmp_file_path)
                financial_metrics = self.extractor.extract_financial_metrics(
                    document_data['text_content']
                )
                
                doc_id = f"{ticker}_{filing_info['accession_number']}"
                self.vector_store.add_document(document_data, doc_id)
                
                return financial_metrics
                
            finally:
                os.unlink(tmp_file_path)
                
        except Exception as e:
            print(f"    Error processing {ticker}: {e}")
            return None
    
    def _generate_competitive_report(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        print("\n📊 Generating competitive analysis report...")
        
        if not company_data:
            return {"error": "No company data available for analysis"}
        
        metrics_comparison = {}
        for ticker, data in company_data.items():
            metrics_comparison[ticker] = data['financial_metrics']
        
        comparison_df = compare_financial_metrics(metrics_comparison)
        
        key_insights = self._generate_insights(company_data, comparison_df)
        
        report = {
            'analysis_date': datetime.now().isoformat(),
            'companies_analyzed': list(company_data.keys()),
            'company_data': company_data,
            'financial_comparison': comparison_df.to_dict('records'),
            'key_insights': key_insights,
            'data_quality': self._assess_data_quality(company_data)
        }
        
        return report
    
    def _generate_insights(self, company_data: Dict[str, Any], 
                          comparison_df: pd.DataFrame) -> List[str]:
        insights = []
        
        if comparison_df.empty:
            return ["Insufficient data for meaningful insights"]
        
        revenue_cols = [col for col in comparison_df.columns if 'revenue_value' in col]
        if revenue_cols:
            revenue_col = revenue_cols[0]
            top_revenue = comparison_df.nlargest(1, revenue_col)
            if not top_revenue.empty:
                leader = top_revenue.iloc[0]['Company']
                revenue = top_revenue.iloc[0][revenue_col]
                insights.append(f"{leader} leads in revenue with ${revenue/1e9:.1f}B")
        
        margin_cols = [col for col in comparison_df.columns if 'profit_margin' in col]
        if margin_cols:
            margin_col = margin_cols[0]
            top_margin = comparison_df.nlargest(1, margin_col)
            if not top_margin.empty:
                leader = top_margin.iloc[0]['Company']
                margin = top_margin.iloc[0][margin_col]
                insights.append(f"{leader} has highest profit margin at {margin:.1%}")
        
        debt_cols = [col for col in comparison_df.columns if 'debt_ratio' in col]
        if debt_cols:
            debt_col = debt_cols[0]
            lowest_debt = comparison_df.nsmallest(1, debt_col)
            if not lowest_debt.empty:
                leader = lowest_debt.iloc[0]['Company']
                debt_ratio = lowest_debt.iloc[0][debt_col]
                insights.append(f"{leader} has lowest debt ratio at {debt_ratio:.1%}")
        
        return insights
    
    def _assess_data_quality(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        quality_scores = []
        
        for ticker, data in company_data.items():
            summary = data.get('summary', {})
            data_quality = summary.get('data_quality', {})
            quality_score = data_quality.get('data_quality_score', 0)
            quality_scores.append(quality_score)
        
        return {
            'avg_quality_score': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            'companies_with_high_quality': sum(1 for score in quality_scores if score > 0.7),
            'total_companies': len(quality_scores),
            'recommendation': 'Good' if sum(quality_scores) / len(quality_scores) > 0.6 else 'Review needed'
        }
    
    def ask_comparative_question(self, question: str, companies: List[str] = None) -> Dict[str, Any]:
        print(f"\n🤖 Answering: {question}")
        
        search_results = self.vector_store.search(question, n_results=10)
        
        response = self.query_engine.answer_query(
            question, search_results, model_preference="local"
        )
        
        relevant_companies = []
        for citation in response.get('citations', []):
            doc_id = citation.get('metadata', {}).get('document_id', '')
            if '_' in doc_id:
                ticker = doc_id.split('_')[0]
                if ticker not in relevant_companies:
                    relevant_companies.append(ticker)
        
        return {
            'question': question,
            'answer': response['response'],
            'relevant_companies': relevant_companies,
            'citations': response['citations'],
            'confidence': len(response['citations']) / 10
        }

def main():
    print("🏢 NeMo Competitive Analysis Demo")
    print("="*50)
    
    analyzer = CompetitiveAnalyzer()
    
    tech_companies = ["AAPL", "MSFT", "GOOGL"]
    
    print(f"\n🎯 Analyzing top tech companies: {', '.join(tech_companies)}")
    
    analysis_report = analyzer.analyze_companies(tech_companies)
    
    if 'error' in analysis_report:
        print(f"❌ Analysis failed: {analysis_report['error']}")
        return
    
    print("\n📊 Analysis Results:")
    print(f"Companies analyzed: {len(analysis_report['companies_analyzed'])}")
    print(f"Data quality: {analysis_report['data_quality']['recommendation']}")
    
    print("\n💡 Key Insights:")
    for insight in analysis_report['key_insights']:
        print(f"  • {insight}")
    
    if analysis_report.get('financial_comparison'):
        print("\n📈 Financial Comparison:")
        comparison_df = pd.DataFrame(analysis_report['financial_comparison'])
        if not comparison_df.empty:
            print(comparison_df[['Company'] + [col for col in comparison_df.columns if 'formatted' in col][:3]])
    
    print("\n🤖 Interactive Q&A:")
    questions = [
        "Which company has the highest revenue growth?",
        "What are the main risk factors across these companies?",
        "How do R&D investments compare between these companies?"
    ]
    
    for question in questions:
        qa_result = analyzer.ask_comparative_question(question)
        print(f"\nQ: {question}")
        print(f"A: {qa_result['answer'][:200]}...")
        print(f"Relevant companies: {', '.join(qa_result['relevant_companies'])}")
        print(f"Confidence: {qa_result['confidence']:.1%}")
    
    print("\n✅ Competitive analysis complete!")
    print(f"📁 Results saved to vector database for future queries")

if __name__ == "__main__":
    main()
