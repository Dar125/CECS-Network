"""
Consensus Mechanism for resolving conflicts between agent recommendations
"""

from typing import Dict, List, Any, Tuple
from collections import defaultdict
import re
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.confidence_scorer import ConfidenceScorer


class WeightedConsensus:
    """Implements weighted consensus for multi-agent recommendations"""
    
    def __init__(self):
        """Initialize consensus mechanism with agent weights"""
        self.agent_weights = {
            "security_checker": 1.5,     # Highest priority
            "performance_analyzer": 1.2,  # Medium priority  
            "code_reviewer": 1.0         # Base priority
        }
        
        self.severity_scores = {
            "critical": 4.0,
            "high": 3.0,
            "medium": 2.0,
            "low": 1.0
        }
        
        self.confidence_scorer = ConfidenceScorer()
    
    def resolve_conflicts(self, agent_findings: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Resolve conflicts between agent recommendations
        
        Args:
            agent_findings: Dictionary mapping agent names to their findings
            
        Returns:
            Resolved recommendations with consensus scoring
        """
        # Extract all recommendations
        all_recommendations = self._extract_recommendations(agent_findings)
        
        # Group similar recommendations
        grouped_recommendations = self._group_similar_recommendations(all_recommendations)
        
        # Calculate consensus scores
        scored_recommendations = self._calculate_consensus_scores(grouped_recommendations)
        
        # Identify conflicts
        conflicts = self._identify_conflicts(grouped_recommendations)
        
        # Sort by priority
        prioritized = sorted(scored_recommendations, key=lambda x: x['consensus_score'], reverse=True)
        
        return {
            "recommendations": prioritized,
            "conflicts": conflicts,
            "agreement_level": self._calculate_agreement_level(grouped_recommendations)
        }
    
    def _extract_recommendations(self, agent_findings: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Extract all recommendations from agent findings"""
        recommendations = []
        
        for agent_name, findings in agent_findings.items():
            for finding in findings:
                if isinstance(finding, dict):
                    rec = {
                        "agent": agent_name,
                        "type": finding.get("type", "general"),
                        "severity": finding.get("severity", "medium"),
                        "description": finding.get("description", ""),
                        "solution": finding.get("solution", ""),
                        "location": finding.get("location", ""),
                        "line_numbers": finding.get("line_numbers", []),
                        "category": finding.get("category", "other")
                    }
                    recommendations.append(rec)
        
        return recommendations
    
    def _group_similar_recommendations(self, recommendations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group recommendations that address the same issue"""
        groups = defaultdict(list)
        
        for rec in recommendations:
            # Create a key based on issue type and affected lines
            if rec['line_numbers']:
                key = f"{rec['type']}_{min(rec['line_numbers'])}"
            else:
                # Use description similarity for grouping when no line numbers
                key = self._get_issue_key(rec['description'])
            
            groups[key].append(rec)
        
        return dict(groups)
    
    def _get_issue_key(self, description: str) -> str:
        """Generate a key for grouping similar issues"""
        # Extract key patterns from description
        patterns = [
            (r"sql.{0,20}injection", "sql_injection"),
            (r"command.{0,20}injection", "command_injection"),
            (r"eval\(|exec\(", "eval_exec"),
            (r"hardcoded.{0,20}(password|secret|key|api)", "hardcoded_secret"),
            (r"plain.{0,20}text.{0,20}password", "plaintext_password"),
            (r"md5|sha1", "weak_hashing"),
            (r"pickle\.load", "unsafe_deserialization"),
            (r"timing.{0,20}attack", "timing_attack"),
            (r"n\+1|n\^2|n\^3|o\(n.{0,5}\)|complexity", "complexity"),
            (r"error.{0,20}handling", "error_handling"),
            (r"input.{0,20}validation", "input_validation"),
            (r"information.{0,20}disclosure", "info_disclosure"),
            (r"logging.{0,20}sensitive", "logging_sensitive")
        ]
        
        description_lower = description.lower()
        for pattern, key in patterns:
            if re.search(pattern, description_lower, re.IGNORECASE):
                return key
        
        # For other issues, use a more specific key
        # Extract the main subject (often after "Issue:" or similar)
        if ':' in description:
            main_part = description.split(':', 1)[1].strip()
        else:
            main_part = description
            
        # Use first significant words
        words = [w for w in main_part.split()[:5] if len(w) > 3]
        if words:
            return "_".join(words[:3]).lower()
        
        # Fallback
        return "other_issue"
    
    def _calculate_consensus_scores(self, grouped_recommendations: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Calculate consensus scores for grouped recommendations"""
        consensus_recommendations = []
        
        for issue_key, recs in grouped_recommendations.items():
            # Calculate weighted score
            total_score = 0
            agent_contributions = {}
            severities = []
            confidence_scores = []
            
            for rec in recs:
                agent = rec['agent']
                severity = rec['severity'].lower()
                
                # Calculate confidence for this recommendation
                confidence = self.confidence_scorer.calculate_confidence(
                    finding=rec,
                    agent_type=agent,
                    context={"severity": severity}
                )
                rec['confidence'] = confidence
                confidence_scores.append(confidence)
                
                # Calculate individual score with confidence weighting
                agent_weight = self.agent_weights.get(agent, 1.0)
                severity_score = self.severity_scores.get(severity, 1.0)
                contribution = agent_weight * severity_score * confidence
                
                total_score += contribution
                agent_contributions[agent] = contribution
                severities.append(severity)
            
            # Determine consensus severity (highest among all)
            severity_priority = ['critical', 'high', 'medium', 'low']
            consensus_severity = next((s for s in severity_priority if s in severities), 'medium')
            
            # Calculate aggregate confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
            
            # Adjust confidence based on agent agreement
            adjusted_confidence = self.confidence_scorer.adjust_consensus_confidence(
                {"confidence": avg_confidence},
                agent_agreements=len(recs),
                total_agents=3  # We have 3 agents total
            )
            
            # Create consensus recommendation
            consensus_rec = {
                "issue_key": issue_key,
                "consensus_score": total_score,
                "consensus_severity": consensus_severity,
                "agent_agreement": len(recs),
                "contributing_agents": list(agent_contributions.keys()),
                "agent_contributions": agent_contributions,
                "confidence": adjusted_confidence,
                "confidence_level": self.confidence_scorer.categorize_confidence(adjusted_confidence),
                "individual_confidences": {rec['agent']: rec['confidence'] for rec in recs},
                "description": self._merge_descriptions(recs),
                "solution": self._merge_solutions(recs),
                "location": self._merge_locations(recs),
                "line_numbers": self._merge_line_numbers(recs),
                "original_recommendations": recs
            }
            
            consensus_recommendations.append(consensus_rec)
        
        return consensus_recommendations
    
    def _merge_descriptions(self, recommendations: List[Dict[str, Any]]) -> str:
        """Merge descriptions from multiple agents"""
        descriptions = [rec['description'] for rec in recommendations if rec['description']]
        
        if not descriptions:
            return "Issue identified by multiple agents"
        
        # Use the most detailed description
        return max(descriptions, key=len)
    
    def _merge_solutions(self, recommendations: List[Dict[str, Any]]) -> str:
        """Merge solutions from multiple agents"""
        solutions = [rec['solution'] for rec in recommendations if rec['solution']]
        
        if not solutions:
            return "Please review agent recommendations for specific solutions"
        
        # If all solutions are similar, use the most detailed one
        if len(set(solutions)) == 1:
            return solutions[0]
        
        # Otherwise, combine unique solutions
        unique_solutions = []
        for sol in solutions:
            if sol not in unique_solutions:
                unique_solutions.append(sol)
        
        return " Additionally, ".join(unique_solutions)
    
    def _merge_locations(self, recommendations: List[Dict[str, Any]]) -> str:
        """Merge location information from multiple recommendations"""
        locations = []
        for rec in recommendations:
            loc = rec.get('location', '')
            if loc and loc not in locations:
                locations.append(loc)
        
        return ", ".join(locations) if locations else ""
    
    def _merge_line_numbers(self, recommendations: List[Dict[str, Any]]) -> List[int]:
        """Merge line numbers from multiple recommendations"""
        all_lines = []
        for rec in recommendations:
            all_lines.extend(rec.get('line_numbers', []))
        
        return sorted(list(set(all_lines)))
    
    def _identify_conflicts(self, grouped_recommendations: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Identify conflicting recommendations"""
        conflicts = []
        
        for issue_key, recs in grouped_recommendations.items():
            if len(recs) > 1:
                # Check for conflicting severities
                severities = [rec['severity'] for rec in recs]
                if len(set(severities)) > 1:
                    conflicts.append({
                        "issue": issue_key,
                        "conflict_type": "severity_mismatch",
                        "agents": [rec['agent'] for rec in recs],
                        "severities": severities
                    })
                
                # Check for conflicting solutions
                solutions = [rec['solution'] for rec in recs if rec['solution']]
                if len(set(solutions)) > 1 and len(solutions) > 1:
                    conflicts.append({
                        "issue": issue_key,
                        "conflict_type": "solution_mismatch",
                        "agents": [rec['agent'] for rec in recs],
                        "solutions": solutions
                    })
        
        return conflicts
    
    def _calculate_agreement_level(self, grouped_recommendations: Dict[str, List[Dict[str, Any]]]) -> float:
        """Calculate overall agreement level between agents"""
        if not grouped_recommendations:
            return 1.0
        
        total_issues = len(grouped_recommendations)
        agreed_issues = sum(1 for recs in grouped_recommendations.values() if len(recs) >= 2)
        
        return agreed_issues / total_issues if total_issues > 0 else 0.0
    
    def generate_conflict_report(self, conflicts: List[Dict[str, Any]]) -> str:
        """Generate a human-readable conflict report"""
        if not conflicts:
            return "No conflicts found between agent recommendations."
        
        report_lines = ["Conflicts Found Between Agents:\n"]
        
        for i, conflict in enumerate(conflicts, 1):
            report_lines.append(f"{i}. Issue: {conflict['issue']}")
            report_lines.append(f"   Type: {conflict['conflict_type'].replace('_', ' ').title()}")
            report_lines.append(f"   Agents: {', '.join(conflict['agents'])}")
            
            if conflict['conflict_type'] == 'severity_mismatch':
                report_lines.append(f"   Severities: {', '.join(conflict['severities'])}")
            elif conflict['conflict_type'] == 'solution_mismatch':
                report_lines.append("   Different solutions proposed")
            
            report_lines.append("")
        
        return "\n".join(report_lines)