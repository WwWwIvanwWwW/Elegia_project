from typing import Dict, Any, List, Optional
from .request import call_llm
import os
import json
import logging
from enum import Enum
from dataclasses import dataclass
import hashlib
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class TaggingResult:
    category: str
    tags: List[str]
    confidence_scores: Dict[str, float]
    taxonomy_updates: List[str]  # Tags that should be added to taxonomy

class TaxonomyStatus(Enum):
    EXISTING = "existing"
    NEW_SUGGESTED = "new_suggested"
    MERGE_CANDIDATE = "merge_candidate"

class SemanticTaggingAgent:
    def __init__(self):
        self.taxonomy = self._load_taxonomy()
        self.tag_usage_frequency = defaultdict(int)  # Track tag popularity
        self.llm_call_cache = {}
        self.metrics = {
            "total_taggings": 0,
            "taxonomy_expansions": 0,
            "disambiguation_attempts": 0,
            "embedding_validations": 0
        }

        # Hierarchical tag relationships
        self.parent_tags = {
            "llm": "искусственный_интеллект",
            "нейросеть": "искусственный_интеллект",
            "искусственный_интеллект": "технологии",
            "стартап": "бизнес",
            "венчур": "бизнес",
            "инвестиции": "бизнес",
            "криптовалюта": "финансы",
            "блокчейн": "технологии",
            "data_science": "наука",
            "machine_learning": "искусственный_интеллект",
            "deep_learning": "искусственный_интеллект"
        }

    def _load_taxonomy(self) -> Dict[str, List[str]]:
        """Load the current taxonomy from file"""
        taxonomy_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'tags_taxonomy.json')
        try:
            with open(taxonomy_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default taxonomy if file doesn't exist
            return {
                "technology": ["искусственный_интеллект", "машинное_обучение", "биг_дата", "blockchain", "cybersecurity"],
                "business": ["стартапы", "инвестиции", "венчур", "маркетинг"],
                "science": ["исследования", "медицина", "астрономия", "биология"],
                "culture": ["искусство", "музыка", "кино", "литература"],
                "politics": ["политика", "выборы", "государство", "международные_отношения"]
            }

    def _save_taxonomy(self):
        """Save updated taxonomy to file"""
        taxonomy_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'tags_taxonomy.json')
        with open(taxonomy_path, 'w', encoding='utf-8') as f:
            json.dump(self.taxonomy, f, ensure_ascii=False, indent=2)

    def _get_all_allowed_tags(self) -> List[str]:
        """Get all allowed tags flatten from categories"""
        allowed_tags = []
        for category, tags in self.taxonomy.items():
            allowed_tags.extend(tags)
        return allowed_tags

    def _contextual_disambiguation(self, word: str, content_context: str) -> str:
        """Resolve ambiguity based on context (e.g., 'яблоко' -> fruit or company)"""
        self.metrics["disambiguation_attempts"] += 1

        word_lower = word.lower()
        context_lower = content_context.lower()

        # Context keywords for different meanings
        fruit_contexts = ["fruit", "food", "eat", "healthy", "vitamin", "diet", "orchard", "tree", "sweet"]
        company_contexts = ["company", "tech", "stock", "iphone", "mac", "store", "inc", "revenue", "ceo"]

        fruit_matches = sum(1 for term in fruit_contexts if term in context_lower)
        company_matches = sum(1 for term in company_contexts if term in context_lower)

        if company_matches > fruit_matches:
            return "apple_inc"
        elif fruit_matches > company_matches:
            return "фрукты"
        else:
            # If unclear, return the original word normalized
            return word_lower.replace(" ", "_")

    def _add_parent_tags(self, tags: List[str]) -> List[str]:
        """Add parent tags based on hierarchical relationships"""
        all_tags = set(tags)

        for tag in tags:
            parent = self.parent_tags.get(tag)
            if parent:
                all_tags.add(parent)

        return list(all_tags)

    def _validate_via_embeddings(self, content: str, tags: List[str]) -> List[str]:
        """Basic validation using string similarity (in real app, use semantic embeddings)"""
        self.metrics["embedding_validations"] += 1

        # Simplified validation - check if tags appear in content or have semantic similarity
        validated_tags = []
        content_lower = content.lower()

        for tag in tags:
            # Simple semantic check - if tag is related to content
            tag_normalized = tag.replace("_", " ").lower()

            # If tag appears in content or has obvious relationship, keep it
            if tag_normalized in content_lower or self._has_semantic_connection(content_lower, tag_normalized):
                validated_tags.append(tag)
            else:
                logger.info(f"Tag '{tag}' failed embedding validation and was removed")

        return validated_tags

    def _has_semantic_connection(self, content: str, tag: str) -> bool:
        """Check if tag has semantic connection to content"""
        # Basic word overlap or related terms
        content_words = set(content.split())
        tag_words = set(tag.split())

        # If any word in tag appears in content, it's connected
        if content_words.intersection(tag_words):
            return True

        # Additional semantic rules could be added here
        semantic_pairs = {
            "искусственный_интеллект": ["ai", "мозг", "нейросеть", "интеллект"],
            "бизнес": ["компания", "деньги", "прибыль", "рынок"],
            "технологии": ["компьютер", "интернет", "программа", "инновации"],
        }

        for main_term, related_terms in semantic_pairs.items():
            if main_term == tag and any(term in content for term in related_terms):
                return True

        return False

    def _normalize_and_limit_tags(self, tags: List[str], max_tags: int = 5) -> List[str]:
        """Normalize and limit tags"""
        # Normalize: lowercase and replace spaces with underscores
        normalized = [tag.strip().lower().replace(" ", "_") for tag in tags if tag.strip()]

        # Filter out empty tags
        normalized = [tag for tag in normalized if tag]

        # Limit to max_tags
        return normalized[:max_tags]

    def _check_for_taxonomy_updates(self, suggested_tags: List[str], threshold: int = 5) -> List[str]:
        """Check if we should suggest adding new tags to taxonomy based on usage frequency"""
        new_suggestions = []

        for tag in suggested_tags:
            # Count how many times this tag has appeared
            freq = self.tag_usage_frequency[tag]

            # If it's popular enough and not in taxonomy, suggest adding
            if freq >= threshold and tag not in self._get_all_allowed_tags():
                new_suggestions.append(tag)
                logger.info(f"Suggesting new taxonomy tag: {tag} (used {freq} times)")

        return new_suggestions

    def _update_taxonomy_with_new_tags(self, new_tags: List[str]):
        """Add new tags to taxonomy (for human moderation)"""
        if not new_tags:
            return

        # Add to a special "proposed" section for human review
        if "proposed" not in self.taxonomy:
            self.taxonomy["proposed"] = []

        for tag in new_tags:
            if tag not in self.taxonomy["proposed"]:
                self.taxonomy["proposed"].append(tag)
                self.metrics["taxonomy_expansions"] += 1

        self._save_taxonomy()

    def _create_taxonomy_aware_prompt(self, summary: str) -> str:
        """Create prompt that considers taxonomy and context"""
        allowed_tags = self._get_all_allowed_tags()
        allowed_tags_str = ", ".join(allowed_tags)

        # Enhance the original prompt to include taxonomy awareness
        prompt = f"""Classify this content into categories and extract relevant tags. Consider the following taxonomy:
Allowed tags: {allowed_tags_str}

Content: {summary}

The word 'яблоко' could mean apple (fruit) or Apple Inc. Choose based on context.
For technology articles, prefer specific terms like 'искусственный_интелLECT' over generic 'технологии'.
Return in JSON format: {{"category": "...", "tags": [...]}}
"""

        return prompt

    async def generate_tags_with_enhancements(self, summary: str, user_tags: List[str] = None) -> Dict[str, Any]:
        """Main method for enhanced tagging with all features"""
        if not summary.strip():
            return {"category": "unknown", "tags": [], "confidence_scores": {}, "taxonomy_updates": []}

        self.metrics["total_taggings"] += 1

        # Create cache key
        cache_key = hashlib.md5(f"{summary}{str(user_tags)}".encode()).hexdigest()
        if cache_key in self.llm_call_cache:
            logger.info("Cache hit for tagging")
            return self.llm_call_cache[cache_key]

        # Prepare prompt with taxonomy awareness
        prompt = self._create_taxonomy_aware_prompt(summary)
        safe_prompt = prompt.replace("{", "{{").replace("}", "}}")

        # Call LLM
        response = await call_llm(safe_prompt)

        if response == "error":
            # Fallback to basic keyword matching
            logger.warning("LLM call failed, using keyword matching fallback")
            basic_tags = self._extract_basic_tags(summary)
            result = {
                "category": "general",
                "tags": self._normalize_and_limit_tags(basic_tags),
                "confidence_scores": {tag: 0.6 for tag in basic_tags},
                "taxonomy_updates": []
            }
        else:
            # Parse LLM response
            try:
                # Extract JSON from response
                import re
                import json

                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    parsed_data = json.loads(json_str)

                    category = parsed_data.get("category", "unknown")
                    suggested_tags = parsed_data.get("tags", [])

                    # Add user-suggested tags if provided
                    if user_tags:
                        suggested_tags.extend(user_tags)

                    # Normalize tags
                    normalized_tags = self._normalize_and_limit_tags(suggested_tags)

                    # Apply contextual disambiguation
                    disambiguated_tags = [
                        self._contextual_disambiguation(tag, summary) for tag in normalized_tags
                    ]

                    # Add parent tags based on hierarchy
                    tags_with_parents = self._add_parent_tags(disambiguated_tags)

                    # Validate tags using semantic similarity
                    validated_tags = self._validate_via_embeddings(summary, tags_with_parents)

                    # Update usage frequency
                    for tag in validated_tags:
                        self.tag_usage_frequency[tag] += 1

                    # Check for taxonomy updates based on popular tags
                    new_taxonomy_suggestions = self._check_for_taxonomy_updates(normalized_tags)

                    # Create confidence scores (basic implementation)
                    confidence_scores = {tag: min(0.9, 0.5 + (self.tag_usage_frequency[tag] * 0.01))
                                       for tag in validated_tags}

                    result = {
                        "category": category,
                        "tags": validated_tags,
                        "confidence_scores": confidence_scores,
                        "taxonomy_updates": new_taxonomy_suggestions
                    }

                    # Update taxonomy if needed
                    self._update_taxonomy_with_new_tags(new_taxonomy_suggestions)

                else:
                    logger.error(f"No JSON found in LLM response: {response}")
                    result = {"category": "unknown", "tags": [], "confidence_scores": {}, "taxonomy_updates": []}
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error parsing tagging response: {e}")
                result = {"category": "unknown", "tags": [], "confidence_scores": {}, "taxonomy_updates": []}

        # Cache the result
        self.llm_call_cache[cache_key] = result

        return result

    def _extract_basic_tags(self, content: str) -> List[str]:
        """Fallback method for extracting tags using keyword matching"""
        content_lower = content.lower()

        # Simple keyword extraction
        potential_tags = []

        # Look for common tech terms
        tech_terms = ["искусственный_интеллект", "машинное_обучение", "data", "ai", "блокчейн", "криптовалюта"]
        for term in tech_terms:
            if term in content_lower:
                potential_tags.append(term)

        # Look for business terms
        biz_terms = ["бизнес", "стартап", "инвестиции", "рынок", "компания"]
        for term in biz_terms:
            if term in content_lower:
                potential_tags.append(term)

        return potential_tags[:5]  # Limit to 5 tags

    def get_taxonomy_status(self) -> Dict[str, Any]:
        """Return current taxonomy status and statistics"""
        all_tags = self._get_all_allowed_tags()
        return {
            "categories": list(self.taxonomy.keys()),
            "total_tags": len(all_tags),
            "usage_statistics": dict(self.tag_usage_frequency),
            "metrics": self.metrics.copy()
        }


# Global instance to maintain state
tags_agent_instance = SemanticTaggingAgent()

async def run(summary: str, user_tags: List[str] = None) -> Dict[str, Any]:
    """Main run function maintaining backward compatibility"""
    result = await tags_agent_instance.generate_tags_with_enhancements(summary, user_tags)

    # Log metrics periodically
    if tags_agent_instance.metrics["total_taggings"] % 10 == 0:
        logger.info(f"Tags agent taxonomy status: {tags_agent_instance.get_taxonomy_status()}")

    # Return in backward-compatible format
    return {
        "category": result["category"],
        "tags": result["tags"]
    }