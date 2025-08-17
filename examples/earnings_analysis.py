#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
import re

from data_sources.sec_api import SECDataSource
from extraction.financial_extractor import FinancialExtractor
from embeddings.vector_store import VectorStore
from reasoning.query_engine import QueryEngine

class EarningsCallAnalyzer:
    def __init__(self):
        self.sec_api = SECDataSource()
        self.extractor = FinancialExtractor()
        self.vector_store = VectorStore(persist_directory="./data/earnings_analysis")
        self.query_engine = QueryEngine()
        
        self.earnings_keywords = [
            'earnings', 'quarterly results', 'financial results',
            'conference call', 'q1', 'q2', 'q3', 'q4',
            'guidance', 'outlook', 'forecast'
        ]
        
    def find_recent_earnings(self, ticker: str, days_back: int = 30) -> List[Dict[str, Any]]:
        print(f"🔍 Looking for recent earnings filings for {ticker}...")
        
        company_info = self.sec_api.get_company_info_by_ticker(ticker)
        if not company_info:
            print(f"❌ Company {ticker} not found")
            return []
            
        recent_8ks = self.sec_api.get_company_filings(
            company_info['cik'], ['8-K'], limit=20
        )
        
        earnings_filings = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        for filing in recent_8ks:
            filing_date = datetime.strptime(filing['filing_date'], '%Y-%m-%d')
            
            if filing_date < cutoff_date:
                continue
                
            if self._is_earnings_related(filing):
                earnings_filings.append({
                    **filing,
                    'company_info': company_info,
                    'relevance_score': self._calculate_earnings_relevance(filing)
                })
        
        earnings_filings.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        print(f"📊 Found {len(earnings_filings)} earnings-related filings")
        return earnings_filings
    
    def _is_earnings_related(self, filing: Dict[str, Any]) -> bool:
        filing_content = self.sec_api.download_filing(filing['filing_url'])
        
        if not filing_content:
            return False
            
        content_lower = filing_content.lower()
        
        keyword_count = sum(1 for keyword in self.earnings_keywords 
                           if keyword in content_lower)
        
        return keyword_count >= 2
    
    def _calculate_earnings_relevance(self, filing: Dict[str, Any]) -> float:
        filing_content = self.sec_api.download_filing(filing['filing_url'])
        
        if not filing_content:
            return 0.0
            
        content_lower = filing_content.lower()
        
        relevance_score = 0.0
        
        for keyword in self.earnings_keywords:
            count = content_lower.count(keyword)
            relevance_score += count * 0.1
        
        financial_terms = ['revenue', 'earnings', 'profit', 'loss', 'guidance', 'outlook']
        for term in financial_terms:
            count = content_lower.count(term)
            relevance_score += count * 0.05
        
        if 'item 2.02' in content_lower:
            relevance_score += 2.0
        
        if any(quarter in content_lower for quarter in ['q1', 'q2', 'q3', 'q4', 'quarter']):
            relevance_score += 1.0
        
        return min(relevance_score, 10.0)
    
    def analyze_earnings_sentiment(self, earnings_filings: List[Dict[str, Any]]) -> Dict[str, Any]:
        print("📈 Analyzing earnings sentiment...")
        
        sentiment_analysis = {
            'filings_analyzed': len(earnings_filings),
            'individual_sentiments': [],
            'overall_sentiment': {},
            'key_themes': [],
            'financial_highlights': []
        }
        
        all_content = []
        
        for filing in earnings_filings:
            filing_content = self.sec_api.download_filing(filing['filing_url'])
            
            if filing_content:
                sentiment_result = self._analyze_filing_sentiment(filing_content)
                
                sentiment_analysis['individual_sentiments'].append({
                    'filing_date': filing['filing_date'],
                    'accession_number': filing['accession_number'],
                    'sentiment': sentiment_result
                })
                
                all_content.append(filing_content)
                
                financial_highlights = self._extract_financial_highlights(filing_content)
                sentiment_analysis['financial_highlights'].extend(financial_highlights)
        
        if sentiment_analysis['individual_sentiments']:
            sentiment_analysis['overall_sentiment'] = self._calculate_overall_sentiment(
                sentiment_analysis['individual_sentiments']
            )
            
            sentiment_analysis['key_themes'] = self._extract_key_themes(all_content)
        
        return sentiment_analysis
    
    def _analyze_filing_sentiment(self, content: str) -> Dict[str, Any]:
        positive_words = [
            'growth', 'increase', 'strong', 'robust', 'excellent', 'outstanding',
            'record', 'beat', 'exceeded', 'optimistic', 'confident', 'solid'
        ]
        
        negative_words = [
            'decline', 'decrease', 'weak', 'challenging', 'difficult', 'concerns',
            'missed', 'below', 'disappointing', 'uncertainty', 'headwinds', 'risks'
        ]
        
        content_lower = content.lower()
        
        positive_count = sum(content_lower.count(word) for word in positive_words)
        negative_count = sum(content_lower.count(word) for word in negative_words)
        
        total_words = len(content.split())
        
        sentiment_score = (positive_count - negative_count) / max(total_words / 1000, 1)
        
        if sentiment_score > 0.5:
            sentiment_label = 'positive'
        elif sentiment_score < -0.5:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        return {
            'sentiment_score': sentiment_score,
            'sentiment_label': sentiment_label,
            'positive_mentions': positive_count,
            'negative_mentions': negative_count,
            'confidence': min(abs(sentiment_score) * 2, 1.0)
        }
    
    def _calculate_overall_sentiment(self, individual_sentiments: List[Dict[str, Any]]) -> Dict[str, Any]:
        sentiment_scores = [s['sentiment']['sentiment_score'] for s in individual_sentiments]
        sentiment_labels = [s['sentiment']['sentiment_label'] for s in individual_sentiments]
        
        avg_score = sum(sentiment_scores) / len(sentiment_scores)
        
        label_counts = {}
        for label in sentiment_labels:
            label_counts[label] = label_counts.get(label, 0) + 1
        
        dominant_sentiment = max(label_counts.keys(), key=lambda k: label_counts[k])
        
        return {
            'average_sentiment_score': avg_score,
            'dominant_sentiment': dominant_sentiment,
            'sentiment_distribution': label_counts,
            'sentiment_trend': 'improving' if sentiment_scores[-1] > sentiment_scores[0] else 'declining'
        }
    
    def _extract_financial_highlights(self, content: str) -> List[str]:
        highlights = []
        
        revenue_pattern = r'revenue[^.]*\$[\d,.]+ (?:million|billion)'
        revenue_matches = re.findall(revenue_pattern, content, re.IGNORECASE)
        highlights.extend(revenue_matches[:3])
        
        earnings_pattern = r'(?:earnings|income)[^.]*\$[\d,.]+ (?:million|billion)'
        earnings_matches = re.findall(earnings_pattern, content, re.IGNORECASE)
        highlights.extend(earnings_matches[:3])
        
        growth_pattern = r'(?:increased|grew|growth)[^.]*\d+%'
        growth_matches = re.findall(growth_pattern, content, re.IGNORECASE)
        highlights.extend(growth_matches[:3])
        
        return highlights[:10]
    
    def _extract_key_themes(self, all_content: List[str]) -> List[str]:
        combined_content = ' '.join(all_content).lower()
        
        theme_keywords = {
            'digital_transformation': ['digital', 'cloud', 'ai', 'artificial intelligence', 'automation'],
            'supply_chain': ['supply chain', 'logistics', 'inventory', 'suppliers'],
            'market_expansion': ['expansion', 'new markets', 'international', 'global'],
            'innovation': ['innovation', 'r&d', 'research', 'development', 'new products'],
            'sustainability': ['sustainability', 'esg', 'environment', 'green', 'renewable'],
            'cost_management': ['cost', 'efficiency', 'savings', 'optimization']
        }
        
        theme_scores = {}
        for theme, keywords in theme_keywords.items():
            score = sum(combined_content.count(keyword) for keyword in keywords)
            if score > 0:
                theme_scores[theme] = score
        
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        
        return [theme.replace('_', ' ').title() for theme, score in sorted_themes[:5]]
    
    def generate_earnings_report(self, ticker: str, days_back: int = 30) -> Dict[str, Any]:
        print(f"📊 Generating earnings analysis report for {ticker}...")
        
        earnings_filings = self.find_recent_earnings(ticker, days_back)
        
        if not earnings_filings:
            return {
                'error': f'No recent earnings filings found for {ticker}',
                'ticker': ticker,
                'analysis_date': datetime.now().isoformat()
            }
        
        sentiment_analysis = self.analyze_earnings_sentiment(earnings_filings)
        
        report = {
            'ticker': ticker,
            'analysis_date': datetime.now().isoformat(),
            'analysis_period_days': days_back,
            'earnings_filings': earnings_filings,
            'sentiment_analysis': sentiment_analysis,
            'summary': self._create_summary(ticker, sentiment_analysis)
        }
        
        return report
    
    def _create_summary(self, ticker: str, sentiment_analysis: Dict[str, Any]) -> Dict[str, Any]:
        overall_sentiment = sentiment_analysis.get('overall_sentiment', {})
        
        summary = {
            'company': ticker,
            'filings_analyzed': sentiment_analysis['filings_analyzed'],
            'overall_sentiment': overall_sentiment.get('dominant_sentiment', 'neutral'),
            'sentiment_score': overall_sentiment.get('average_sentiment_score', 0),
            'key_themes': sentiment_analysis.get('key_themes', []),
            'recommendation': 'neutral'
        }
        
        sentiment_score = summary['sentiment_score']
        if sentiment_score > 0.5:
            summary['recommendation'] = 'positive outlook'
        elif sentiment_score < -0.5:
            summary['recommendation'] = 'cautious outlook'
        
        return summary

