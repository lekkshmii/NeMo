import openai
import anthropic
import google.generativeai as genai
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
from typing import Dict, List, Any, Optional, Union
import logging
import json
import re
from config.settings import config

class QueryEngine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_llm_clients()
        self._setup_local_models()
        
    def _setup_llm_clients(self):
        if config.openai_api_key:
            openai.api_key = config.openai_api_key
            self.openai_client = openai.OpenAI(api_key=config.openai_api_key)
        else:
            self.openai_client = None
            
        if config.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        else:
            self.anthropic_client = None
            
        if config.google_api_key:
            genai.configure(api_key=config.google_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
        else:
            self.gemini_model = None
    
    def _setup_local_models(self):
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            self.local_financial_model = pipeline(
                "text-generation",
                model=config.financial_llm_model,
                device=device,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                max_length=1024
            )
            
        except Exception as e:
            self.logger.warning(f"Could not load local financial model: {e}")
            self.local_financial_model = None
    
    def answer_query(self, query: str, context: Dict[str, Any], 
                    model_preference: str = "claude") -> Dict[str, Any]:
        
        context_text = self._format_context(context)
        
        prompt = self._build_prompt(query, context_text)
        
        response = None
        citations = []
        
        try:
            if model_preference == "claude" and self.anthropic_client:
                response = self._query_claude(prompt, context)
            elif model_preference == "gpt" and self.openai_client:
                response = self._query_openai(prompt, context)
            elif model_preference == "gemini" and self.gemini_model:
                response = self._query_gemini(prompt)
            elif model_preference == "local" and self.local_financial_model:
                response = self._query_local(prompt)
            else:
                response = self._fallback_query(prompt, context)
                
            citations = self._extract_citations(context)
            
        except Exception as e:
            self.logger.error(f"Query processing error: {e}")
            response = f"Error processing query: {str(e)}"
            
        return {
            'query': query,
            'response': response,
            'citations': citations,
            'context_used': len(context_text),
            'model_used': model_preference
        }
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        context_parts = []
        
        text_results = context.get('text_results', [])
        for i, result in enumerate(text_results[:10]):
            context_parts.append(f"[TEXT-{i+1}] {result['content']}")
            
        table_results = context.get('table_results', [])
        for i, result in enumerate(table_results[:5]):
            context_parts.append(f"[TABLE-{i+1}] {result['content']}")
            
        return "\n\n".join(context_parts)
    
    def _build_prompt(self, query: str, context: str) -> str:
        return f"""You are a financial research analyst with access to SEC filings, earnings reports, and financial documents. 

Based on the following context from financial documents, answer the user's question accurately and provide specific citations.

CONTEXT:
{context}

QUESTION: {query}

Please provide a comprehensive answer that:
1. Directly addresses the question
2. Uses specific information from the context
3. Includes relevant financial metrics and data points
4. Cites sources using [TEXT-X] or [TABLE-X] format
5. Highlights any limitations or uncertainties in the data

ANSWER:"""
    
    def _query_claude(self, prompt: str, context: Dict[str, Any]) -> str:
        try:
            message = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
            
        except Exception as e:
            self.logger.error(f"Claude API error: {e}")
            return f"Error with Claude API: {str(e)}"
    
    def _query_openai(self, prompt: str, context: Dict[str, Any]) -> str:
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a financial research analyst specializing in SEC filings and financial document analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=config.max_tokens,
                temperature=config.temperature
            )
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return f"Error with OpenAI API: {str(e)}"
    
    def _query_gemini(self, prompt: str) -> str:
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            return f"Error with Gemini API: {str(e)}"
    
    def _query_local(self, prompt: str) -> str:
        try:
            response = self.local_financial_model(
                prompt,
                max_length=config.max_tokens,
                temperature=config.temperature,
                do_sample=True,
                pad_token_id=self.local_financial_model.tokenizer.eos_token_id
            )
            
            generated_text = response[0]['generated_text']
            answer = generated_text[len(prompt):].strip()
            
            return answer
            
        except Exception as e:
            self.logger.error(f"Local model error: {e}")
            return f"Error with local model: {str(e)}"
    
    def _fallback_query(self, prompt: str, context: Dict[str, Any]) -> str:
        return self._rule_based_answer(prompt, context)
    
    def _rule_based_answer(self, prompt: str, context: Dict[str, Any]) -> str:
        query_lower = prompt.lower()
        
        if any(keyword in query_lower for keyword in ['revenue', 'sales', 'income']):
            return self._extract_financial_metrics_answer(context, 'revenue')
        elif any(keyword in query_lower for keyword in ['risk', 'risks']):
            return self._extract_risk_factors_answer(context)
        elif any(keyword in query_lower for keyword in ['debt', 'liability']):
            return self._extract_financial_metrics_answer(context, 'debt')
        elif any(keyword in query_lower for keyword in ['cash', 'liquidity']):
            return self._extract_financial_metrics_answer(context, 'cash')
        else:
            return self._generic_context_answer(context)
    
    def _extract_financial_metrics_answer(self, context: Dict[str, Any], metric_type: str) -> str:
        relevant_content = []
        
        for result in context.get('text_results', []):
            if metric_type in result['content'].lower():
                relevant_content.append(result['content'])
                
        for result in context.get('table_results', []):
            if metric_type in result['content'].lower():
                relevant_content.append(result['content'])
        
        if relevant_content:
            return f"Based on the financial documents, here's information about {metric_type}:\n\n" + "\n\n".join(relevant_content[:3])
        else:
            return f"No specific information about {metric_type} found in the provided documents."
    
    def _extract_risk_factors_answer(self, context: Dict[str, Any]) -> str:
        risk_content = []
        
        for result in context.get('text_results', []):
            content_lower = result['content'].lower()
            if any(keyword in content_lower for keyword in ['risk', 'uncertainty', 'challenge']):
                risk_content.append(result['content'])
        
        if risk_content:
            return "Key risk factors identified in the documents:\n\n" + "\n\n".join(risk_content[:3])
        else:
            return "No specific risk factors found in the provided documents."
    
    def _generic_context_answer(self, context: Dict[str, Any]) -> str:
        text_results = context.get('text_results', [])
        
        if text_results:
            return f"Based on the available financial documents:\n\n{text_results[0]['content']}"
        else:
            return "No relevant information found in the provided documents."
    
    def _extract_citations(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        citations = []
        
        for i, result in enumerate(context.get('text_results', [])):
            metadata = result.get('metadata', {})
            citations.append({
                'id': f"TEXT-{i+1}",
                'type': 'text',
                'page': metadata.get('page', 'Unknown'),
                'document_id': metadata.get('document_id', 'Unknown'),
                'relevance_score': result.get('relevance_score', 0),
                'content_preview': result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
            })
            
        for i, result in enumerate(context.get('table_results', [])):
            metadata = result.get('metadata', {})
            citations.append({
                'id': f"TABLE-{i+1}",
                'type': 'table',
                'page': metadata.get('page', 'Unknown'),
                'document_id': metadata.get('document_id', 'Unknown'),
                'relevance_score': result.get('relevance_score', 0),
                'content_preview': result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
            })
            
        return citations
    
    def generate_summary(self, document_chunks: Dict[str, List[Dict[str, Any]]], 
                        model_preference: str = "claude") -> Dict[str, Any]:
        
        text_content = " ".join([
            chunk['content'] for chunk in document_chunks.get('text_chunks', [])[:20]
        ])
        
        summary_prompt = f"""Please provide a comprehensive summary of this financial document:

DOCUMENT CONTENT:
{text_content[:4000]}

Please include:
1. Company name and document type
2. Key financial metrics and performance indicators
3. Major business developments or changes
4. Risk factors and concerns
5. Forward-looking statements or guidance

SUMMARY:"""
        
        try:
            if model_preference == "claude" and self.anthropic_client:
                summary = self._query_claude(summary_prompt, {})
            elif model_preference == "gpt" and self.openai_client:
                summary = self._query_openai(summary_prompt, {})
            elif model_preference == "gemini" and self.gemini_model:
                summary = self._query_gemini(summary_prompt)
            else:
                summary = self._rule_based_summary(text_content)
                
        except Exception as e:
            summary = f"Error generating summary: {str(e)}"
        
        return {
            'summary': summary,
            'model_used': model_preference,
            'content_length': len(text_content)
        }
    
    def _rule_based_summary(self, content: str) -> str:
        sentences = content.split('.')[:10]
        return "Document Summary:\n\n" + ". ".join(sentences) + "."
