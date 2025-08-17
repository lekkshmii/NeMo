import re
import pandas as pd
from typing import Dict, List, Any, Optional
import numpy as np
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import logging

class FinancialExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._load_models()
        self._compile_patterns()
        
    def _load_models(self):
        try:
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert"
            )
        except Exception as e:
            self.logger.warning(f"Could not load FinBERT: {e}")
            self.sentiment_analyzer = None
            
    def _compile_patterns(self):
        self.financial_patterns = {
            'revenue': [
                r'(?:total\s+)?(?:net\s+)?revenue[s]?\s*[\:\-]?\s*\$?\s*([\d,\.]+)\s*(?:million|billion|thousand)?',
                r'(?:net\s+)?sales\s*[\:\-]?\s*\$?\s*([\d,\.]+)\s*(?:million|billion|thousand)?',
                r'total\s+revenue\s*[\:\-]?\s*\$?\s*([\d,\.]+)\s*(?:million|billion|thousand)?'
            ],
            'net_income': [
                r'net\s+income\s*[\:\-]?\s*\$?\s*([\d,\.]+)\s*(?:million|billion|thousand)?',
                r'net\s+earnings\s*[\:\-]?\s*\$?\s*([\d,\.]+)\s*(?:million|billion|thousand)?',
                r'(?:net\s+)?profit\s*[\:\-]?\s*\$?\s*([\d,\.]+)\s*(?:million|billion|thousand)?'
            ],
            'eps': [
                r'earnings\s+per\s+share\s*[\:\-]?\s*\$?\s*([\d,\.]+)',
                r'basic\s+eps\s*[\:\-]?\s*\$?\s*([\d,\.]+)',
                r'diluted\s+eps\s*[\:\-]?\s*\$?\s*([\d,\.]+)'
            ],
            'total_assets': [
                r'total\s+assets\s*[\:\-]?\s*\$?\s*([\d,\.]+)\s*(?:million|billion|thousand)?'
            ],
            'debt': [
                r'total\s+debt\s*[\:\-]?\s*\$?\s*([\d,\.]+)\s*(?:million|billion|thousand)?',
                r'long[\-\s]term\s+debt\s*[\:\-]?\s*\$?\s*([\d,\.]+)\s*(?:million|billion|thousand)?'
            ],
            'cash': [
                r'cash\s+and\s+cash\s+equivalents\s*[\:\-]?\s*\$?\s*([\d,\.]+)\s*(?:million|billion|thousand)?',
                r'total\s+cash\s*[\:\-]?\s*\$?\s*([\d,\.]+)\s*(?:million|billion|thousand)?'
            ]
        }
        
        self.risk_patterns = [
            r'risk\s+factor[s]?',
            r'material\s+weakness',
            r'going\s+concern',
            r'litigation',
            r'regulatory\s+risk',
            r'market\s+risk',
            r'credit\s+risk',
            r'operational\s+risk',
            r'cybersecurity',
            r'data\s+breach'
        ]
        
    def extract_financial_metrics(self, text_content: List[Dict[str, Any]]) -> Dict[str, Any]:
        metrics = {
            'financial_data': {},
            'risk_factors': [],
            'sentiment_analysis': {},
            'key_sections': {}
        }
        
        combined_text = " ".join([block['content'] for block in text_content])
        
        metrics['financial_data'] = self._extract_numerical_metrics(combined_text)
        metrics['risk_factors'] = self._extract_risk_factors(combined_text)
        metrics['sentiment_analysis'] = self._analyze_sentiment(combined_text)
        metrics['key_sections'] = self._extract_key_sections(text_content)
        
        return metrics
    
    def _extract_numerical_metrics(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        financial_data = {}
        
        for metric_type, patterns in self.financial_patterns.items():
            financial_data[metric_type] = []
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    try:
                        raw_value = match.group(1)
                        
                        cleaned_value = re.sub(r'[^\d\.]', '', raw_value)
                        if cleaned_value:
                            numeric_value = float(cleaned_value)
                            
                            context = text[max(0, match.start()-100):match.end()+100]
                            
                            multiplier = 1
                            if 'billion' in context.lower():
                                multiplier = 1e9
                            elif 'million' in context.lower():
                                multiplier = 1e6
                            elif 'thousand' in context.lower():
                                multiplier = 1e3
                                
                            final_value = numeric_value * multiplier
                            
                            financial_data[metric_type].append({
                                'value': final_value,
                                'raw_text': match.group(0),
                                'context': context.strip(),
                                'confidence': self._calculate_confidence(context, metric_type)
                            })
                            
                    except (ValueError, IndexError) as e:
                        continue
                        
        return financial_data
    
    def _extract_risk_factors(self, text: str) -> List[Dict[str, Any]]:
        risk_factors = []
        
        for pattern in self.risk_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                context = text[max(0, match.start()-200):match.end()+200]
                
                risk_factors.append({
                    'risk_type': pattern.replace(r'\s+', ' ').replace('\\', ''),
                    'context': context.strip(),
                    'position': match.start()
                })
                
        return risk_factors
    
    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        if not self.sentiment_analyzer:
            return {'error': 'Sentiment analyzer not available'}
            
        try:
            chunks = [text[i:i+512] for i in range(0, len(text), 512)]
            
            sentiments = []
            for chunk in chunks[:10]:
                if len(chunk.strip()) > 50:
                    result = self.sentiment_analyzer(chunk)
                    sentiments.append(result[0])
            
            if sentiments:
                positive_count = sum(1 for s in sentiments if s['label'] == 'positive')
                negative_count = sum(1 for s in sentiments if s['label'] == 'negative')
                neutral_count = len(sentiments) - positive_count - negative_count
                
                avg_score = np.mean([s['score'] for s in sentiments])
                
                return {
                    'overall_sentiment': {
                        'positive': positive_count / len(sentiments),
                        'negative': negative_count / len(sentiments),
                        'neutral': neutral_count / len(sentiments)
                    },
                    'average_confidence': avg_score,
                    'total_chunks_analyzed': len(sentiments)
                }
                
        except Exception as e:
            self.logger.error(f"Sentiment analysis error: {e}")
            
        return {'error': 'Sentiment analysis failed'}
    
    def _extract_key_sections(self, text_content: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        sections = {
            'management_discussion': [],
            'business_overview': [],
            'financial_statements': [],
            'risk_factors': []
        }
        
        section_keywords = {
            'management_discussion': ['management discussion', 'md&a', 'mda'],
            'business_overview': ['business overview', 'business description', 'our business'],
            'financial_statements': ['consolidated statements', 'balance sheet', 'income statement'],
            'risk_factors': ['risk factors', 'item 1a']
        }
        
        for block in text_content:
            content = block['content'].lower()
            
            for section_name, keywords in section_keywords.items():
                for keyword in keywords:
                    if keyword in content:
                        sections[section_name].append({
                            'content': block['content'],
                            'page': block.get('page', 0),
                            'relevance_score': content.count(keyword)
                        })
                        break
                        
        return sections
    
    def _calculate_confidence(self, context: str, metric_type: str) -> float:
        confidence = 0.5
        
        context_lower = context.lower()
        
        if metric_type in context_lower:
            confidence += 0.2
            
        if any(word in context_lower for word in ['total', 'net', 'gross']):
            confidence += 0.1
            
        if any(word in context_lower for word in ['million', 'billion', 'thousand']):
            confidence += 0.1
            
        if '$' in context:
            confidence += 0.1
            
        return min(confidence, 1.0)
    
    def extract_from_tables(self, tables: List[Dict[str, Any]]) -> Dict[str, Any]:
        table_metrics = {
            'financial_statements': [],
            'summary_data': {}
        }
        
        for table in tables:
            df = table.get('raw_data', pd.DataFrame())
            
            if not df.empty:
                financial_statement = self._identify_financial_statement(df)
                
                if financial_statement:
                    processed_table = self._process_financial_table(df, financial_statement)
                    table_metrics['financial_statements'].append({
                        'table_id': table.get('table_id'),
                        'page': table.get('page'),
                        'statement_type': financial_statement,
                        'data': processed_table
                    })
                    
        return table_metrics
    
    def _identify_financial_statement(self, df: pd.DataFrame) -> Optional[str]:
        df_str = df.to_string().lower()
        
        if any(keyword in df_str for keyword in ['revenue', 'sales', 'net income', 'earnings']):
            return 'income_statement'
        elif any(keyword in df_str for keyword in ['assets', 'liabilities', 'equity', 'cash']):
            return 'balance_sheet'
        elif any(keyword in df_str for keyword in ['cash flow', 'operating activities']):
            return 'cash_flow'
            
        return None
    
    def _process_financial_table(self, df: pd.DataFrame, statement_type: str) -> Dict[str, Any]:
        processed = {
            'statement_type': statement_type,
            'data': df.to_dict('records'),
            'key_metrics': {}
        }
        
        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) > 0:
                processed['key_metrics'] = {
                    'numeric_columns': list(numeric_cols),
                    'summary_stats': df[numeric_cols].describe().to_dict()
                }
                
        except Exception as e:
            self.logger.error(f"Error processing financial table: {e}")
            
        return processed
