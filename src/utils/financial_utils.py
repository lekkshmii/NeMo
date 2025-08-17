import re
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def clean_financial_value(value_str: str) -> Optional[float]:
    if not value_str:
        return None
        
    value_str = str(value_str).strip()
    
    negative_indicators = ['(', '-', 'loss', 'deficit']
    is_negative = any(indicator in value_str.lower() for indicator in negative_indicators)
    
    clean_value = re.sub(r'[^\d\.]', '', value_str)
    
    if not clean_value:
        return None
        
    try:
        numeric_value = float(clean_value)
        return -numeric_value if is_negative else numeric_value
    except ValueError:
        return None

def extract_financial_periods(text: str) -> List[Dict[str, Any]]:
    period_patterns = [
        r'(?:for\s+the\s+)?(?:year|quarter)\s+ended?\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'(?:fiscal\s+)?(?:year|quarter)\s+(\d{4})',
        r'(\d{4})\s+(?:fiscal\s+)?(?:year|quarter)',
        r'Q([1-4])\s+(\d{4})',
        r'(\d{1,2})/(\d{1,2})/(\d{4})'
    ]
    
    periods = []
    
    for pattern in period_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            periods.append({
                'raw_text': match.group(0),
                'extracted_date': match.groups(),
                'position': match.start()
            })
    
    return periods

def calculate_financial_ratios(metrics: Dict[str, float]) -> Dict[str, float]:
    ratios = {}
    
    try:
        if 'revenue' in metrics and 'net_income' in metrics and metrics['revenue'] > 0:
            ratios['profit_margin'] = metrics['net_income'] / metrics['revenue']
        
        if 'net_income' in metrics and 'total_assets' in metrics and metrics['total_assets'] > 0:
            ratios['roa'] = metrics['net_income'] / metrics['total_assets']
        
        if 'total_debt' in metrics and 'total_assets' in metrics and metrics['total_assets'] > 0:
            ratios['debt_ratio'] = metrics['total_debt'] / metrics['total_assets']
        
        if 'cash' in metrics and 'total_debt' in metrics and metrics['total_debt'] > 0:
            ratios['cash_to_debt'] = metrics['cash'] / metrics['total_debt']
        
        if 'total_assets' in metrics and 'total_debt' in metrics:
            equity = metrics['total_assets'] - metrics.get('total_debt', 0)
            if equity > 0 and 'net_income' in metrics:
                ratios['roe'] = metrics['net_income'] / equity
                
    except (ZeroDivisionError, KeyError) as e:
        logger.warning(f"Error calculating ratios: {e}")
    
    return ratios

def detect_currency_and_scale(text: str) -> Dict[str, Any]:
    currency_patterns = {
        'USD': [r'\$', r'USD', r'US\s+dollars?', r'dollars?'],
        'EUR': [r'€', r'EUR', r'euros?'],
        'GBP': [r'£', r'GBP', r'pounds?'],
        'JPY': [r'¥', r'JPY', r'yen']
    }
    
    scale_patterns = {
        'thousands': [r'thousands?', r'\(000\)', r'in\s+thousands'],
        'millions': [r'millions?', r'\(000,000\)', r'in\s+millions'],
        'billions': [r'billions?', r'\(000,000,000\)', r'in\s+billions']
    }
    
    detected = {'currency': 'USD', 'scale': 'actual', 'scale_factor': 1}
    
    for currency, patterns in currency_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                detected['currency'] = currency
                break
    
    for scale, patterns in scale_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                detected['scale'] = scale
                if scale == 'thousands':
                    detected['scale_factor'] = 1000
                elif scale == 'millions':
                    detected['scale_factor'] = 1000000
                elif scale == 'billions':
                    detected['scale_factor'] = 1000000000
                break
    
    return detected

def standardize_metric_names(metric_name: str) -> str:
    standardization_map = {
        'total revenue': 'revenue',
        'net sales': 'revenue',
        'total sales': 'revenue',
        'revenues': 'revenue',
        'sales': 'revenue',
        
        'net earnings': 'net_income',
        'net profit': 'net_income',
        'profit': 'net_income',
        'earnings': 'net_income',
        
        'total debt': 'debt',
        'long-term debt': 'long_term_debt',
        'short-term debt': 'short_term_debt',
        
        'cash and cash equivalents': 'cash',
        'cash and equivalents': 'cash',
        'total cash': 'cash',
        
        'total assets': 'assets',
        'total stockholders equity': 'equity',
        'shareholders equity': 'equity',
        'stockholders equity': 'equity'
    }
    
    metric_lower = metric_name.lower().strip()
    
    for pattern, standard in standardization_map.items():
        if pattern in metric_lower:
            return standard
    
    return metric_lower.replace(' ', '_').replace('-', '_')

