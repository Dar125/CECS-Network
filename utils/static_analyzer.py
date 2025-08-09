"""
Static Analysis Tools Integration

Integrates popular static analysis tools like pylint and bandit for enhanced code analysis.
"""

import os
import subprocess
import tempfile
import json
from typing import Dict, List, Any, Optional
import sys

class StaticAnalyzer:
    """Integrates various static analysis tools"""
    
    def __init__(self):
        self.available_tools = self._check_available_tools()
    
    def _check_available_tools(self) -> Dict[str, bool]:
        """Check which static analysis tools are available"""
        tools = {
            "pylint": False,
            "bandit": False,
            "flake8": False,
            "mypy": False,
            "black": False
        }
        
        for tool in tools:
            try:
                subprocess.run([tool, "--version"], 
                             capture_output=True, 
                             check=False,
                             timeout=5)
                tools[tool] = True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                tools[tool] = False
        
        return tools
    
    def analyze_with_pylint(self, code: str, filename: str = "temp.py") -> Dict[str, Any]:
        """Run pylint analysis on code
        
        Args:
            code: Python source code
            filename: Name of the file (for reporting)
            
        Returns:
            Dictionary with pylint results
        """
        if not self.available_tools.get("pylint"):
            return {
                "tool": "pylint",
                "status": "unavailable",
                "error": "Pylint is not installed"
            }
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Run pylint with JSON output
            result = subprocess.run(
                ["pylint", temp_file, "--output-format=json", "--reports=n"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse results
            issues = []
            if result.stdout:
                try:
                    issues = json.loads(result.stdout)
                except json.JSONDecodeError:
                    # Fallback to text parsing if JSON fails
                    issues = self._parse_pylint_text(result.stdout)
            
            # Calculate score (pylint exit code indicates score)
            # Exit codes: 0=no error, 1=fatal, 2=error, 4=warning, 8=refactor, 16=convention
            score = 10.0  # Default perfect score
            if result.returncode > 0:
                # Rough score calculation based on exit code
                score = max(0, 10 - (result.returncode * 0.5))
            
            return {
                "tool": "pylint",
                "status": "success",
                "score": score,
                "issues": self._categorize_pylint_issues(issues),
                "total_issues": len(issues),
                "filename": filename
            }
            
        except subprocess.TimeoutExpired:
            return {
                "tool": "pylint",
                "status": "timeout",
                "error": "Pylint analysis timed out"
            }
        except Exception as e:
            return {
                "tool": "pylint",
                "status": "error",
                "error": str(e)
            }
        finally:
            # Clean up temp file
            if 'temp_file' in locals() and os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def analyze_with_bandit(self, code: str, filename: str = "temp.py") -> Dict[str, Any]:
        """Run bandit security analysis on code
        
        Args:
            code: Python source code
            filename: Name of the file (for reporting)
            
        Returns:
            Dictionary with bandit results
        """
        if not self.available_tools.get("bandit"):
            return {
                "tool": "bandit",
                "status": "unavailable",
                "error": "Bandit is not installed"
            }
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Run bandit with JSON output
            result = subprocess.run(
                ["bandit", temp_file, "-f", "json", "-ll"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse results
            security_issues = []
            metrics = {}
            
            if result.stdout:
                try:
                    bandit_output = json.loads(result.stdout)
                    security_issues = bandit_output.get("results", [])
                    metrics = bandit_output.get("metrics", {})
                except json.JSONDecodeError:
                    pass
            
            return {
                "tool": "bandit",
                "status": "success",
                "security_issues": self._categorize_bandit_issues(security_issues),
                "metrics": {
                    "total_issues": len(security_issues),
                    "severity_high": sum(1 for issue in security_issues if issue.get("issue_severity") == "HIGH"),
                    "severity_medium": sum(1 for issue in security_issues if issue.get("issue_severity") == "MEDIUM"),
                    "severity_low": sum(1 for issue in security_issues if issue.get("issue_severity") == "LOW"),
                    "confidence_high": sum(1 for issue in security_issues if issue.get("issue_confidence") == "HIGH"),
                    "confidence_medium": sum(1 for issue in security_issues if issue.get("issue_confidence") == "MEDIUM"),
                    "confidence_low": sum(1 for issue in security_issues if issue.get("issue_confidence") == "LOW")
                },
                "filename": filename
            }
            
        except subprocess.TimeoutExpired:
            return {
                "tool": "bandit",
                "status": "timeout",
                "error": "Bandit analysis timed out"
            }
        except Exception as e:
            return {
                "tool": "bandit",
                "status": "error",
                "error": str(e)
            }
        finally:
            # Clean up temp file
            if 'temp_file' in locals() and os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def analyze_all(self, code: str, filename: str = "temp.py") -> Dict[str, Any]:
        """Run all available static analysis tools
        
        Args:
            code: Python source code
            filename: Name of the file (for reporting)
            
        Returns:
            Combined results from all tools
        """
        results = {
            "filename": filename,
            "tools_available": self.available_tools,
            "analyses": {}
        }
        
        # Run pylint if available
        if self.available_tools.get("pylint"):
            results["analyses"]["pylint"] = self.analyze_with_pylint(code, filename)
        
        # Run bandit if available
        if self.available_tools.get("bandit"):
            results["analyses"]["bandit"] = self.analyze_with_bandit(code, filename)
        
        # Add summary
        results["summary"] = self._create_summary(results["analyses"])
        
        return results
    
    def _categorize_pylint_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize pylint issues by type"""
        categories = {
            "convention": [],
            "refactor": [],
            "warning": [],
            "error": [],
            "fatal": []
        }
        
        for issue in issues:
            category = issue.get("type", "").lower()
            if category in categories:
                categories[category].append({
                    "line": issue.get("line", 0),
                    "column": issue.get("column", 0),
                    "message": issue.get("message", ""),
                    "symbol": issue.get("symbol", ""),
                    "message_id": issue.get("message-id", "")
                })
        
        return categories
    
    def _categorize_bandit_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format bandit issues for easier consumption"""
        formatted_issues = []
        
        for issue in issues:
            formatted_issues.append({
                "line": issue.get("line_number", 0),
                "test_id": issue.get("test_id", ""),
                "test_name": issue.get("test_name", ""),
                "severity": issue.get("issue_severity", ""),
                "confidence": issue.get("issue_confidence", ""),
                "text": issue.get("issue_text", ""),
                "cwe": issue.get("issue_cwe", {})
            })
        
        return formatted_issues
    
    def _parse_pylint_text(self, output: str) -> List[Dict[str, Any]]:
        """Parse pylint text output as fallback"""
        issues = []
        lines = output.split('\n')
        
        for line in lines:
            # Basic parsing for pylint output format
            # Example: "module.py:10:0: C0103: Constant name "a" doesn't conform..."
            parts = line.split(':', 4)
            if len(parts) >= 5:
                try:
                    issues.append({
                        "line": int(parts[1]),
                        "column": int(parts[2]),
                        "type": parts[3].strip()[0].lower(),  # First letter indicates type
                        "message": parts[4].strip()
                    })
                except (ValueError, IndexError):
                    pass
        
        return issues
    
    def _create_summary(self, analyses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Create a summary of all analysis results"""
        summary = {
            "total_issues": 0,
            "security_issues": 0,
            "code_quality_issues": 0,
            "recommendations": []
        }
        
        # Pylint summary
        if "pylint" in analyses and analyses["pylint"]["status"] == "success":
            pylint_data = analyses["pylint"]
            summary["code_quality_issues"] = pylint_data["total_issues"]
            summary["total_issues"] += pylint_data["total_issues"]
            summary["pylint_score"] = pylint_data["score"]
            
            if pylint_data["score"] < 7.0:
                summary["recommendations"].append(
                    "Code quality score is below 7.0. Consider addressing pylint warnings."
                )
        
        # Bandit summary
        if "bandit" in analyses and analyses["bandit"]["status"] == "success":
            bandit_data = analyses["bandit"]
            summary["security_issues"] = bandit_data["metrics"]["total_issues"]
            summary["total_issues"] += bandit_data["metrics"]["total_issues"]
            
            if bandit_data["metrics"]["severity_high"] > 0:
                summary["recommendations"].append(
                    f"Found {bandit_data['metrics']['severity_high']} high-severity security issues. "
                    "These should be addressed immediately."
                )
        
        return summary


# Convenience function
def run_static_analysis(code: str, filename: str = "temp.py") -> Dict[str, Any]:
    """Run static analysis on code"""
    analyzer = StaticAnalyzer()
    return analyzer.analyze_all(code, filename)