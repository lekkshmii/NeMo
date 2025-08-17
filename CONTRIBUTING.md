# Contributing to NeMo

Thank you for your interest in contributing to NeMo! This document provides guidelines and information for contributors.

## 🎯 Ways to Contribute

- 🐛 **Bug Reports**: Report issues or unexpected behavior
- 💡 **Feature Requests**: Suggest new features or improvements
- 📝 **Documentation**: Improve documentation, examples, or tutorials
- 🧪 **Testing**: Add tests or improve test coverage
- 🔧 **Code**: Implement new features or fix bugs
- 📊 **Data**: Contribute datasets or improve data processing
- 🎨 **UI/UX**: Improve user interfaces or user experience

## 🚀 Getting Started

### Development Environment Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/nemo.git
   cd nemo
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Install Development Tools**
   ```bash
   pip install black flake8 pytest pytest-cov pre-commit
   pre-commit install
   ```

5. **Setup Environment**
   ```bash
   cp .env.template .env
   # Add your API keys to .env
   python setup.py
   ```

### 🧪 Running Tests

```bash
# Run all tests
python tests/test_nemo.py

# Run with pytest for detailed output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## 📋 Contribution Process

### 1. **Issue First**
Before starting work on a significant change:
- Check existing issues to avoid duplication
- Create a new issue describing your proposal
- Wait for discussion and approval from maintainers

### 2. **Branch Naming**
Use descriptive branch names:
- `feature/add-bloomberg-integration`
- `bugfix/fix-sec-api-timeout`
- `docs/update-installation-guide`
- `test/add-query-engine-tests`

### 3. **Code Standards**

#### Python Code Style
```bash
# Format code with Black
black src/ tests/ examples/

# Check linting with flake8
flake8 src/ tests/ examples/