def format_financial_number(value: float, currency: str = 'USD', 
                          scale: str = 'millions') -> str:
    if pd.isna(value):
        return 'N/A'
    
    currency_symbols = {'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥'}
    symbol = currency_symbols.get(currency, '$')
    
    if scale == 'billions':
        formatted_value = value / 1e9
        suffix = 'B'
    elif scale == 'millions':
        formatted_value = value / 1e6
        suffix = 'M'
    elif scale == 'thousands':
        formatted_value = value / 1e3
        suffix = 'K'
    else:
        formatted_value = value
        suffix = ''
    
    if abs(formatted_value) >= 1000:
        return f"{symbol}{formatted_value:,.1f}{suffix}"
    elif abs(formatted_value) >= 1:
        return f"{symbol}{formatted_value:.1f}{suffix}"
    else:
        return f"{symbol}{formatted_value:.2f}{suffix}"

def create_financial_summary(metrics: Dict[str, Any]) -> Dict[str, Any]:
    financial_data = metrics.get('financial_data', {})
    
    summary = {
        'key_metrics': {},
        'ratios': {},
        'period_info': {},
        'data_quality': {}
    }
    
    for metric_type, values in financial_data.items():
        if values:
            latest_value = values[0]
            summary['key_metrics'][metric_type] = {
                'value': latest_value['value'],
                'confidence': latest_value['confidence'],
                'formatted': format_financial_number(latest_value['value'])
            }
    
    if summary['key_metrics']:
        key_values = {k: v['value'] for k, v in summary['key_metrics'].items()}
        summary['ratios'] = calculate_financial_ratios(key_values)
    
    summary['data_quality'] = {
        'metrics_found': len(summary['key_metrics']),
        'avg_confidence': np.mean([v['confidence'] for v in summary['key_metrics'].values()]) if summary['key_metrics'] else 0,
        'risk_factors_count': len(metrics.get('risk_factors', [])),
        'sentiment_analyzed': 'sentiment_analysis' in metrics
    }
    
    return summary

def compare_financial_metrics(company_metrics: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    comparison_data = []
    
    for company, metrics in company_metrics.items():
        summary = create_financial_summary(metrics)
        
        row = {'Company': company}
        
        for metric, data in summary['key_metrics'].items():
            row[f'{metric}_value'] = data['value']
            row[f'{metric}_formatted'] = data['formatted']
        
        for ratio, value in summary['ratios'].items():
            row[f'{ratio}_ratio'] = value
        
        comparison_data.append(row)
    
    return pd.DataFrame(comparison_data)

def validate_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    validation_results = {
        'is_valid': True,
        'warnings': [],
        'errors': [],
        'data_quality_score': 0.0
    }
    
    if not data.get('financial_data'):
        validation_results['errors'].append("No financial data extracted")
        validation_results['is_valid'] = False
    
    financial_data = data.get('financial_data', {})
    
    for metric_type, values in financial_data.items():
        for value_entry in values:
            if value_entry['confidence'] < 0.3:
                validation_results['warnings'].append(
                    f"Low confidence ({value_entry['confidence']:.2f}) for {metric_type}"
                )
            
            if value_entry['value'] < 0 and metric_type in ['revenue', 'cash', 'assets']:
                validation_results['warnings'].append(
                    f"Negative value for {metric_type} seems unusual"
                )
    
    quality_factors = []
    
    quality_factors.append(min(len(financial_data) / 5, 1.0))
    
    if financial_data:
        avg_confidence = np.mean([
            v['confidence'] for values in financial_data.values() 
            for v in values
        ])
        quality_factors.append(avg_confidence)
    
    risk_factors = data.get('risk_factors', [])
    quality_factors.append(min(len(risk_factors) / 10, 1.0))
    
    validation_results['data_quality_score'] = np.mean(quality_factors) if quality_factors else 0.0
    
    return validation_results

def generate_insights(financial_summary: Dict[str, Any]) -> List[str]:
    insights = []
    
    ratios = financial_summary.get('ratios', {})
    
    if 'profit_margin' in ratios:
        margin = ratios['profit_margin']
        if margin > 0.2:
            insights.append(f"Strong profitability with {margin:.1%} profit margin")
        elif margin < 0:
            insights.append(f"Company is unprofitable with {margin:.1%} profit margin")
        else:
            insights.append(f"Moderate profitability with {margin:.1%} profit margin")
    
    if 'debt_ratio' in ratios:
        debt_ratio = ratios['debt_ratio']
        if debt_ratio > 0.6:
            insights.append(f"High leverage with {debt_ratio:.1%} debt-to-assets ratio")
        elif debt_ratio < 0.3:
            insights.append(f"Conservative capital structure with {debt_ratio:.1%} debt ratio")
    
    if 'roa' in ratios:
        roa = ratios['roa']
        if roa > 0.15:
            insights.append(f"Excellent asset efficiency with {roa:.1%} ROA")
        elif roa < 0.05:
            insights.append(f"Low asset efficiency with {roa:.1%} ROA")
    
    data_quality = financial_summary.get('data_quality', {})
    quality_score = data_quality.get('data_quality_score', 0)
    
    if quality_score > 0.8:
        insights.append("High-quality financial data extraction")
    elif quality_score < 0.5:
        insights.append("Limited financial data available - may need manual review")
    
    return insights
