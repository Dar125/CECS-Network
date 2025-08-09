"""
Test cases for Day 7 advanced features:
- Caching system
- Structured logging and performance monitoring
- Agent confidence scoring
- AST parsing
- Static analysis integration
"""

import asyncio
import pytest
import sys
import os
import json
import time
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cache_manager import CacheManager, ModalCacheManager
from utils.logger import StructuredLogger, PerformanceMonitor, APICallTracker, get_logger, track_performance
from utils.confidence_scorer import ConfidenceScorer
from utils.ast_analyzer import ASTAnalyzer, analyze_python_code
from utils.static_analyzer import StaticAnalyzer
from utils.consensus_mechanism import WeightedConsensus


class TestCacheManager:
    """Test cache management functionality"""
    
    def test_cache_basic_operations(self):
        """Test basic cache get/set operations"""
        cache = CacheManager(ttl=3600)
        
        # Test cache miss
        result = cache.get("test_code", "code_reviewer")
        assert result is None
        assert cache.stats["misses"] == 1
        
        # Test cache set and hit
        test_result = {"issues": ["test issue"], "score": 8.5}
        cache.set("test_code", "code_reviewer", test_result)
        
        cached_result = cache.get("test_code", "code_reviewer")
        assert cached_result == test_result
        assert cache.stats["hits"] == 1
    
    def test_cache_key_generation(self):
        """Test cache key generation with different inputs"""
        cache = CacheManager()
        
        # Same code and agent should generate same key
        key1 = cache._generate_cache_key("def foo(): pass", "security_checker")
        key2 = cache._generate_cache_key("def foo(): pass", "security_checker")
        assert key1 == key2
        
        # Different code should generate different key
        key3 = cache._generate_cache_key("def bar(): pass", "security_checker")
        assert key1 != key3
        
        # Different agent should generate different key
        key4 = cache._generate_cache_key("def foo(): pass", "code_reviewer")
        assert key1 != key4
    
    def test_cache_expiration(self):
        """Test cache entry expiration"""
        cache = CacheManager(ttl=1)  # 1 second TTL
        
        cache.set("test_code", "agent", {"result": "test"})
        assert cache.get("test_code", "agent") is not None
        
        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("test_code", "agent") is None
        assert cache.stats["evictions"] == 1
    
    def test_cache_stats(self):
        """Test cache statistics tracking"""
        cache = CacheManager()
        
        # Generate some cache activity
        cache.get("code1", "agent")  # miss
        cache.set("code1", "agent", {"result": 1})
        cache.get("code1", "agent")  # hit
        cache.get("code2", "agent")  # miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 1/3
        assert stats["cache_size"] == 1


class TestStructuredLogging:
    """Test structured logging functionality"""
    
    def test_structured_logger_creation(self):
        """Test logger initialization"""
        logger = get_logger("test_module")
        assert isinstance(logger, StructuredLogger)
        assert logger.logger.name == "test_module"
    
    def test_log_with_context(self):
        """Test logging with additional context"""
        logger = get_logger("test")
        logger.add_context(request_id="123", user="test_user")
        
        # Mock the logger handler to capture output
        with patch.object(logger.logger, 'log') as mock_log:
            logger.info("Test message", operation="test_op")
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == 20  # INFO level
            assert call_args[0][1] == "Test message"
            assert "context" in call_args[1]["extra"]
            assert call_args[1]["extra"]["context"]["request_id"] == "123"
            assert call_args[1]["extra"]["context"]["operation"] == "test_op"
    
    def test_performance_tracking_decorator(self):
        """Test performance tracking decorator"""
        @track_performance("test_operation")
        def slow_function():
            time.sleep(0.1)
            return "done"
        
        result = slow_function()
        assert result == "done"
        
        # Check that metric was recorded
        stats = perf_monitor.get_stats("test_operation_duration")
        assert stats["count"] >= 1
        assert stats["min"] >= 0.1
    
    @pytest.mark.asyncio
    async def test_async_performance_tracking(self):
        """Test async performance tracking"""
        @track_performance("async_operation")
        async def async_function():
            await asyncio.sleep(0.1)
            return "async done"
        
        result = await async_function()
        assert result == "async done"
        
        stats = perf_monitor.get_stats("async_operation_duration")
        assert stats["count"] >= 1
    
    def test_api_call_tracker(self):
        """Test API call tracking"""
        tracker = APICallTracker()
        
        # Track some API calls
        tracker.track_call(
            api_name="openai",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=200,
            duration=1.5
        )
        
        tracker.track_call(
            api_name="openai",
            model="gpt-4o-mini",
            input_tokens=50,
            output_tokens=100,
            duration=0.8
        )
        
        summary = tracker.get_summary()
        assert summary["total_calls"] == 2
        assert summary["total_tokens"] == 450
        assert summary["total_cost"] > 0
        assert "gpt-4o" in summary["by_model"]
        assert "gpt-4o-mini" in summary["by_model"]


