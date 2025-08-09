"""
Security Checker Agent - Focuses on vulnerability detection and security best practices
"""

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
import os
from typing import Dict, List, Any
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.static_analyzer import run_static_analysis
from utils.logger import get_logger, track_performance

# Initialize logger
logger = get_logger(__name__)


class SecurityCheckerAgent:
    """Agent specialized in security vulnerability detection and prevention"""
    
    def __init__(self, api_key: str = None):
        """Initialize the Security Checker Agent
        
        Args:
            api_key: OpenAI API key (defaults to env var OPENAI_API_KEY)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
            
        self.model_client = OpenAIChatCompletionClient(
            model="gpt-4o",  # Using full model for better security detection
            temperature=0.1,
            api_key=self.api_key
        )
        
        self.agent = AssistantAgent(
            name="security_checker",
            model_client=self.model_client,
            system_message=self._get_system_message()
        )
    
    def _get_system_message(self) -> str:
        """Define the system message for the security checker agent"""
        return """You are an expert security analyst specializing in code security and vulnerability detection.
        
        Your responsibilities include detecting:
        1. **Injection Vulnerabilities**: SQL injection, command injection, LDAP injection, XPath injection
        2. **Cross-Site Scripting (XSS)**: Reflected, stored, and DOM-based XSS
        3. **Authentication Issues**: Weak authentication, missing auth checks, session management flaws
        4. **Authorization Problems**: Privilege escalation, IDOR, path traversal
        5. **Cryptographic Issues**: Weak algorithms, hardcoded secrets, improper key management
        6. **Input Validation**: Missing or insufficient input validation and sanitization
        7. **Information Disclosure**: Sensitive data exposure, verbose error messages
        8. **Security Misconfigurations**: Insecure defaults, unnecessary features enabled
        9. **Dependencies**: Known vulnerabilities in third-party libraries
        10. **OWASP Top 10**: All current OWASP Top 10 vulnerabilities
        
        For each vulnerability found, you MUST provide in this exact format:
        VULNERABILITY: [Name of vulnerability]
        SEVERITY: [Critical/High/Medium/Low]
        LOCATION: [Line numbers or code sections]
        DESCRIPTION: [Detailed explanation]
        IMPACT: [What an attacker could do]
        REMEDIATION: [How to fix it with code example]
        
        You MUST find and report ALL security issues. Look especially for:
        - String concatenation in SQL queries (SQL injection)
        - User input directly in templates (XSS)
        - Hardcoded passwords or secrets
        - eval() or exec() with user input
        - Weak hashing algorithms (MD5, SHA1)
        - Unsafe deserialization (pickle with user data)
        
        Be extremely thorough. This is a security review - missing vulnerabilities is unacceptable."""
    
    @track_performance("security_checker_analyze")
    async def analyze_code(self, code: str, filename: str = "unknown", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze code for security vulnerabilities
        
        Args:
            code: The code to analyze
            filename: Name of the file being analyzed
            context: Additional context (e.g., framework, dependencies)
            
        Returns:
            Dictionary containing security analysis results
        """
        logger.info("Starting security analysis", filename=filename)
        
        context = context or {}
        language = context.get("language", "auto-detect")
        framework = context.get("framework", "unknown")
        
        # Run static security analysis for Python code
        static_results = {}
        if language.lower() in ["python", "py", "auto-detect"]:
            logger.info("Running static security analysis with bandit")
            static_results = run_static_analysis(code, filename)
            
            # Extract bandit findings if available
            bandit_summary = ""
            if ("analyses" in static_results and 
                "bandit" in static_results["analyses"] and 
                static_results["analyses"]["bandit"]["status"] == "success"):
                
                bandit_data = static_results["analyses"]["bandit"]
                bandit_issues = bandit_data.get("security_issues", [])
                
                if bandit_issues:
                    bandit_summary = "\n\nStatic Security Analysis (Bandit) Results:\n"
                    for issue in bandit_issues:
                        bandit_summary += f"- Line {issue['line']}: {issue['test_name']} "
                        bandit_summary += f"(Severity: {issue['severity']}, Confidence: {issue['confidence']})\n"
                        bandit_summary += f"  {issue['text']}\n"
        
        prompt = f"""Please perform a security analysis of the following code from file '{filename}':

```{language}
{code}
```

Framework/Library: {framework if framework != 'unknown' else 'Auto-detect'}
{bandit_summary if 'bandit_summary' in locals() else ''}

Perform a comprehensive security review following the guidelines in your system message. 
Focus on identifying real vulnerabilities, not just theoretical issues.

If static analysis results are provided, incorporate them into your analysis and verify the findings."""

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
            
            vulnerabilities = self._extract_vulnerability_summary(analysis_text)
            
            result = {
                "agent": "security_checker",
                "filename": filename,
                "status": "success",
                "analysis": analysis_text,
                "vulnerabilities": vulnerabilities
            }
            
            # Add static analysis results if available
            if static_results:
                result["static_analysis"] = static_results
                
                # Merge static analysis findings
                if ("analyses" in static_results and 
                    "bandit" in static_results["analyses"] and 
                    static_results["analyses"]["bandit"]["status"] == "success"):
                    
                    bandit_metrics = static_results["analyses"]["bandit"]["metrics"]
                    result["vulnerabilities"]["static_high"] = bandit_metrics.get("severity_high", 0)
                    result["vulnerabilities"]["static_medium"] = bandit_metrics.get("severity_medium", 0)
                    result["vulnerabilities"]["static_low"] = bandit_metrics.get("severity_low", 0)
            
            logger.info("Security analysis completed",
                       filename=filename,
                       vulnerabilities_found=sum(vulnerabilities.values()),
                       has_static_analysis=bool(static_results))
            
            return result
        except Exception as e:
            logger.error("Security analysis failed",
                        exception=e,
                        filename=filename)
            
            return {
                "agent": "security_checker",
                "filename": filename,
                "status": "error",
                "error": str(e),
                "analysis": None,
                "static_analysis": static_results if 'static_results' in locals() else {}
            }
    
    def _extract_vulnerability_summary(self, analysis_text: str) -> Dict[str, int]:
        """Extract vulnerability counts from analysis text
        
        Categorize by severity levels
        """
        analysis_lower = analysis_text.lower()
        return {
            "critical": analysis_lower.count("critical severity") + analysis_lower.count("critical:"),
            "high": analysis_lower.count("high severity") + analysis_lower.count("high:"),
            "medium": analysis_lower.count("medium severity") + analysis_lower.count("medium:"),
            "low": analysis_lower.count("low severity") + analysis_lower.count("low:")
        }
    
    async def check_dependencies(self, dependencies: List[str], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Check dependencies for known vulnerabilities
        
        Args:
            dependencies: List of dependencies (package names with versions)
            context: Additional context
            
        Returns:
            Security analysis of dependencies
        """
        deps_formatted = "\n".join(dependencies)
        
        prompt = f"""Analyze the following dependencies for known security vulnerabilities:

{deps_formatted}

Check for:
1. Known CVEs in these specific versions
2. Outdated packages with security patches available
3. Packages with poor security track records
4. Suspicious or potentially malicious packages

Provide specific version recommendations for any vulnerable dependencies."""

        try:
            result = await self.agent.run(task=prompt)
            return {
                "agent": "security_checker",
                "analysis_type": "dependencies",
                "status": "success",
                "result": result
            }
        except Exception as e:
            return {
                "agent": "security_checker",
                "analysis_type": "dependencies",
                "status": "error",
                "error": str(e)
            }
    
    async def generate_security_report(self, vulnerabilities: List[Dict[str, Any]]) -> str:
        """Generate a consolidated security report
        
        Args:
            vulnerabilities: List of vulnerability findings
            
        Returns:
            Formatted security report
        """
        if not vulnerabilities:
            return "No security vulnerabilities detected."
        
        report_sections = []
        report_sections.append("# Security Analysis Report\n")
        
        # Summary statistics
        total_critical = sum(v.get("vulnerabilities", {}).get("critical", 0) for v in vulnerabilities)
        total_high = sum(v.get("vulnerabilities", {}).get("high", 0) for v in vulnerabilities)
        total_medium = sum(v.get("vulnerabilities", {}).get("medium", 0) for v in vulnerabilities)
        total_low = sum(v.get("vulnerabilities", {}).get("low", 0) for v in vulnerabilities)
        
        report_sections.append("## Summary")
        report_sections.append(f"- Critical: {total_critical}")
        report_sections.append(f"- High: {total_high}")
        report_sections.append(f"- Medium: {total_medium}")
        report_sections.append(f"- Low: {total_low}\n")
        
        # Detailed findings
        report_sections.append("## Detailed Findings\n")
        for vuln in vulnerabilities:
            if vuln.get("status") == "success":
                report_sections.append(f"### {vuln.get('filename', 'Unknown file')}")
                report_sections.append(vuln.get("analysis", "No analysis available"))
                report_sections.append("\n---\n")
        
        return "\n".join(report_sections)