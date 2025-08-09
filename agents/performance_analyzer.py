"""
Performance Analyzer Agent - Focuses on code performance, complexity, and optimization
"""

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
import os
from typing import Dict, List, Any
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ast_analyzer import analyze_python_code
from utils.logger import get_logger, track_performance

# Initialize logger
logger = get_logger(__name__)


class PerformanceAnalyzerAgent:
    """Agent specialized in performance analysis and optimization recommendations"""
    
    def __init__(self, api_key: str = None):
        """Initialize the Performance Analyzer Agent
        
        Args:
            api_key: OpenAI API key (defaults to env var OPENAI_API_KEY)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
            
        self.model_client = OpenAIChatCompletionClient(
            model="gpt-4o",  # Using full model for better analysis
            temperature=0.1,
            api_key=self.api_key
        )
        
        self.agent = AssistantAgent(
            name="performance_analyzer",
            model_client=self.model_client,
            system_message=self._get_system_message()
        )
    
    def _get_system_message(self) -> str:
        """Define the system message for the performance analyzer agent"""
        return """You are an expert performance engineer specializing in code optimization and complexity analysis.
        
        Your responsibilities include analyzing:
        1. **Time Complexity**: Identify algorithms and their Big O notation
        2. **Space Complexity**: Memory usage and potential memory leaks
        3. **Database Performance**: Query optimization, N+1 problems, indexing issues
        4. **Algorithmic Efficiency**: Suggest more efficient algorithms or data structures
        5. **Resource Usage**: CPU, memory, I/O bottlenecks
        6. **Caching Opportunities**: Identify where caching could improve performance
        7. **Concurrency Issues**: Race conditions, deadlocks, thread safety
        8. **Network Efficiency**: API call optimization, payload size reduction
        9. **Loop Optimization**: Nested loops, unnecessary iterations
        10. **Memory Management**: Object creation patterns, garbage collection impact
        
        For each performance issue found, you MUST provide in this exact format:
        ISSUE: [Name of performance issue]
        SEVERITY: [Critical/High/Medium/Low]
        LOCATION: [Function name and line numbers]
        COMPLEXITY: [Current time/space complexity, e.g., O(n³)]
        IMPACT: [Performance impact description]
        SOLUTION: [Optimization suggestion with improved complexity]
        
        You MUST find and report ALL performance issues. Look especially for:
        - Triple nested loops (O(n³) or worse)
        - Quadratic algorithms where linear is possible
        - Memory leaks (objects added to collections but never removed)
        - N+1 database queries
        - Unnecessary repeated calculations
        - Missing caching opportunities
        - Inefficient string concatenation in loops
        - Recursive functions without memoization
        
        Be thorough. This is a performance review - missing bottlenecks is unacceptable."""
    
    @track_performance("performance_analyzer_analyze")
    async def analyze_code(self, code: str, filename: str = "unknown", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze code for performance issues and optimization opportunities
        
        Args:
            code: The code to analyze
            filename: Name of the file being analyzed
            context: Additional context (e.g., expected load, constraints)
            
        Returns:
            Dictionary containing performance analysis results
        """
        logger.info("Starting performance analysis", filename=filename)
        
        context = context or {}
        language = context.get("language", "auto-detect")
        expected_load = context.get("expected_load", "unknown")
        
        # Run AST analysis for Python code
        ast_results = {}
        if language.lower() in ["python", "py", "auto-detect"]:
            logger.info("Running AST analysis for Python code")
            ast_results = analyze_python_code(code)
            
            # Enhance context with AST insights
            if "ast_analysis" in ast_results and "error" not in ast_results["ast_analysis"]:
                ast_data = ast_results["ast_analysis"]
                context["ast_metrics"] = ast_data.get("metrics", {})
                context["complexity_scores"] = ast_data.get("complexity", {})
        
        # Build enhanced prompt with AST insights
        ast_summary = ""
        if ast_results and "ast_analysis" in ast_results and "error" not in ast_results["ast_analysis"]:
            ast_data = ast_results["ast_analysis"]
            metrics = ast_data.get("metrics", {})
            
            if metrics:
                ast_summary = f"""

AST Analysis Results:
- Total Functions: {metrics.get('total_functions', 0)}
- Average Complexity: {metrics.get('avg_complexity', 0)}
- Max Complexity: {metrics.get('max_complexity', 0)}
- High Complexity Functions: {', '.join(metrics.get('high_complexity_functions', []))}
- Security Issues Found: {metrics.get('security_issues', 0)}
- Code Smells: {metrics.get('code_smell_count', 0)}

Complexity Scores by Function:
"""
                for func, score in ast_data.get("complexity", {}).items():
                    ast_summary += f"- {func}: {score}\n"
        
        prompt = f"""Please perform a performance analysis of the following code from file '{filename}':

```{language}
{code}
```

Expected Load: {expected_load if expected_load != 'unknown' else 'Not specified'}
{ast_summary}

Perform a comprehensive performance review following the guidelines in your system message.

CRITICAL: You must find and report ALL performance issues using the exact format specified:
ISSUE: [Name]
SEVERITY: [Critical/High/Medium/Low]
LOCATION: [Function and lines]
COMPLEXITY: [e.g., O(n³)]
IMPACT: [Description]
SOLUTION: [Fix]

Specifically look for:
- Triple nested loops (like in find_duplicate_users)
- Memory leaks (like objects added to cache but never removed)
- N+1 query patterns in database operations
- Recursive functions without proper base cases
- Any O(n²) or worse algorithms

Use the AST analysis data to inform your review if provided."""

        try:
            result = await self.agent.run(task=prompt)
            
            # Extract the actual message content from AutoGen response
            if hasattr(result, 'messages') and len(result.messages) > 0:
                # Get the last assistant message
                analysis_text = result.messages[-1].content
            elif hasattr(result, 'content'):
                analysis_text = result.content
            elif isinstance(result, str):
                analysis_text = result
            else:
                analysis_text = str(result)
            
            # Merge AST findings with agent analysis
            performance_issues = self._extract_performance_issues(analysis_text)
            
            result = {
                "agent": "performance_analyzer",
                "filename": filename,
                "status": "success",
                "analysis": analysis_text,
                "performance_issues": performance_issues,
                "issues": self._extract_structured_issues(analysis_text)
            }
            
            # Add AST analysis if available
            if ast_results:
                result["ast_analysis"] = ast_results.get("ast_analysis", {})
            
            logger.info("Performance analysis completed",
                       filename=filename,
                       issues_found=len(result.get("issues", [])),
                       has_ast_data=bool(ast_results))
            
            return result
        except Exception as e:
            logger.error("Performance analysis failed",
                        exception=e,
                        filename=filename)
            
            return {
                "agent": "performance_analyzer",
                "filename": filename,
                "status": "error",
                "error": str(e),
                "analysis": None,
                "ast_analysis": ast_results.get("ast_analysis", {}) if ast_results else {}
            }
    
    def _extract_performance_issues(self, analysis_text: str) -> Dict[str, Any]:
        """Extract performance issue summary from analysis text"""
        analysis_lower = analysis_text.lower()
        
        # Extract complexity mentions
        time_complexity_issues = (
            analysis_lower.count("o(n^2)") + analysis_lower.count("o(n*n)") +
            analysis_lower.count("o(n^3)") + analysis_lower.count("o(n*n*n)") +
            analysis_lower.count("exponential") + analysis_lower.count("quadratic")
        )
        
        return {
            "critical": analysis_lower.count("critical performance") + analysis_lower.count("severe performance"),
            "high": analysis_lower.count("high impact") + analysis_lower.count("significant performance"),
            "medium": analysis_lower.count("medium impact") + analysis_lower.count("moderate performance"),
            "low": analysis_lower.count("low impact") + analysis_lower.count("minor performance"),
            "complexity_issues": time_complexity_issues
        }
    
    def _extract_structured_issues(self, analysis_text: str) -> List[Dict[str, str]]:
        """Extract structured issues from analysis text"""
        issues = []
        lines = analysis_text.split('\n')
        
        i = 0
        while i < len(lines):
            if lines[i].strip().startswith("ISSUE:"):
                issue = {"name": lines[i].replace("ISSUE:", "").strip()}
                
                # Look for other fields
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith("ISSUE:"):
                    line = lines[j].strip()
                    if line.startswith("SEVERITY:"):
                        issue["severity"] = line.replace("SEVERITY:", "").strip()
                    elif line.startswith("LOCATION:"):
                        issue["location"] = line.replace("LOCATION:", "").strip()
                    elif line.startswith("COMPLEXITY:"):
                        issue["complexity"] = line.replace("COMPLEXITY:", "").strip()
                    elif line.startswith("IMPACT:"):
                        issue["impact"] = line.replace("IMPACT:", "").strip()
                    elif line.startswith("SOLUTION:"):
                        issue["solution"] = line.replace("SOLUTION:", "").strip()
                    j += 1
                
                issues.append(issue)
                i = j
            else:
                i += 1
        
        return issues
    
    async def analyze_complexity(self, code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform detailed complexity analysis
        
        Args:
            code: The code to analyze
            context: Additional context
            
        Returns:
            Complexity analysis results
        """
        prompt = f"""Analyze the time and space complexity of the following code:

```
{code}
```

For each function/method:
1. Identify the time complexity (best, average, worst case)
2. Identify the space complexity
3. Explain the reasoning
4. Suggest improvements if complexity can be reduced
5. Provide the improved code if applicable"""

        try:
            result = await self.agent.run(task=prompt)
            return {
                "agent": "performance_analyzer",
                "analysis_type": "complexity",
                "status": "success",
                "result": result
            }
        except Exception as e:
            return {
                "agent": "performance_analyzer",
                "analysis_type": "complexity",
                "status": "error",
                "error": str(e)
            }
    
    async def suggest_optimizations(self, code: str, performance_goals: List[str] = None) -> Dict[str, Any]:
        """Generate specific optimization suggestions
        
        Args:
            code: The code to optimize
            performance_goals: Specific goals (e.g., ["reduce memory", "improve latency"])
            
        Returns:
            Optimization suggestions
        """
        goals = performance_goals or ["general performance improvement"]
        goals_text = ", ".join(goals)
        
        prompt = f"""Provide optimization suggestions for the following code with these goals: {goals_text}

```
{code}
```

For each optimization:
1. Explain the current issue
2. Provide the optimized code
3. Quantify the expected improvement
4. Discuss any trade-offs
5. Consider maintainability impact"""

        try:
            result = await self.agent.run(task=prompt)
            return {
                "agent": "performance_analyzer",
                "analysis_type": "optimizations",
                "status": "success",
                "goals": performance_goals,
                "suggestions": result
            }
        except Exception as e:
            return {
                "agent": "performance_analyzer",
                "analysis_type": "optimizations",
                "status": "error",
                "error": str(e)
            }
    
    async def benchmark_comparison(self, implementations: List[Dict[str, str]]) -> Dict[str, Any]:
        """Compare performance characteristics of multiple implementations
        
        Args:
            implementations: List of dicts with 'name' and 'code' keys
            
        Returns:
            Comparative analysis
        """
        if len(implementations) < 2:
            return {
                "status": "error",
                "error": "At least 2 implementations required for comparison"
            }
        
        impl_text = "\n\n".join([
            f"=== Implementation: {impl['name']} ===\n```\n{impl['code']}\n```"
            for impl in implementations
        ])
        
        prompt = f"""Compare the performance characteristics of these implementations:

{impl_text}

Provide:
1. Time complexity comparison
2. Space complexity comparison
3. Pros and cons of each approach
4. Recommendation based on different scenarios
5. Benchmark estimates for different input sizes"""

        try:
            result = await self.agent.run(task=prompt)
            return {
                "agent": "performance_analyzer",
                "analysis_type": "benchmark_comparison",
                "status": "success",
                "implementations": [impl['name'] for impl in implementations],
                "comparison": result
            }
        except Exception as e:
            return {
                "agent": "performance_analyzer",
                "analysis_type": "benchmark_comparison",
                "status": "error",
                "error": str(e)
            }