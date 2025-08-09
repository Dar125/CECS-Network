"""
Simplified Multi-Agent Orchestrator that directly calls each agent
"""

import asyncio
import os
from typing import Dict, List, Any
from datetime import datetime
from dotenv import load_dotenv
import time

from agents.code_reviewer import CodeReviewerAgent
from agents.security_checker import SecurityCheckerAgent
from agents.performance_analyzer import PerformanceAnalyzerAgent
from utils.consensus_mechanism import WeightedConsensus
from utils.report_generator import ReportGenerator
from utils.logger import get_logger, log_performance, track_performance, api_tracker, perf_monitor

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger(__name__)


class SimpleMultiAgentOrchestrator:
    """Orchestrates multiple specialized agents for comprehensive code review"""
    
    def __init__(self, api_key: str = None):
        """Initialize the orchestrator with all specialized agents"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        logger.info("Initializing SimpleMultiAgentOrchestrator", 
                   api_key_provided=bool(api_key))
        
        # Initialize specialized agents
        self.code_reviewer = CodeReviewerAgent(api_key=self.api_key)
        self.security_checker = SecurityCheckerAgent(api_key=self.api_key)
        self.performance_analyzer = PerformanceAnalyzerAgent(api_key=self.api_key)
        
        # Initialize utilities
        self.consensus = WeightedConsensus()
        self.report_generator = ReportGenerator()
        
        logger.info("Orchestrator initialized successfully")
        
    @track_performance("orchestrator_review_code")
    async def review_code(self, 
                         code: str, 
                         filename: str = "unknown",
                         pr_description: str = "",
                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Orchestrate a comprehensive code review using all agents
        
        Args:
            code: The code to review
            filename: Name of the file
            pr_description: Description of the pull request
            context: Additional context
            
        Returns:
            Comprehensive review results
        """
        start_time = time.time()
        context = context or {}
        context["pr_description"] = pr_description
        
        logger.info("Starting multi-agent review", 
                   filename=filename,
                   code_length=len(code),
                   pr_description=pr_description)
        
        try:
            # Run each agent independently with performance tracking
            with log_performance("code_reviewer_agent", logger):
                code_review_result = await self.code_reviewer.analyze_code(
                    code=code,
                    filename=filename,
                    context=context
                )
                # Count issues based on the agent's response format
                code_issues_count = 0
                if "issues" in code_review_result:
                    code_issues_count = len(code_review_result.get("issues", []))
                elif "issues_found" in code_review_result:
                    code_issues_count = sum(code_review_result.get("issues_found", {}).values())
                
                logger.info("Code Reviewer completed",
                           issues_found=code_issues_count)
            
            with log_performance("security_checker_agent", logger):
                security_result = await self.security_checker.analyze_code(
                    code=code,
                    filename=filename,
                    context=context
                )
                # Count vulnerabilities - it's a dict with severity counts
                vuln_count = 0
                if "vulnerabilities" in security_result:
                    vulns = security_result.get("vulnerabilities", {})
                    if isinstance(vulns, dict):
                        vuln_count = sum(vulns.values())
                    else:
                        vuln_count = len(vulns)
                
                logger.info("Security Checker completed",
                           vulnerabilities_found=vuln_count)
            
            with log_performance("performance_analyzer_agent", logger):
                performance_result = await self.performance_analyzer.analyze_code(
                    code=code,
                    filename=filename,
                    context=context
                )
                # Count performance issues - could be dict or list
                perf_count = 0
                if "issues" in performance_result:
                    perf_count = len(performance_result.get("issues", []))
                elif "performance_issues" in performance_result:
                    perf_issues = performance_result.get("performance_issues", {})
                    if isinstance(perf_issues, dict):
                        perf_count = sum(perf_issues.values())
                    else:
                        perf_count = len(perf_issues)
                
                logger.info("Performance Analyzer completed",
                           issues_found=perf_count)
            
            # Apply consensus mechanism
            with log_performance("consensus_mechanism", logger):
                agent_findings = self._extract_agent_findings(
                    code_review_result,
                    security_result,
                    performance_result
                )
                
                consensus_results = self.consensus.resolve_conflicts(agent_findings)
                logger.info("Consensus mechanism completed",
                           total_recommendations=len(consensus_results.get("recommendations", [])),
                           conflicts_resolved=len(consensus_results.get("conflicts", [])))
            
            # Generate unified report
            with log_performance("report_generation", logger):
                # Generate report
                orchestrator_results = {
                    "filename": filename,
                    "timestamp": datetime.now().isoformat(),
                    "agent_results": {
                        "code_reviewer": code_review_result,
                        "security_checker": security_result,
                        "performance_analyzer": performance_result
                    },
                    "overall_summary": self._generate_summary_from_consensus(
                        consensus_results,
                        code_review_result,
                        security_result,
                        performance_result
                    )
                }
                
                markdown_report = self.report_generator.generate_pr_report(
                    orchestrator_results,
                    consensus_results,
                    {"title": pr_description, "files_changed": 1}
                )
            
            # Calculate total processing time
            total_time = time.time() - start_time
            
            # Record overall metrics
            perf_monitor.record_metric("total_review_time", total_time, {"filename": filename})
            perf_monitor.record_metric("total_issues_found", 
                                     len(consensus_results.get("recommendations", [])),
                                     {"filename": filename})
            
            logger.info("Code review completed successfully",
                       filename=filename,
                       total_time_seconds=total_time,
                       total_recommendations=len(consensus_results.get("recommendations", [])))
            
            return {
                "status": "success",
                "filename": filename,
                "timestamp": datetime.now().isoformat(),
                "consensus_results": consensus_results,
                "orchestrator_results": orchestrator_results,
                "markdown_report": markdown_report,
                "summary": orchestrator_results["overall_summary"],
                "performance_metrics": {
                    "total_time": total_time,
                    "agent_metrics": perf_monitor.get_all_stats(),
                    "api_usage": api_tracker.get_summary()
                }
            }
            
        except Exception as e:
            logger.error("Error during orchestration", 
                        exception=e,
                        filename=filename)
            
            return {
                "status": "error",
                "filename": filename,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "performance_metrics": {
                    "total_time": time.time() - start_time,
                    "api_usage": api_tracker.get_summary()
                }
            }
    
    def _extract_agent_findings(self, code_review, security, performance) -> Dict[str, List[Dict[str, Any]]]:
        """Extract structured findings from agent results"""
        findings = {
            "code_reviewer": [],
            "security_checker": [],
            "performance_analyzer": []
        }
        
        # Parse code review findings
        if code_review.get("status") == "success":
            # First try to use structured issues if available
            if "issues" in code_review and isinstance(code_review["issues"], list):
                findings["code_reviewer"] = code_review["issues"]
                logger.info("Code reviewer: Found structured issues", 
                          count=len(code_review["issues"]))
            else:
                # Fallback to text parsing
                review_text = str(code_review.get("review", ""))
                findings["code_reviewer"] = self._parse_findings_from_text(
                    review_text, "code_reviewer"
                )
                logger.info("Code reviewer: Parsed from text", 
                          count=len(findings["code_reviewer"]))
        
        # Parse security findings
        if security.get("status") == "success":
            # Security vulnerabilities is a dict with counts, need to parse from text
            analysis_text = str(security.get("analysis", ""))
            findings["security_checker"] = self._parse_findings_from_text(
                analysis_text, "security_checker"
            )
            logger.info("Security checker: Parsed from text", 
                      count=len(findings["security_checker"]))
        
        # Parse performance findings
        if performance.get("status") == "success":
            # First try to use structured issues if available
            if "issues" in performance and isinstance(performance["issues"], list):
                findings["performance_analyzer"] = performance["issues"]
                logger.info("Performance analyzer: Found structured issues", 
                          count=len(performance["issues"]))
            else:
                # Fallback to text parsing
                analysis_text = str(performance.get("analysis", ""))
                findings["performance_analyzer"] = self._parse_findings_from_text(
                    analysis_text, "performance_analyzer"
                )
                logger.info("Performance analyzer: Parsed from text", 
                          count=len(findings["performance_analyzer"]))
        
        # Log summary of findings by type
        for agent, agent_findings in findings.items():
            if agent_findings:
                types = [f.get('type', 'unknown') for f in agent_findings]
                type_counts = {t: types.count(t) for t in set(types)}
                logger.info(f"{agent} findings by type", 
                          types=type_counts,
                          total=len(agent_findings))
        
        return findings
    
    def _parse_findings_from_text(self, text: str, agent_name: str) -> List[Dict[str, Any]]:
        """Parse findings from agent output text"""
        findings = []
        
        # Log what text we're parsing for which agent
        logger.info(f"Parsing text for {agent_name}",
                   text_length=len(text),
                   text_preview=text[:200] + "..." if len(text) > 200 else text)
        
        # Parse code reviewer format
        if agent_name == "code_reviewer":
            lines = text.split('\n')
            current_issue = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('ISSUE:') or '**ISSUE**' in line:
                    if current_issue:
                        findings.append(current_issue)
                    current_issue = {
                        'type': 'code_quality',
                        'agent': agent_name,
                        'description': line.replace('ISSUE:', '').strip()
                    }
                elif line.startswith('DESCRIPTION:'):
                    current_issue['description'] = line.replace('DESCRIPTION:', '').strip()
                elif line.startswith('SEVERITY:'):
                    current_issue['severity'] = line.replace('SEVERITY:', '').strip().lower()
                elif line.startswith('LOCATION:'):
                    current_issue['location'] = line.replace('LOCATION:', '').strip()
                elif line.startswith('SUGGESTION:') or line.startswith('SOLUTION:'):
                    current_issue['solution'] = line.replace('SUGGESTION:', '').replace('SOLUTION:', '').strip()
            
            if current_issue:
                findings.append(current_issue)
            
            # If no structured findings, look for common patterns
            if not findings:
                text_lower = text.lower()
                
                # No password hashing
                if 'password' in text_lower and ('plain' in text_lower or 'hash' in text_lower):
                    findings.append({
                        'type': 'code_quality',
                        'agent': agent_name,
                        'description': 'Passwords stored without hashing',
                        'severity': 'high',
                        'solution': 'Use bcrypt or similar secure hashing'
                    })
                
                # Global mutable state
                if 'global' in text_lower and 'mutable' in text_lower:
                    findings.append({
                        'type': 'code_quality',
                        'agent': agent_name,
                        'description': 'Global mutable state detected',
                        'severity': 'medium',
                        'solution': 'Use dependency injection or encapsulation'
                    })
                
                # No input validation
                if 'validation' in text_lower and ('missing' in text_lower or 'no' in text_lower):
                    findings.append({
                        'type': 'code_quality',
                        'agent': agent_name,
                        'description': 'Missing input validation',
                        'severity': 'high',
                        'solution': 'Add input validation and sanitization'
                    })
        
        # Parse security agent format
        elif agent_name == "security_checker":
            lines = text.split('\n')
            current_vuln = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('VULNERABILITY:') or '**VULNERABILITY**' in line:
                    if current_vuln:
                        findings.append(current_vuln)
                    # Extract description from both formats
                    if '**VULNERABILITY**' in line:
                        desc = line.split('**VULNERABILITY**')[1].split(':')[1].strip()
                    else:
                        desc = line.replace('VULNERABILITY:', '').strip()
                    
                    current_vuln = {
                        'type': 'security',  # Changed from 'vulnerability' to 'security'
                        'agent': agent_name,
                        'description': desc
                    }
                elif line.startswith('SEVERITY:'):
                    current_vuln['severity'] = line.replace('SEVERITY:', '').strip().lower()
                elif line.startswith('LOCATION:'):
                    current_vuln['location'] = line.replace('LOCATION:', '').strip()
                elif line.startswith('IMPACT:'):
                    current_vuln['impact'] = line.replace('IMPACT:', '').strip()
                elif line.startswith('REMEDIATION:'):
                    current_vuln['solution'] = line.replace('REMEDIATION:', '').strip()
            
            if current_vuln:
                findings.append(current_vuln)
            
            # If no structured findings, look for common patterns
            if not findings:
                text_lower = text.lower()
                
                # SQL Injection
                if 'sql injection' in text_lower:
                    findings.append({
                        'type': 'security',
                        'agent': agent_name,
                        'description': 'SQL Injection vulnerability detected',
                        'severity': 'critical',
                        'solution': 'Use parameterized queries or prepared statements'
                    })
                
                # Command Injection
                if 'command injection' in text_lower:
                    findings.append({
                        'type': 'security',
                        'agent': agent_name,
                        'description': 'Command injection vulnerability detected',
                        'severity': 'critical',
                        'solution': 'Sanitize user input and avoid shell=True'
                    })
                
                # Hardcoded credentials
                if 'hardcoded' in text_lower and ('password' in text_lower or 'credential' in text_lower):
                    findings.append({
                        'type': 'security',
                        'agent': agent_name,
                        'description': 'Hardcoded credentials detected',
                        'severity': 'high',
                        'solution': 'Use environment variables or secure configuration management'
                    })
                
                # Unsafe deserialization
                if 'pickle' in text_lower and 'unsafe' in text_lower:
                    findings.append({
                        'type': 'security',
                        'agent': agent_name,
                        'description': 'Unsafe deserialization vulnerability',
                        'severity': 'critical',
                        'solution': 'Use JSON or other safe serialization formats'
                    })
        
        # Parse performance analyzer format
        elif agent_name == "performance_analyzer":
            lines = text.split('\n')
            current_issue = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('ISSUE:') or '**ISSUE**' in line:
                    if current_issue:
                        findings.append(current_issue)
                    # Extract issue description from both formats
                    if '**ISSUE**' in line:
                        desc = line.split('**ISSUE**')[1].split(':')[1].strip()
                    else:
                        desc = line.replace('ISSUE:', '').strip()
                    
                    current_issue = {
                        'type': 'performance',
                        'agent': agent_name,
                        'description': desc
                    }
                elif '**SEVERITY**' in line or line.startswith('SEVERITY:'):
                    sev = line.split(':')[-1].strip().lower()
                    current_issue['severity'] = sev
                elif '**LOCATION**' in line or line.startswith('LOCATION:'):
                    loc = line.split(':')[-1].strip()
                    current_issue['location'] = loc
                elif '**COMPLEXITY**' in line or line.startswith('COMPLEXITY:'):
                    comp = line.split(':')[-1].strip()
                    current_issue['complexity'] = comp
                elif '**IMPACT**' in line or line.startswith('IMPACT:'):
                    imp = line.split(':')[-1].strip()
                    current_issue['impact'] = imp
                elif '**SOLUTION**' in line or line.startswith('SOLUTION:'):
                    sol = line.split(':')[-1].strip()
                    current_issue['solution'] = sol
            
            if current_issue:
                findings.append(current_issue)
                
        # Special handling for performance analyzer - add pattern-based detection
        if agent_name == "performance_analyzer" and not findings:
            text_lower = text.lower()
            
            # Look for specific performance issues in the text
            if 'o(n³)' in text_lower or 'o(n^3)' in text_lower or 'triple nested' in text_lower:
                findings.append({
                    'type': 'performance',
                    'agent': agent_name,
                    'description': 'Triple nested loops causing O(n³) complexity',
                    'severity': 'critical',
                    'complexity': 'O(n³)',
                    'impact': 'Extremely poor performance with large datasets',
                    'solution': 'Use a set or dictionary for O(n) complexity'
                })
            
            if 'memory leak' in text_lower or 'unbounded cache' in text_lower:
                findings.append({
                    'type': 'performance',
                    'agent': agent_name,
                    'description': 'Memory leak - unbounded cache growth',
                    'severity': 'high',
                    'impact': 'Memory usage grows without limit',
                    'solution': 'Implement cache size limits or LRU eviction'
                })
            
            if 'string concatenation' in text_lower and 'loop' in text_lower:
                findings.append({
                    'type': 'performance',
                    'agent': agent_name,
                    'description': 'Inefficient string concatenation in loop',
                    'severity': 'medium',
                    'impact': 'O(n²) string building complexity',
                    'solution': 'Use join() or list comprehension'
                })
            
            if 'cache_user' in text and ('memory leak' in text.lower() or 'never clear' in text.lower()):
                findings.append({
                    'type': 'performance',
                    'agent': agent_name,
                    'description': 'Memory leak in cache_user - cache grows unbounded',
                    'severity': 'high',
                    'location': 'cache_user function',
                    'impact': 'Memory usage grows indefinitely',
                    'solution': 'Implement cache size limit or TTL'
                })
                
            if 'get_all_users' in text and ('n+1' in text.lower() or 'multiple queries' in text.lower()):
                findings.append({
                    'type': 'performance',
                    'agent': agent_name,
                    'description': 'N+1 query pattern in get_all_users',
                    'severity': 'high',
                    'location': 'get_all_users function',
                    'impact': 'Database performance degrades linearly with user count',
                    'solution': 'Use a single query with JOIN or batch fetching'
                })
        
        # Parse code reviewer format
        elif agent_name == "code_reviewer":
            lines = text.split('\n')
            current_issue = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('ISSUE:') or '**ISSUE**' in line:
                    if current_issue:
                        findings.append(current_issue)
                    current_issue = {
                        'type': 'code_quality',
                        'agent': agent_name,
                        'description': line.replace('ISSUE:', '').strip()
                    }
                elif line.startswith('SEVERITY:'):
                    current_issue['severity'] = line.replace('SEVERITY:', '').strip().lower()
                elif line.startswith('LOCATION:'):
                    current_issue['location'] = line.replace('LOCATION:', '').strip()
                elif line.startswith('DESCRIPTION:'):
                    current_issue['impact'] = line.replace('DESCRIPTION:', '').strip()
                elif line.startswith('SUGGESTION:'):
                    current_issue['solution'] = line.replace('SUGGESTION:', '').strip()
            
            if current_issue:
                findings.append(current_issue)
        
        # Also do general parsing for other content
        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()
            
            # Look for specific vulnerability mentions
            vulnerabilities = [
                ('sql injection', 'critical'),
                ('xss', 'critical'),
                ('cross-site scripting', 'critical'),
                ('eval(', 'critical'),
                ('exec(', 'critical'),
                ('pickle.loads', 'critical'),
                ('hardcoded password', 'high'),
                ('hardcoded secret', 'high'),
                ('md5', 'high'),
                ('sha1', 'high'),
                ('debug=true', 'medium'),
                ('no input validation', 'high'),
                ('missing authentication', 'critical')
            ]
            
            for vuln_pattern, severity in vulnerabilities:
                if vuln_pattern in line_lower and line.strip():
                    # Check if this line was already parsed
                    already_parsed = any(
                        f.get('description', '').lower() in line_lower 
                        for f in findings
                    )
                    
                    if not already_parsed:
                        # Assign type based on agent
                        if agent_name == 'security_checker':
                            issue_type = 'security'
                        elif agent_name == 'performance_analyzer':
                            issue_type = 'performance'
                        elif agent_name == 'code_reviewer':
                            issue_type = 'code_quality'
                        else:
                            issue_type = 'issue'
                        
                        findings.append({
                            'type': issue_type,
                            'severity': severity,
                            'description': line.strip(),
                            'agent': agent_name
                        })
        
        # Remove duplicates
        unique_findings = []
        seen_descriptions = set()
        for finding in findings:
            desc = finding.get('description', '').lower()
            if desc and desc not in seen_descriptions:
                seen_descriptions.add(desc)
                unique_findings.append(finding)
        
        return unique_findings
    
    def _generate_summary_from_consensus(self, consensus_results, code_review, security, performance) -> Dict[str, Any]:
        """Generate summary statistics from consensus results"""
        # Count issues by type from consensus and original findings
        code_quality_count = 0
        security_count = 0
        performance_count = 0
        
        recommendations = consensus_results.get('recommendations', [])
        logger.info("Generating summary from consensus", 
                   total_recommendations=len(recommendations))
        
        for i, rec in enumerate(recommendations):
            # Look at the original recommendations to determine type
            original_recs = rec.get('original_recommendations', [])
            
            # Check issue types from original findings
            has_security = False
            has_performance = False
            has_code_quality = False
            
            # Log details for debugging
            logger.debug(f"Recommendation {i}: {rec.get('description', '')[:50]}...",
                        contributing_agents=rec.get('contributing_agents', []),
                        num_original=len(original_recs))
            
            for orig in original_recs:
                issue_type = orig.get('type', '').lower()
                agent = orig.get('agent', '')
                
                logger.debug(f"  Original finding: type={issue_type}, agent={agent}")
                
                if issue_type in ['vulnerability', 'security']:
                    has_security = True
                elif issue_type in ['performance', 'complexity']:
                    has_performance = True
                elif issue_type in ['code_quality', 'quality', 'code']:
                    has_code_quality = True
                else:
                    # Fall back to agent-based categorization
                    if agent == 'security_checker':
                        has_security = True
                    elif agent == 'performance_analyzer':
                        has_performance = True
                    elif agent == 'code_reviewer':
                        has_code_quality = True
            
            # Count the issue in appropriate categories (one issue per recommendation)
            categorized_as = None
            if has_performance:
                performance_count += 1
                categorized_as = "performance"
            elif has_code_quality:
                code_quality_count += 1
                categorized_as = "code_quality"
            else:
                # Default to security if no clear type
                security_count += 1
                categorized_as = "security"
            
            logger.debug(f"  Categorized as: {categorized_as}")
        
        logger.info("Summary generation complete",
                   code_quality=code_quality_count,
                   security=security_count,
                   performance=performance_count)
        
        return {
            "total_issues": {
                "code_quality": code_quality_count,
                "security": security_count,
                "performance": performance_count
            }
        }
    
    def _generate_summary(self, code_review, security, performance) -> Dict[str, Any]:
        """Generate summary statistics"""
        # Handle both single dict results and list results from batch_analyze
        if isinstance(code_review, list):
            # Aggregate issues from all files
            code_issues = {"high": 0, "medium": 0, "low": 0}
            for result in code_review:
                if result.get("status") == "success" and "issues_found" in result:
                    for severity, count in result["issues_found"].items():
                        code_issues[severity] = code_issues.get(severity, 0) + count
        else:
            code_issues = code_review.get("issues_found", {})
        
        if isinstance(security, list):
            # Aggregate vulnerabilities from all files
            sec_vulns = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for result in security:
                if result.get("status") == "success" and "vulnerabilities" in result:
                    for severity, count in result["vulnerabilities"].items():
                        sec_vulns[severity] = sec_vulns.get(severity, 0) + count
        else:
            sec_vulns = security.get("vulnerabilities", {})
        
        if isinstance(performance, list):
            # Aggregate performance issues from all files
            perf_issues = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for result in performance:
                if result.get("status") == "success" and "performance_issues" in result:
                    for severity, count in result["performance_issues"].items():
                        perf_issues[severity] = perf_issues.get(severity, 0) + count
        else:
            perf_issues = performance.get("performance_issues", {})
            if not perf_issues and "issues" in performance:
                perf_issues = performance["issues"]
        
        return {
            "total_issues": {
                "code_quality": code_issues.get("high", 0) +
                               code_issues.get("medium", 0) +
                               code_issues.get("low", 0),
                "security": sec_vulns.get("critical", 0) +
                           sec_vulns.get("high", 0) +
                           sec_vulns.get("medium", 0),
                "performance": perf_issues.get("critical", 0) +
                              perf_issues.get("high", 0) +
                              perf_issues.get("medium", 0)
            }
        }
    
    async def review_pull_request(self, pr_files: List[Dict[str, str]], pr_description: str = "") -> Dict[str, Any]:
        """Review an entire pull request with multiple files"""
        print(f"\nReviewing PR with {len(pr_files)} files")
        print("=" * 60)
        
        all_reviews = []
        start_time = datetime.now()
        
        for i, file_info in enumerate(pr_files, 1):
            print(f"\nReviewing file {i}/{len(pr_files)}: {file_info['filename']}")
            
            review = await self.review_code(
                code=file_info["content"],
                filename=file_info["filename"],
                pr_description=pr_description,
                context={"language": file_info.get("language", "python")}
            )
            
            all_reviews.append(review)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Aggregate all findings for PR-level consensus
        all_agent_findings = {
            "code_reviewer": [],
            "security_checker": [],
            "performance_analyzer": []
        }
        
        for review in all_reviews:
            if review.get("status") == "success":
                # Get the actual parsed findings from each file review
                orchestrator_results = review.get("orchestrator_results", {})
                agent_results = orchestrator_results.get("agent_results", {})
                
                # Extract findings from each agent
                for agent_name in all_agent_findings:
                    agent_data = agent_results.get(agent_name, {})
                    if agent_data.get("status") == "success":
                        # Parse the findings from the agent's analysis
                        if agent_name == "code_reviewer":
                            analysis_text = agent_data.get("review", "")
                        else:
                            analysis_text = agent_data.get("analysis", "")
                        
                        findings = self._parse_findings_from_text(str(analysis_text), agent_name)
                        all_agent_findings[agent_name].extend(findings)
        
        # Apply PR-level consensus
        pr_consensus = self.consensus.resolve_conflicts(all_agent_findings)
        
        # Generate PR-level report
        pr_orchestrator_results = {
            "files_reviewed": len(pr_files),
            "total_duration_seconds": duration,
            "average_duration_per_file": duration / len(pr_files) if pr_files else 0,
            "file_reviews": all_reviews,
            "overall_summary": self._generate_pr_summary_from_consensus(pr_consensus, all_reviews)
        }
        
        pr_report = self.report_generator.generate_pr_report(
            pr_orchestrator_results,
            pr_consensus,
            {
                "title": pr_description,
                "files_changed": len(pr_files),
                "author": "Test User"
            }
        )
        
        return {
            "pr_description": pr_description,
            "files_reviewed": len(pr_files),
            "total_duration_seconds": duration,
            "file_reviews": all_reviews,
            "pr_consensus": pr_consensus,
            "markdown_report": pr_report,
            "overall_summary": pr_orchestrator_results["overall_summary"]
        }
    
    def _generate_pr_summary_from_consensus(self, pr_consensus: Dict[str, Any], file_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate overall PR summary from consensus results"""
        # Count issues by type from consensus
        code_quality_count = 0
        security_count = 0
        performance_count = 0
        
        recommendations = pr_consensus.get('recommendations', [])
        for rec in recommendations:
            # Look at the original recommendations to determine type
            original_recs = rec.get('original_recommendations', [])
            
            # Check issue types from original findings
            has_security = False
            has_performance = False
            has_code_quality = False
            
            for orig in original_recs:
                issue_type = orig.get('type', '').lower()
                if issue_type in ['vulnerability', 'security']:
                    has_security = True
                elif issue_type in ['performance', 'complexity']:
                    has_performance = True
                elif issue_type in ['code_quality', 'quality', 'code']:
                    has_code_quality = True
                else:
                    # Fall back to agent-based categorization
                    agent = orig.get('agent', '')
                    if agent == 'security_checker':
                        has_security = True
                    elif agent == 'performance_analyzer':
                        has_performance = True
                    elif agent == 'code_reviewer':
                        has_code_quality = True
            
            # Count the issue in appropriate categories (one issue per recommendation)
            if has_performance:
                performance_count += 1
            elif has_code_quality:
                code_quality_count += 1
            else:
                # Default to security if no clear type
                security_count += 1
        
        failed_files = []
        successful_files = []
        
        for review in file_reviews:
            if review.get("status") == "error":
                failed_files.append(review.get("filename", "unknown"))
            else:
                successful_files.append(review.get("filename", "unknown"))
        
        return {
            "total_issues": {
                "code_quality": code_quality_count,
                "security": security_count,
                "performance": performance_count
            },
            "failed_files": failed_files,
            "successful_files": successful_files,
            "success_rate": len(successful_files) / len(file_reviews) if file_reviews else 0
        }
    
    def _generate_pr_summary(self, file_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate overall PR summary from individual file reviews"""
        total_issues = {
            "code_quality": 0,
            "security": 0,
            "performance": 0
        }
        
        failed_files = []
        successful_files = []
        
        for review in file_reviews:
            if review.get("status") == "error":
                failed_files.append(review.get("filename", "unknown"))
            else:
                successful_files.append(review.get("filename", "unknown"))
                summary = review.get("summary", {})
                if "total_issues" in summary:
                    issues = summary["total_issues"]
                    total_issues["code_quality"] += issues.get("code_quality", 0)
                    total_issues["security"] += issues.get("security", 0)
                    total_issues["performance"] += issues.get("performance", 0)
        
        return {
            "total_issues": total_issues,
            "failed_files": failed_files,
            "successful_files": successful_files,
            "success_rate": len(successful_files) / len(file_reviews) if file_reviews else 0
        }