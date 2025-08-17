import requests
import json
import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta
import time
import re
from pathlib import Path
from config.settings import config

class SECDataSource:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://data.sec.gov"
        self.headers = {
            'User-Agent': config.sec_user_agent,
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'data.sec.gov'
        }
        self.rate_limit_delay = 0.1
        
    def search_company(self, query: str) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/submissions/CIK{query.zfill(10)}.json"
            response = self._make_request(url)
            
            if response:
                return [self._format_company_info(response)]
            else:
                return self._search_by_ticker(query)
                
        except Exception as e:
            self.logger.error(f"Error searching company {query}: {e}")
            return []
    
    def _search_by_ticker(self, ticker: str) -> List[Dict[str, Any]]:
        try:
            tickers_url = f"{self.base_url}/submissions/submissions.zip"
            
            companies = []
            
            return companies
            
        except Exception as e:
            self.logger.error(f"Error searching by ticker {ticker}: {e}")
            return []
    
    def get_company_filings(self, cik: str, form_types: List[str] = None, 
                           limit: int = 20) -> List[Dict[str, Any]]:
        
        if form_types is None:
            form_types = ['10-K', '10-Q', '8-K']
            
        try:
            cik_padded = cik.zfill(10)
            url = f"{self.base_url}/submissions/CIK{cik_padded}.json"
            
            response = self._make_request(url)
            
            if not response:
                return []
                
            filings = []
            recent_filings = response.get('filings', {}).get('recent', {})
            
            if recent_filings:
                filings_data = self._parse_filings_data(recent_filings, form_types, limit)
                filings.extend(filings_data)
                
            return filings[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting filings for CIK {cik}: {e}")
            return []
    
    def _parse_filings_data(self, recent_filings: Dict[str, List], 
                           form_types: List[str], limit: int) -> List[Dict[str, Any]]:
        filings = []
        
        accession_numbers = recent_filings.get('accessionNumber', [])
        filing_dates = recent_filings.get('filingDate', [])
        forms = recent_filings.get('form', [])
        primary_docs = recent_filings.get('primaryDocument', [])
        
        for i in range(min(len(accession_numbers), limit * 2)):
            if i < len(forms) and forms[i] in form_types:
                accession = accession_numbers[i] if i < len(accession_numbers) else ''
                filing_date = filing_dates[i] if i < len(filing_dates) else ''
                form_type = forms[i] if i < len(forms) else ''
                primary_doc = primary_docs[i] if i < len(primary_docs) else ''
                
                filing_url = self._build_filing_url(accession, primary_doc)
                
                filings.append({
                    'accession_number': accession,
                    'filing_date': filing_date,
                    'form_type': form_type,
                    'primary_document': primary_doc,
                    'filing_url': filing_url,
                    'data_url': f"{self.base_url}/submissions/{accession}.json"
                })
                
                if len(filings) >= limit:
                    break
                    
        return filings
    
    def _build_filing_url(self, accession_number: str, primary_document: str) -> str:
        accession_clean = accession_number.replace('-', '')
        
        base_edgar_url = "https://www.sec.gov/Archives/edgar/data"
        
        cik_from_accession = accession_number[:10]
        
        return f"{base_edgar_url}/{cik_from_accession}/{accession_number}/{primary_document}"
    
    def download_filing(self, filing_url: str) -> Optional[str]:
        try:
            headers = {
                'User-Agent': config.sec_user_agent
            }
            
            response = requests.get(filing_url, headers=headers, timeout=30)
            time.sleep(self.rate_limit_delay)
            
            if response.status_code == 200:
                return response.text
            else:
                self.logger.warning(f"Failed to download filing: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error downloading filing {filing_url}: {e}")
            return None
    
    def get_financial_data(self, cik: str, taxonomy: str = "us-gaap", 
                          tag: str = "Revenues") -> Dict[str, Any]:
        try:
            cik_padded = cik.zfill(10)
            url = f"{self.base_url}/api/xbrl/companyconcept/CIK{cik_padded}/{taxonomy}/{tag}.json"
            
            response = self._make_request(url)
            
            if response:
                return self._format_financial_data(response)
            else:
                return {}
                
        except Exception as e:
            self.logger.error(f"Error getting financial data for CIK {cik}: {e}")
            return {}
    
    def _format_financial_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        formatted_data = {
            'tag': data.get('tag'),
            'label': data.get('label'),
            'description': data.get('description'),
            'taxonomy': data.get('taxonomy'),
            'units': {}
        }
        
        units_data = data.get('units', {})
        
        for unit, values in units_data.items():
            formatted_values = []
            
            for value_entry in values:
                formatted_values.append({
                    'value': value_entry.get('val'),
                    'start_date': value_entry.get('start'),
                    'end_date': value_entry.get('end'),
                    'filed_date': value_entry.get('filed'),
                    'form': value_entry.get('form'),
                    'frame': value_entry.get('frame')
                })
            
            formatted_data['units'][unit] = formatted_values
            
        return formatted_data
    
    def search_recent_filings(self, form_type: str = "8-K", 
                             days_back: int = 7) -> List[Dict[str, Any]]:
        filings = []
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            for single_date in pd.date_range(start_date, end_date):
                date_str = single_date.strftime('%Y-%m-%d')
                daily_filings = self._get_daily_filings(date_str, form_type)
                filings.extend(daily_filings)
                
        except Exception as e:
            self.logger.error(f"Error searching recent filings: {e}")
            
        return filings
    
    def _get_daily_filings(self, date_str: str, form_type: str) -> List[Dict[str, Any]]:
        try:
            url = f"https://www.sec.gov/Archives/edgar/daily-index/{date_str.replace('-', '/')}/form.idx"
            
            response = requests.get(url, headers=self.headers, timeout=30)
            time.sleep(self.rate_limit_delay)
            
            if response.status_code != 200:
                return []
                
            lines = response.text.split('\n')
            filings = []
            
            for line in lines:
                if form_type in line:
                    parts = line.split('|')
                    if len(parts) >= 5:
                        filings.append({
                            'form_type': parts[0].strip(),
                            'company_name': parts[1].strip(),
                            'cik': parts[2].strip(),
                            'date_filed': parts[3].strip(),
                            'file_path': parts[4].strip(),
                            'filing_url': f"https://www.sec.gov/Archives/{parts[4].strip()}"
                        })
                        
            return filings
            
        except Exception as e:
            self.logger.error(f"Error getting daily filings for {date_str}: {e}")
            return []
    
    def _make_request(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            time.sleep(self.rate_limit_delay)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Request failed with status {response.status_code}: {url}")
                return None
                
        except Exception as e:
            self.logger.error(f"Request error for {url}: {e}")
            return None
    
    def _format_company_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'cik': data.get('cik'),
            'name': data.get('name'),
            'ticker': data.get('tickers', [None])[0] if data.get('tickers') else None,
            'exchange': data.get('exchanges', [None])[0] if data.get('exchanges') else None,
            'sic': data.get('sic'),
            'sic_description': data.get('sicDescription'),
            'entity_type': data.get('entityType'),
            'business_address': data.get('addresses', {}).get('business'),
            'mailing_address': data.get('addresses', {}).get('mailing')
        }
    
    def get_earnings_calls(self, cik: str, limit: int = 5) -> List[Dict[str, Any]]:
        filings = self.get_company_filings(cik, ['8-K'], limit * 2)
        
        earnings_calls = []
        
        for filing in filings:
            if self._is_earnings_call(filing):
                earnings_calls.append({
                    **filing,
                    'type': 'earnings_call'
                })
                
                if len(earnings_calls) >= limit:
                    break
                    
        return earnings_calls
    
    def _is_earnings_call(self, filing: Dict[str, Any]) -> bool:
        content = self.download_filing(filing.get('filing_url', ''))
        
        if not content:
            return False
            
        content_lower = content.lower()
        
        earnings_keywords = [
            'earnings', 'quarterly results', 'financial results',
            'conference call', 'investor call'
        ]
        
        return any(keyword in content_lower for keyword in earnings_keywords)
    
    def get_company_info_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        ticker_mappings = {
            'AAPL': '0000320193',
            'MSFT': '0000789019', 
            'GOOGL': '0001652044',
            'AMZN': '0001018724',
            'TSLA': '0001318605',
            'META': '0001326801',
            'NVDA': '0001045810'
        }
        
        cik = ticker_mappings.get(ticker.upper())
        
        if cik:
            companies = self.search_company(cik)
            return companies[0] if companies else None
        else:
            return None
