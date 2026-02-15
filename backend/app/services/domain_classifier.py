"""Domain classifier using keyword matching."""
import json
from pathlib import Path
from typing import Optional, Dict, List

from ..config import DOMAINS_CONFIG_PATH


class DomainClassifier:
    """Classifies questions into AZ-104 domains based on keywords."""
    
    def __init__(self):
        self.domains: List[Dict] = []
        self.default_domain: str = "identity-governance"
        self._load_config()
    
    def _load_config(self):
        """Load domain configuration from JSON file."""
        if DOMAINS_CONFIG_PATH.exists():
            with open(DOMAINS_CONFIG_PATH, 'r') as f:
                config = json.load(f)
                self.domains = config.get("domains", [])
                self.default_domain = config.get("default_domain", "identity-governance")
    
    def classify(self, text: str) -> str:
        """
        Classify question text into a domain.
        Returns the domain_id with the highest keyword match count.
        """
        if not text:
            return self.default_domain
        
        text_lower = text.lower()
        scores = {}
        
        for domain in self.domains:
            domain_id = domain["id"]
            keywords = domain.get("keywords", [])
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[domain_id] = score
        
        # Return domain with highest score, or default if no matches
        if scores:
            best = max(scores, key=scores.get)
            if scores[best] > 0:
                return best
        
        return self.default_domain
    
    def get_domain_name(self, domain_id: str) -> str:
        """Get the human-readable name for a domain."""
        for domain in self.domains:
            if domain["id"] == domain_id:
                return domain["name"]
        return domain_id
    
    def get_all_domains(self) -> List[Dict]:
        """Get all domain definitions."""
        return self.domains


# Singleton instance
_classifier: Optional[DomainClassifier] = None


def get_classifier() -> DomainClassifier:
    """Get or create the domain classifier singleton."""
    global _classifier
    if _classifier is None:
        _classifier = DomainClassifier()
    return _classifier