class TestConfidenceScoring:
    """Test confidence scoring system"""
    
    def test_basic_confidence_calculation(self):
        """Test basic confidence score calculation"""
        scorer = ConfidenceScorer()
        
        finding = {
            "description": "This is definitely a security vulnerability",
            "severity": "high"
        }
        
        confidence = scorer.calculate_confidence(finding, "security_checker")
        assert 0.8 <= confidence <= 0.95
    
    def test_evidence_keywords(self):
        """Test evidence keyword detection"""
        scorer = ConfidenceScorer()
        
        # High confidence keywords
        high_conf_finding = {
            "description": "This definitely causes a SQL injection vulnerability",
            "severity": "critical"
        }
        high_conf = scorer.calculate_confidence(high_conf_finding, "security_checker")
        
        # Low confidence keywords
        low_conf_finding = {
            "description": "This might possibly be an issue",
            "severity": "low"
        }
        low_conf = scorer.calculate_confidence(low_conf_finding, "security_checker")
        
        assert high_conf > low_conf
    
    def test_consensus_confidence_adjustment(self):
        """Test confidence adjustment based on agent consensus"""
        scorer = ConfidenceScorer()
        
        # High agreement should boost confidence
        high_agreement = scorer.adjust_consensus_confidence(
            {"confidence": 0.7},
            agent_agreements=3,
            total_agents=3
        )
        assert high_agreement > 0.7
        
        # Low agreement should reduce confidence
        low_agreement = scorer.adjust_consensus_confidence(
            {"confidence": 0.7},
            agent_agreements=1,
            total_agents=3
        )
        assert low_agreement < 0.7
    
    def test_confidence_categorization(self):
        """Test confidence score categorization"""
        scorer = ConfidenceScorer()
        
        assert scorer.categorize_confidence(0.9) == "Very High"
        assert scorer.categorize_confidence(0.75) == "High"
        assert scorer.categorize_confidence(0.6) == "Medium"
        assert scorer.categorize_confidence(0.45) == "Low"
        assert scorer.categorize_confidence(0.3) == "Very Low"


