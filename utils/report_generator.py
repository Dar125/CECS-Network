"""
Report Generator for creating unified code review reports
"""

from typing import Dict, List, Any
from datetime import datetime
import json


class ReportGenerator:
    """Generates formatted reports from multi-agent analysis results"""
    
    def __init__(self):
        """Initialize the report generator"""
        self.report_sections = [
            "executive_summary",
            "critical_issues", 
            "security_findings",
            "performance_analysis",
            "code_quality_review",
            "recommendations",
            "metrics"
        ]
    
    def generate_pr_report(self, 
                          orchestrator_results: Dict[str, Any],
                          consensus_results: Dict[str, Any],
                          pr_metadata: Dict[str, Any] = None) -> str:
        """Generate a comprehensive PR review report
        
        Args:
            orchestrator_results: Results from the orchestrator
            consensus_results: Results from consensus mechanism
            pr_metadata: Additional PR information
            
        Returns:
            Formatted report as markdown
        """
        report_lines = []
        
        # Header
        report_lines.extend(self._generate_header(pr_metadata))
        
        # Executive Summary
        report_lines.extend(self._generate_executive_summary(orchestrator_results, consensus_results))
        
        # Critical Issues
        report_lines.extend(self._generate_critical_issues(consensus_results))
        
        # Detailed Findings by Category
        report_lines.extend(self._generate_security_section(orchestrator_results))
        report_lines.extend(self._generate_performance_section(orchestrator_results))
        report_lines.extend(self._generate_code_quality_section(orchestrator_results))
        
        # Recommendations
        report_lines.extend(self._generate_recommendations(consensus_results))
        
        # Metrics
        report_lines.extend(self._generate_metrics(orchestrator_results))
        
        # Footer
        report_lines.extend(self._generate_footer())
        
        return "\n".join(report_lines)
    
    def _generate_header(self, pr_metadata: Dict[str, Any] = None) -> List[str]:
        """Generate report header"""
        lines = [
            "# Multi-Agent Code Review Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            ""
        ]
        
        if pr_metadata:
            lines.extend([
                "## Pull Request Details",
                f"- **Title:** {pr_metadata.get('title', 'N/A')}",
                f"- **Author:** {pr_metadata.get('author', 'N/A')}",
                f"- **Files Changed:** {pr_metadata.get('files_changed', 'N/A')}",
                f"- **Lines Added:** +{pr_metadata.get('additions', 0)}",
                f"- **Lines Removed:** -{pr_metadata.get('deletions', 0)}",
                ""
            ])
        
        lines.append("---\n")
        return lines
    
    def _generate_executive_summary(self, 
                                   orchestrator_results: Dict[str, Any],
                                   consensus_results: Dict[str, Any]) -> List[str]:
        """Generate executive summary section"""
        lines = ["## Executive Summary\n"]
        
        # Extract key metrics
        recommendations = consensus_results.get('recommendations', [])
        critical_count = sum(1 for r in recommendations if r.get('consensus_severity') == 'critical')
        high_count = sum(1 for r in recommendations if r.get('consensus_severity') == 'high')
        
        # Overall assessment
        if critical_count > 0:
            assessment = "**CRITICAL ISSUES FOUND** - Immediate attention required"
        elif high_count > 0:
            assessment = "**High priority issues detected** - Should be addressed before merge"
        else:
            assessment = "**No critical issues found** - Code is generally acceptable"
        
        lines.extend([
            assessment,
            "",
            "### Key Findings:",
            f"- **Critical Issues:** {critical_count}",
            f"- **High Priority Issues:** {high_count}",
            f"- **Total Recommendations:** {len(recommendations)}",
            f"- **Agent Agreement Level:** {consensus_results.get('agreement_level', 0)*100:.1f}%",
            ""
        ])
        
        # Add conflict summary if any
        conflicts = consensus_results.get('conflicts', [])
        if conflicts:
            lines.extend([
                "### Conflicts Detected:",
                f"- **Total Conflicts:** {len(conflicts)}",
                "- Agents provided differing assessments on some issues",
                ""
            ])
        
        lines.append("---\n")
        return lines
    
    def _generate_critical_issues(self, consensus_results: Dict[str, Any]) -> List[str]:
        """Generate critical issues section"""
        recommendations = consensus_results.get('recommendations', [])
        critical_issues = [r for r in recommendations if r.get('consensus_severity') == 'critical']
        
        if not critical_issues:
            return []
        
        lines = ["## Critical Issues\n"]
        lines.append("These issues must be addressed immediately:\n")
        
        for i, issue in enumerate(critical_issues[:5], 1):  # Top 5 critical
            # Clean up the description to ensure it's properly formatted
            description = issue.get('description', 'Issue')
            # Remove any leading/trailing special characters or prefixes
            if description.startswith('- **DESCRIPTION**:'):
                description = description.replace('- **DESCRIPTION**:', '').strip()
            elif description.startswith('#### '):
                description = description.replace('####', '').strip()
            
            lines.extend([
                f"### {i}. {description}",
                f"- **Severity:** {issue.get('consensus_severity', 'N/A').upper()}",
                f"- **Consensus Score:** {issue.get('consensus_score', 0):.1f}",
                f"- **Identified by:** {', '.join(issue.get('contributing_agents', []))}",
                ""
            ])
            
            if issue.get('location'):
                lines.append(f"- **Location:** {issue.get('location')}")
            elif issue.get('line_numbers'):
                lines.append(f"- **Location:** Lines {', '.join(map(str, issue['line_numbers']))}")
            
            solution = issue.get('solution', 'See detailed recommendations')
            if solution and solution != 'See detailed recommendations':
                lines.extend([
                    f"- **Solution:** {solution}",
                    ""
                ])
            else:
                lines.append("")
        
        lines.append("---\n")
        return lines
    
    def _generate_security_section(self, orchestrator_results: Dict[str, Any]) -> List[str]:
        """Generate security findings section"""
        lines = ["## Security Analysis\n"]
        
        security_findings = self._extract_agent_findings(orchestrator_results, 'security')
        
        if not security_findings:
            lines.append("No security vulnerabilities detected.\n")
        else:
            lines.append("### Vulnerabilities Found:\n")
            
            # Group by severity
            by_severity = self._group_by_severity(security_findings)
            
            for severity in ['critical', 'high', 'medium', 'low']:
                if severity in by_severity:
                    lines.append(f"#### {severity.upper()} ({len(by_severity[severity])})")
                    for finding in by_severity[severity][:3]:  # Top 3 per severity
                        lines.append(f"- {finding.get('description', 'Security issue')}")
                    lines.append("")
        
        lines.append("---\n")
        return lines
    
    def _generate_performance_section(self, orchestrator_results: Dict[str, Any]) -> List[str]:
        """Generate performance analysis section"""
        lines = ["## Performance Analysis\n"]
        
        performance_findings = self._extract_agent_findings(orchestrator_results, 'performance')
        
        if not performance_findings:
            lines.append("No significant performance issues detected.\n")
        else:
            lines.append("### Performance Issues:\n")
            
            # Categorize by type
            complexity_issues = [f for f in performance_findings if 'complexity' in str(f).lower()]
            database_issues = [f for f in performance_findings if 'database' in str(f).lower() or 'query' in str(f).lower()]
            other_issues = [f for f in performance_findings if f not in complexity_issues + database_issues]
            
            if complexity_issues:
                lines.append("#### Algorithm Complexity")
                for issue in complexity_issues[:3]:
                    lines.append(f"- {issue.get('description', 'Complexity issue')}")
                lines.append("")
            
            if database_issues:
                lines.append("#### Database Performance")
                for issue in database_issues[:3]:
                    lines.append(f"- {issue.get('description', 'Database issue')}")
                lines.append("")
            
            if other_issues:
                lines.append("#### Other Performance Issues")
                for issue in other_issues[:3]:
                    lines.append(f"- {issue.get('description', 'Performance issue')}")
                lines.append("")
        
        lines.append("---\n")
        return lines
    
    def _generate_code_quality_section(self, orchestrator_results: Dict[str, Any]) -> List[str]:
        """Generate code quality section"""
        lines = ["## Code Quality Review\n"]
        
        quality_findings = self._extract_agent_findings(orchestrator_results, 'quality')
        
        if not quality_findings:
            lines.append("Code meets quality standards.\n")
        else:
            lines.append("### Areas for Improvement:\n")
            
            # Categorize by type
            categories = {
                "documentation": [],
                "naming": [],
                "structure": [],
                "best_practices": []
            }
            
            for finding in quality_findings:
                desc_lower = str(finding.get('description', '')).lower()
                if 'document' in desc_lower or 'comment' in desc_lower:
                    categories["documentation"].append(finding)
                elif 'naming' in desc_lower or 'variable' in desc_lower:
                    categories["naming"].append(finding)
                elif 'structure' in desc_lower or 'architecture' in desc_lower:
                    categories["structure"].append(finding)
                else:
                    categories["best_practices"].append(finding)
            
            for category, issues in categories.items():
                if issues:
                    lines.append(f"#### {category.replace('_', ' ').title()}")
                    for issue in issues[:3]:
                        lines.append(f"- {issue.get('description', 'Quality issue')}")
                    lines.append("")
        
        lines.append("---\n")
        return lines
    
    def _generate_recommendations(self, consensus_results: Dict[str, Any]) -> List[str]:
        """Generate prioritized recommendations section"""
        lines = ["## Prioritized Recommendations\n"]
        
        recommendations = consensus_results.get('recommendations', [])
        
        if not recommendations:
            lines.append("No specific recommendations.\n")
        else:
            lines.append("Based on weighted consensus from all agents:\n")
            
            # Group by priority
            priority_groups = {
                "immediate": [r for r in recommendations if r.get('consensus_severity') in ['critical']],
                "high": [r for r in recommendations if r.get('consensus_severity') in ['high']],
                "medium": [r for r in recommendations if r.get('consensus_severity') in ['medium']],
                "low": [r for r in recommendations if r.get('consensus_severity') in ['low']]
            }
            
            for priority, recs in priority_groups.items():
                if recs:
                    lines.append(f"### {priority.title()} Priority")
                    for i, rec in enumerate(recs[:5], 1):  # Top 5 per priority
                        # Clean up the description
                        description = rec.get('description', 'Recommendation')
                        if description.startswith('- **DESCRIPTION**:'):
                            description = description.replace('- **DESCRIPTION**:', '').strip()
                        elif description.startswith('#### '):
                            description = description.replace('####', '').strip()
                            
                        lines.extend([
                            f"{i}. **{description}**",
                            f"   - Score: {rec.get('consensus_score', 0):.1f}",
                            f"   - Agents: {len(rec.get('contributing_agents', []))} in agreement",
                            f"   - Action: {rec.get('solution', 'Review needed')}",
                            ""
                        ])
        
        lines.append("---\n")
        return lines
    
    def _generate_metrics(self, orchestrator_results: Dict[str, Any]) -> List[str]:
        """Generate metrics section"""
        lines = ["## Analysis Metrics\n"]
        
        # Count issues from recommendations
        if 'file_reviews' in orchestrator_results:
            security_count = 0
            performance_count = 0
            quality_count = 0
            
            for review in orchestrator_results.get('file_reviews', []):
                if review.get('status') == 'success':
                    consensus = review.get('consensus_results', {})
                    recommendations = consensus.get('recommendations', [])
                    
                    for rec in recommendations:
                        agents = rec.get('contributing_agents', [])
                        if 'security_checker' in agents:
                            security_count += 1
                        if 'performance_analyzer' in agents:
                            performance_count += 1
                        if 'code_reviewer' in agents:
                            quality_count += 1
            
            lines.extend([
                "### Issue Distribution",
                f"- **Security Issues:** {security_count}",
                f"- **Performance Issues:** {performance_count}",
                f"- **Code Quality Issues:** {quality_count}",
                ""
            ])
        elif 'overall_summary' in orchestrator_results:
            summary = orchestrator_results['overall_summary']
            total_issues = summary.get('total_issues', {})
            
            lines.extend([
                "### Issue Distribution",
                f"- **Security Issues:** {total_issues.get('security', 0)}",
                f"- **Performance Issues:** {total_issues.get('performance', 0)}",
                f"- **Code Quality Issues:** {total_issues.get('code_quality', 0)}",
                ""
            ])
        
        if 'files_reviewed' in orchestrator_results:
            lines.extend([
                "### Review Statistics",
                f"- **Files Reviewed:** {orchestrator_results.get('files_reviewed', 0)}",
                f"- **Total Review Time:** {orchestrator_results.get('total_duration_seconds', 0):.2f}s",
                f"- **Average Time per File:** {orchestrator_results.get('average_duration_per_file', 0):.2f}s",
                ""
            ])
        
        lines.append("---\n")
        return lines
    
    def _generate_footer(self) -> List[str]:
        """Generate report footer"""
        return [
            "## About This Report\n",
            "This report was generated by a multi-agent code review system featuring:",
            "- **Code Reviewer Agent**: Analyzes code quality and best practices",
            "- **Security Checker Agent**: Identifies security vulnerabilities", 
            "- **Performance Analyzer Agent**: Detects performance bottlenecks",
            "",
            "Recommendations are prioritized using weighted consensus where security issues",
            "receive highest priority (1.5x), followed by performance (1.2x) and code quality (1.0x).",
            "",
            f"*Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S UTC')}*"
        ]
    
    def _extract_agent_findings(self, orchestrator_results: Dict[str, Any], category: str) -> List[Dict[str, Any]]:
        """Extract findings for a specific category from orchestrator results"""
        findings = []
        
        # Map category to agent names
        category_map = {
            'security': 'security_checker',
            'performance': 'performance_analyzer',
            'quality': 'code_reviewer'
        }
        
        agent_name = category_map.get(category)
        if not agent_name:
            return findings
            
        # Extract from file reviews
        file_reviews = orchestrator_results.get('file_reviews', [])
        for review in file_reviews:
            if review.get('status') == 'success':
                consensus = review.get('consensus_results', {})
                recommendations = consensus.get('recommendations', [])
                
                # Filter recommendations by agent
                for rec in recommendations:
                    contributing_agents = rec.get('contributing_agents', [])
                    if agent_name in contributing_agents:
                        findings.append({
                            'description': rec.get('description', ''),
                            'severity': rec.get('consensus_severity', 'medium'),
                            'solution': rec.get('solution', '')
                        })
        
        return findings
    
    def _group_by_severity(self, findings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group findings by severity level"""
        grouped = {}
        for finding in findings:
            severity = finding.get('severity', 'medium').lower()
            if severity not in grouped:
                grouped[severity] = []
            grouped[severity].append(finding)
        return grouped
    
    def generate_json_report(self, 
                           orchestrator_results: Dict[str, Any],
                           consensus_results: Dict[str, Any]) -> str:
        """Generate report in JSON format for programmatic consumption"""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_issues": len(consensus_results.get('recommendations', [])),
                "critical_issues": sum(1 for r in consensus_results.get('recommendations', []) 
                                     if r.get('consensus_severity') == 'critical'),
                "agreement_level": consensus_results.get('agreement_level', 0)
            },
            "recommendations": consensus_results.get('recommendations', []),
            "conflicts": consensus_results.get('conflicts', []),
            "metrics": orchestrator_results.get('overall_summary', {})
        }
        
        return json.dumps(report_data, indent=2)