# Type checking (optional)
mypy src/
```

#### Code Quality Guidelines
- Follow PEP 8 style guidelines
- Use type hints for function parameters and returns
- Write docstrings for classes and public methods
- Keep functions focused and under 50 lines when possible
- Use meaningful variable and function names

#### Example Code Structure
```python
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class FinancialAnalyzer:
    """Analyzes financial documents and extracts key metrics.
    
    This class provides methods for processing financial documents
    and extracting structured data for analysis.
    
    Args:
        config: Configuration settings for the analyzer
        
    Example:
        analyzer = FinancialAnalyzer(config)
        metrics = analyzer.extract_metrics(document)
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def extract_metrics(self, document: str) -> Optional[Dict[str, Any]]:
        """Extract financial metrics from a document.
        
        Args:
            document: Raw document content
            
        Returns:
            Dictionary containing extracted metrics, or None if extraction fails
            
        Raises:
            ValueError: If document is empty or invalid
        """
        if not document or not document.strip():
            raise ValueError("Document cannot be empty")
            
        try:
            # Implementation here
            pass
        except Exception as e:
            self.logger.error(f"Error extracting metrics: {e}")
            return None
```

### 4. **Testing Requirements**

#### Test Categories
- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **Performance Tests**: Test processing speed and memory usage

#### Writing Tests
```python
import unittest
from unittest.mock import Mock, patch
from src.extraction.financial_extractor import FinancialExtractor

class TestFinancialExtractor(unittest.TestCase):
    
    def setUp(self):
        self.extractor = FinancialExtractor()
    
    def test_extract_revenue_success(self):
        """Test successful revenue extraction from text."""
        text = "Total revenue was $100.5 million for the quarter."
        
        result = self.extractor.extract_revenue(text)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['value'], 100500000)
        self.assertGreater(result['confidence'], 0.8)
    
    def test_extract_revenue_no_data(self):
        """Test revenue extraction with no revenue data."""
        text = "The company reported strong growth this quarter."
        
        result = self.extractor.extract_revenue(text)
        
        self.assertIsNone(result)
    
    @patch('src.extraction.financial_extractor.requests.get')
    def test_api_integration(self, mock_get):
        """Test API integration with mocked responses."""
        mock_response = Mock()
        mock_response.json.return_value = {'revenue': 1000000}
        mock_get.return_value = mock_response
        
        result = self.extractor.get_external_data()
        
        self.assertEqual(result['revenue'], 1000000)
```

### 5. **Documentation**

#### Code Documentation
- Add docstrings to all classes and public methods
- Include type hints for parameters and return values
- Provide usage examples in docstrings
- Update README.md for new features

#### Jupyter Notebooks
- Keep notebooks clean and well-commented
- Include markdown cells explaining each step
- Test notebooks before committing
- Clear output cells before committing (optional)

### 6. **Commit Messages**

Use conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(sec-api): add real-time filing monitoring

Add functionality to monitor SEC filings in real-time
using websocket connections for instant updates.

Closes #123
```

```
fix(query-engine): handle empty search results gracefully

Previously, empty search results would cause a crash.
Now returns appropriate error message to user.

Fixes #456
```

## 🎯 Specific Contribution Areas

### 🧠 AI/ML Improvements
- **Model Integration**: Add support for new language models
- **Performance Optimization**: Improve inference speed and accuracy
- **Fine-tuning**: Create domain-specific model adaptations
- **Evaluation**: Develop better metrics and benchmarks

### 📊 Data Processing
- **Document Formats**: Support for new file types (Word, PowerPoint, etc.)
- **Data Sources**: Integration with additional financial data providers
- **Parsing Improvements**: Better extraction accuracy for complex documents
- **Real-time Processing**: Streaming data processing capabilities

### 🌐 API and Integration
- **REST API**: New endpoints and improved error handling
- **Authentication**: User management and API key systems
- **Rate Limiting**: Smart throttling and quota management
- **Webhooks**: Event-driven notifications

### 🎨 User Experience
- **Dashboard**: Interactive web interface improvements
- **Visualization**: Better charts and data presentation
- **Mobile Support**: Responsive design and mobile apps
- **Accessibility**: Screen reader and keyboard navigation support

### 🔒 Security and Privacy
- **Data Encryption**: Secure storage and transmission
- **Privacy Controls**: Data anonymization and GDPR compliance
- **Access Control**: Role-based permissions
- **Audit Logging**: Security event tracking

## 🐛 Bug Reports

When reporting bugs, please include:

### Required Information
- **Environment**: OS, Python version, dependency versions
- **Steps to Reproduce**: Exact steps that trigger the bug
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Error Messages**: Full error traceback
- **Sample Data**: Minimal example that reproduces the issue

### Bug Report Template
```markdown
## Bug Description
Brief description of the bug

## Environment
- OS: [e.g., Windows 10, macOS 12.0, Ubuntu 20.04]
- Python: [e.g., 3.9.7]
- NeMo Version: [e.g., 0.1.0]

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What you expected to happen

## Actual Behavior
What actually happened

## Error Messages
```
Full error traceback here
```

## Additional Context
Any other context about the problem
```

## 💡 Feature Requests

When requesting features, please include:

### Required Information
- **Use Case**: Why is this feature needed?
- **Proposed Solution**: How should it work?
- **Alternatives**: What alternatives have you considered?
- **Impact**: Who would benefit from this feature?

### Feature Request Template
```markdown
## Feature Description
Brief description of the requested feature

## Problem Statement
What problem does this feature solve?

## Proposed Solution
How should this feature work?

## Example Usage
```python
# Example code showing how the feature would be used
result = new_feature.process(data)
```

## Alternatives Considered
What other approaches did you consider?

## Additional Context
Any other context or screenshots about the feature
```

## 🎓 Learning Resources

### Financial Domain Knowledge
- [SEC EDGAR Database](https://www.sec.gov/edgar)
- [Financial Statement Analysis](https://www.investopedia.com/articles/fundamental-analysis/)
- [XBRL Standards](https://www.xbrl.org/)

### Technical Skills
- [Python Best Practices](https://docs.python-guide.org/)
- [Machine Learning for Finance](https://github.com/stefan-jansen/machine-learning-for-trading)
- [Vector Databases](https://weaviate.io/blog/what-is-a-vector-database)

### NLP and AI
- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [LangChain Documentation](https://python.langchain.com/)
- [Financial NLP Papers](https://github.com/AI4Finance-Foundation/FinNLP)

## 📞 Getting Help

- 💬 **GitHub Discussions**: For questions and general discussion
- 🐛 **GitHub Issues**: For bug reports and feature requests
- 📧 **Email**: maintainers@nemo-ai.com for private inquiries
- 📖 **Documentation**: Check the wiki for detailed guides

## 🏆 Recognition

Contributors will be:
- Listed in the README contributors section
- Mentioned in release notes for significant contributions
- Invited to join the core team for exceptional contributions

## 📜 Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

### Our Standards

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

Thank you for contributing to NeMo! 🚀
