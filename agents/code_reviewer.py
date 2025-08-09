"""
Code Reviewer Agent - Focuses on clean code principles, best practices, and documentation
"""

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
import os
from typing import Dict, List, Any
import time
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import get_logger, track_performance, api_tracker

# Initialize logger
logger = get_logger(__name__)


class CodeReviewerAgent:
    """Agent specialized in code quality, best practices, and maintainability"""
    
    def __init__(self, api_key: str = None):
        """Initialize the Code Reviewer Agent
        
        Args:
            api_key: OpenAI API key (defaults to env var OPENAI_API_KEY)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        logger.info("Initializing CodeReviewerAgent")
            
        self.model_client = OpenAIChatCompletionClient(
            model="gpt-4o",  # Using full model for better analysis
            temperature=0.1,
            api_key=self.api_key
        )
        
        self.agent = AssistantAgent(
            name="code_reviewer",
            model_client=self.model_client,
            system_message=self._get_system_message()
        )
    
    def _get_system_message(self) -> str:
        """Define the system message for the code reviewer agent"""
        return """You are an expert code reviewer focusing on clean code principles and best practices.
        
        Your responsibilities include:
        1. **Code Quality**: Evaluate code readability, maintainability, and adherence to SOLID principles
        2. **Best Practices**: Check for language-specific best practices and idiomatic code
        3. **Documentation**: Assess code documentation, comments, and docstrings
        4. **Naming Conventions**: Review variable, function, and class naming
        5. **Code Structure**: Analyze overall architecture and organization
        6. **Error Handling**: Evaluate error handling and edge cases
        7. **Testing**: Check for testability and suggest test cases
        
        For each code quality issue found, you MUST provide in this exact format:
        ISSUE: [Name of code quality issue]
        SEVERITY: [Critical/High/Medium/Low]
        LOCATION: [Function/class name and line numbers]
        DESCRIPTION: [Detailed explanation of the issue]
        SUGGESTION: [How to improve the code]
        
        You MUST find and report ALL code quality issues. Look especially for:
        - Functions with too many parameters (>5)
        - Global variables and state mutation
        - Poor error handling or missing validation
        - Hardcoded values that should be constants
        - Code duplication
        - Functions doing too many things (SRP violation)
        - Poor naming conventions
        - Missing or inadequate documentation
        - Debug code in production
        
        Be constructive and educational in your feedback. Focus on the most impactful improvements."""
    
    @track_performance("code_reviewer_analyze")
    async def analyze_code(self, code: str, filename: str = "unknown", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze code and provide review feedback
        
        Args:
            code: The code to review
            filename: Name of the file being reviewed
            context: Additional context (e.g., PR description, language)
            
        Returns:
            Dictionary containing review results
        """
        start_time = time.time()
        context = context or {}
        language = context.get("language", "auto-detect")
        pr_description = context.get("pr_description", "")
        
        logger.info("Starting code review analysis",
                   filename=filename,
                   code_length=len(code),
                   language=language)
        
        prompt = f"""Please review the following code from file '{filename}':

```{language}
{code}
```

PR Description: {pr_description if pr_description else 'Not provided'}

Provide a comprehensive code review following the guidelines in your system message."""

        try:
            # Track API call
            api_start = time.time()
            result = await self.agent.run(task=prompt)
            api_duration = time.time() - api_start
            
            # Estimate tokens (rough approximation)
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = 500  # Estimated average response
            
            # Extract the actual message content from AutoGen response
            if hasattr(result, 'messages') and len(result.messages) > 0:
                # Get the last assistant message
                review_text = result.messages[-1].content
            elif hasattr(result, 'content'):
                review_text = result.content
            elif isinstance(result, str):
                review_text = result
            else:
                review_text = str(result)
            
            # Track API usage
            api_tracker.track_call(
                api_name="openai",
                model="gpt-4o",
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
                duration=api_duration
            )
            
            issues_found = self._extract_issue_count(review_text)
            total_issues = sum(issues_found.values())
            
            logger.info("Code review analysis completed",
                       filename=filename,
                       total_issues=total_issues,
                       issues_breakdown=issues_found,
                       duration=time.time() - start_time)
            
            return {
                "agent": "code_reviewer",
                "filename": filename,
                "status": "success",
                "review": review_text,
                "issues_found": issues_found,
                "issues": self._extract_issues(review_text),
                "metrics": {
                    "analysis_time": time.time() - start_time,
                    "api_call_time": api_duration
                }
            }
        except Exception as e:
            logger.error("Code review analysis failed",
                        exception=e,
                        filename=filename)
            
            return {
                "agent": "code_reviewer",
                "filename": filename,
                "status": "error",
                "error": str(e),
                "review": None,
                "metrics": {
                    "analysis_time": time.time() - start_time
                }
            }
    
    def _extract_issue_count(self, review_text: str) -> Dict[str, int]:
        """Extract issue counts from review text
        
        Simple heuristic to count issues by severity
        """
        review_lower = review_text.lower()
        return {
            "high": review_lower.count("high severity") + review_lower.count("critical"),
            "medium": review_lower.count("medium severity") + review_lower.count("moderate"),
            "low": review_lower.count("low severity") + review_lower.count("minor")
        }
    
    def _extract_issues(self, review_text: str) -> List[Dict[str, str]]:
        """Extract structured issues from review text"""
        issues = []
        lines = review_text.split('\n')
        
        i = 0
        while i < len(lines):
            if lines[i].strip().startswith("ISSUE:"):
                issue = {"name": lines[i].replace("ISSUE:", "").strip()}
                
                # Look for description and suggestion
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith("ISSUE:"):
                    if lines[j].strip().startswith("DESCRIPTION:"):
                        issue["description"] = lines[j].replace("DESCRIPTION:", "").strip()
                    elif lines[j].strip().startswith("SUGGESTION:"):
                        issue["suggestion"] = lines[j].replace("SUGGESTION:", "").strip()
                    j += 1
                
                issues.append(issue)
                i = j
            else:
                i += 1
        
        return issues
    
    async def batch_analyze(self, files: List[Dict[str, str]], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Analyze multiple files
        
        Args:
            files: List of dicts with 'filename' and 'content' keys
            context: Additional context for all files
            
        Returns:
            List of review results
        """
        results = []
        for file_info in files:
            result = await self.analyze_code(
                code=file_info["content"],
                filename=file_info["filename"],
                context=context
            )
            results.append(result)
        return results