def main():
    print("📞 NeMo Earnings Call Analysis Demo")
    print("="*50)
    
    analyzer = EarningsCallAnalyzer()
    
    test_companies = ["AAPL", "MSFT"]
    
    for ticker in test_companies:
        print(f"\n🎯 Analyzing recent earnings for {ticker}")
        
        report = analyzer.generate_earnings_report(ticker, days_back=60)
        
        if 'error' in report:
            print(f"❌ {report['error']}")
            continue
        
        summary = report['summary']
        sentiment = report['sentiment_analysis']
        
        print(f"\n📊 {ticker} Earnings Analysis Summary:")
        print(f"  Filings analyzed: {summary['filings_analyzed']}")
        print(f"  Overall sentiment: {summary['overall_sentiment']}")
        print(f"  Sentiment score: {summary['sentiment_score']:.2f}")
        print(f"  Recommendation: {summary['recommendation']}")
        
        if summary['key_themes']:
            print(f"  Key themes: {', '.join(summary['key_themes'])}")
        
        if sentiment['financial_highlights']:
            print(f"\n💰 Financial Highlights:")
            for highlight in sentiment['financial_highlights'][:3]:
                print(f"  • {highlight}")
        
        print(f"\n📈 Sentiment Trend: {sentiment['overall_sentiment'].get('sentiment_trend', 'stable')}")
    
    print("\n✅ Earnings analysis complete!")

if __name__ == "__main__":
    main()