class TestASTAnalyzer:
    """Test AST analysis functionality"""
    
    def test_basic_ast_analysis(self):
        """Test basic AST analysis"""
        code = """
def calculate_sum(a, b):
    '''Calculate sum of two numbers'''
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y

result = calculate_sum(1, 2)
"""
        
        results = analyze_python_code(code)
        assert "ast_analysis" in results
        
        ast_data = results["ast_analysis"]
        assert len(ast_data["functions"]) == 1
        assert ast_data["functions"][0]["name"] == "calculate_sum"
        assert ast_data["functions"][0]["docstring"] == True
        
        assert len(ast_data["classes"]) == 1
        assert ast_data["classes"][0]["name"] == "Calculator"
        assert "multiply" in ast_data["classes"][0]["methods"]
    
    def test_complexity_calculation(self):
        """Test cyclomatic complexity calculation"""
        complex_code = """
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            else:
                return x + y
        else:
            return x
    elif x < 0 and y < 0:
        return -x - y
    else:
        for i in range(10):
            if i % 2 == 0:
                print(i)
        return 0
"""
        
        results = analyze_python_code(complex_code)
        ast_data = results["ast_analysis"]
        
        assert "complexity" in ast_data
        assert "complex_function" in ast_data["complexity"]
        # Should have high complexity due to nested conditions
        assert ast_data["complexity"]["complex_function"] > 5
    
    def test_security_pattern_detection(self):
        """Test detection of security patterns"""
        vulnerable_code = """
import pickle

password = "admin123"
api_key = "sk-1234567890"

def unsafe_function(user_input):
    eval(user_input)
    exec(user_input)
    
    data = pickle.loads(user_input)
    return data
"""
        
        results = analyze_python_code(vulnerable_code)
        ast_data = results["ast_analysis"]
        
        assert len(ast_data["security_patterns"]) >= 2
        
        # Check for dangerous function detection
        dangerous_funcs = [p for p in ast_data["security_patterns"] 
                          if p["type"] == "dangerous_function"]
        assert len(dangerous_funcs) >= 2
        
        # Check for hardcoded secrets
        secrets = [p for p in ast_data["security_patterns"] 
                   if p["type"] == "hardcoded_secret"]
        assert len(secrets) >= 2
    
    def test_code_smell_detection(self):
        """Test code smell detection"""
        smelly_code = """
def function_with_too_many_params(a, b, c, d, e, f, g):
    pass

def very_long_function():
    # Simulate a long function
    x = 1
    x = 2
    x = 3
    x = 4
    x = 5
    x = 6
    x = 7
    x = 8
    x = 9
    x = 10
    x = 11
    x = 12
    x = 13
    x = 14
    x = 15
    x = 16
    x = 17
    x = 18
    x = 19
    x = 20
    x = 21
    x = 22
    x = 23
    x = 24
    x = 25
    x = 26
    x = 27
    x = 28
    x = 29
    x = 30
    x = 31
    x = 32
    x = 33
    x = 34
    x = 35
    x = 36
    x = 37
    x = 38
    x = 39
    x = 40
    x = 41
    x = 42
    x = 43
    x = 44
    x = 45
    x = 46
    x = 47
    x = 48
    x = 49
    x = 50
    x = 51
    x = 52
    return x

try:
    something()
except:
    pass
"""
        
        results = analyze_python_code(smelly_code)
        ast_data = results["ast_analysis"]
        
        assert len(ast_data["code_smells"]) >= 2
        
        # Check for too many parameters
        param_smells = [s for s in ast_data["code_smells"] 
                        if s["type"] == "too_many_parameters"]
        assert len(param_smells) >= 1
        
        # Check for bare except
        except_smells = [s for s in ast_data["code_smells"] 
                         if s["type"] == "bare_except"]
        assert len(except_smells) >= 1


class TestStaticAnalyzer:
    """Test static analysis integration"""
    
    def test_static_analyzer_initialization(self):
        """Test static analyzer initialization"""
        analyzer = StaticAnalyzer()
        assert isinstance(analyzer.available_tools, dict)
        # At least check for tool availability (may not be installed in test env)
        assert "pylint" in analyzer.available_tools
        assert "bandit" in analyzer.available_tools
    
    def test_analyze_all_basic(self):
        """Test running all available analyzers"""
        analyzer = StaticAnalyzer()
        
        test_code = """
def add(a, b):
    return a + b

result = add(1, 2)
"""
        
        results = analyzer.analyze_all(test_code, "test.py")
        
        assert "filename" in results
        assert "tools_available" in results
        assert "analyses" in results
        assert "summary" in results


class TestIntegration:
    """Test integration of Day 7 features"""
    
    @pytest.mark.asyncio
    async def test_consensus_with_confidence(self):
        """Test consensus mechanism with confidence scoring"""
        consensus = WeightedConsensus()
        
        agent_findings = {
            "security_checker": [
                {
                    "agent": "security_checker",
                    "type": "SQL Injection",
                    "severity": "Critical",
                    "description": "Definitely a SQL injection vulnerability in user query",
                    "location": "Line 15",
                    "line_numbers": [15]
                }
            ],
            "code_reviewer": [
                {
                    "agent": "code_reviewer",
                    "type": "SQL Injection Risk",
                    "severity": "High",
                    "description": "Possibly vulnerable to SQL injection",
                    "location": "Line 15",
                    "line_numbers": [15]
                }
            ]
        }
        
        results = consensus.resolve_conflicts(agent_findings)
        
        assert "recommendations" in results
        assert len(results["recommendations"]) >= 1
        
        # Check that confidence scores were added
        for rec in results["recommendations"]:
            assert "confidence" in rec
            assert "confidence_level" in rec
            assert "individual_confidences" in rec


if __name__ == "__main__":
    pytest.main([__file__, "-v"])