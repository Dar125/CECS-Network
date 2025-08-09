"""
Confidence Scoring System for Agent Findings

Provides confidence scoring for individual agent findings based on various factors.
"""

from typing import Dict, List, Any, Tuple
import re

class ConfidenceScorer:
    """Calculate confidence scores for agent findings"""
    
    def __init__(self):
        # Define confidence modifiers based on various factors
        self.evidence_keywords = {
            "definitely": 0.95,
            "certainly": 0.90,
            "clearly": 0.85,
            "obviously": 0.85,
            "likely": 0.70,
            "probably": 0.65,
            "possibly": 0.50,
            "might": 0.45,
            "could": 0.40,
            "uncertain": 0.30,
            "unclear": 0.25
        }
        
        self.severity_confidence = {
            "critical": 0.90,
            "high": 0.80,
            "medium": 0.60,
            "low": 0.40
        }
    
    def calculate_confidence(self, 
                           finding: Dict[str, Any], 
                           agent_type: str,
                           context: Dict[str, Any] = None) -> float:
        """Calculate confidence score for a specific finding
        
        Args:
            finding: The finding dictionary from an agent
            agent_type: Type of agent (code_reviewer, security_checker, etc.)
            context: Additional context
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence_factors = []
        
        # Base confidence by agent type
        agent_base_confidence = {
            "security_checker": 0.85,  # Security findings tend to be more definitive
            "code_reviewer": 0.75,     # Code quality is somewhat subjective
            "performance_analyzer": 0.80  # Performance issues are measurable
        }
        base_confidence = agent_base_confidence.get(agent_type, 0.70)
        confidence_factors.append(base_confidence)
        
        # Check for evidence strength in description
        description = str(finding.get("description", "")).lower()
        suggestion = str(finding.get("suggestion", "")).lower()
        full_text = f"{description} {suggestion}"
        
        # Evidence keywords
        evidence_score = self._calculate_evidence_score(full_text)
        if evidence_score > 0:
            confidence_factors.append(evidence_score)
        
        # Severity-based confidence
        severity = finding.get("severity", "medium").lower()
        if severity in self.severity_confidence:
            confidence_factors.append(self.severity_confidence[severity])
        
        # Specific pattern detection boosts confidence
        if self._has_specific_evidence(finding, agent_type):
            confidence_factors.append(0.90)
        
        # Calculate weighted average
        if confidence_factors:
            confidence = sum(confidence_factors) / len(confidence_factors)
        else:
            confidence = base_confidence
        
        # Apply bounds
        return max(0.1, min(0.95, confidence))
    
    def _calculate_evidence_score(self, text: str) -> float:
        """Calculate evidence score based on keywords"""
        scores = []
        for keyword, score in self.evidence_keywords.items():
            if keyword in text:
                scores.append(score)
        
        return max(scores) if scores else 0.0
    
    def _has_specific_evidence(self, finding: Dict[str, Any], agent_type: str) -> bool:
        """Check for specific evidence patterns that increase confidence"""
        description = str(finding.get("description", "")).lower()
        
        # Security-specific patterns
        if agent_type == "security_checker":
            security_patterns = [
                r"sql injection",
                r"cross-site scripting",
                r"hardcoded (password|secret|key)",
                r"vulnerable to",
                r"allows unauthorized"
            ]
            for pattern in security_patterns:
                if re.search(pattern, description):
                    return True
        
        # Performance-specific patterns
        elif agent_type == "performance_analyzer":
            perf_patterns = [
                r"o\(n\^[2-9]\)",  # Quadratic or worse complexity
                r"exponential",
                r"memory leak",
                r"infinite loop",
                r"blocking operation"
            ]
            for pattern in perf_patterns:
                if re.search(pattern, description):
                    return True
        
        # Code quality specific patterns
        elif agent_type == "code_reviewer":
            quality_patterns = [
                r"violates \w+ principle",
                r"anti-pattern",
                r"code smell",
                r"technical debt",
                r"unmaintainable"
            ]
            for pattern in quality_patterns:
                if re.search(pattern, description):
                    return True
        
        return False
    
    def calculate_aggregate_confidence(self, findings: List[Dict[str, Any]]) -> float:
        """Calculate aggregate confidence for a set of findings"""
        if not findings:
            return 0.0
        
        confidences = [f.get("confidence", 0.5) for f in findings]
        
        # Weighted average giving more weight to higher confidence findings
        weighted_sum = sum(c * c for c in confidences)  # Square to emphasize high confidence
        weight_total = sum(c for c in confidences)
        
        if weight_total > 0:
            return weighted_sum / weight_total
        return 0.5
    
    def adjust_consensus_confidence(self, 
                                  recommendation: Dict[str, Any],
                                  agent_agreements: int,
                                  total_agents: int) -> float:
        """Adjust confidence based on agent consensus
        
        Args:
            recommendation: The consensus recommendation
            agent_agreements: Number of agents that agree
            total_agents: Total number of agents
            
        Returns:
            Adjusted confidence score
        """
        base_confidence = recommendation.get("confidence", 0.5)
        agreement_ratio = agent_agreements / total_agents
        
        # Boost confidence for high agreement
        if agreement_ratio >= 0.8:
            confidence_boost = 0.15
        elif agreement_ratio >= 0.6:
            confidence_boost = 0.10
        else:
            confidence_boost = 0.0
        
        # Penalty for low agreement
        if agreement_ratio < 0.4:
            confidence_penalty = 0.15
        else:
            confidence_penalty = 0.0
        
        adjusted = base_confidence + confidence_boost - confidence_penalty
        return max(0.1, min(0.95, adjusted))
    
    def categorize_confidence(self, confidence: float) -> str:
        """Categorize confidence score into human-readable levels"""
        if confidence >= 0.85:
            return "Very High"
        elif confidence >= 0.70:
            return "High"
        elif confidence >= 0.55:
            return "Medium"
        elif confidence >= 0.40:
            return "Low"
        else:
            return "Very Low"