from typing import List, Dict, Any
from .request import call_llm
import os
import logging
import json
import asyncio
from datetime import datetime, timedelta
from database.db import get_user_profile, update_user_interests
import math
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class TimeContext(Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"

@dataclass
class RecommendationContext:
    user_id: int
    category: str
    tags: List[str]
    timestamp: datetime
    content_age: int  # in hours
    interaction_history: List[Dict[str, Any]]

class PersonalizationAgent:
    def __init__(self):
        self.user_interests = {}  # In-memory cache of user interests
        self.collaborative_cache = {}  # Cache for collaborative filtering
        self.exploration_tracker = {}  # Track exploration vs exploitation
        self.metrics = {
            "total_recommendations": 0,
            "accepted_recommendations": 0,
            "collaborative_matches": 0,
            "exploration_attempts": 0,
            "time_based_recommendations": 0
        }
        # Decay factor for old interests (lower = faster decay)
        self.decay_factor = 0.95

        # Time-based content preferences
        self.time_preferences = {
            TimeContext.MORNING: ["технологии", "новости", "бизнес"],
            TimeContext.AFTERNOON: ["наука", "исследования", "аналитика"],
            TimeContext.EVENING: ["культура", "искусство", "кино", "музыка"],
            TimeContext.NIGHT: ["наука", "философия", "психология"]
        }

    def _get_time_context(self) -> TimeContext:
        """Determine time context based on current time"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return TimeContext.MORNING
        elif 12 <= hour < 17:
            return TimeContext.AFTERNOON
        elif 17 <= hour < 22:
            return TimeContext.EVENING
        else:
            return TimeContext.NIGHT

    def _load_user_interests(self, user_id: int) -> Dict[str, float]:
        """Load and cache user interests with decay applied"""
        if user_id in self.user_interests:
            interests = self.user_interests[user_id]
        else:
            profile = get_user_profile(user_id)
            # Convert preferred tags to interests with initial weights
            interests = {}
            for tag in profile.get("preferred_tags", []):
                interests[tag] = 0.8  # Default weight for existing preferences
            self.user_interests[user_id] = interests

        # Apply time decay to all interests
        current_time = datetime.now()
        for tag in list(interests.keys()):
            # For simplicity, we'll apply decay based on a theoretical last interaction time
            # In a real implementation, we'd track last interaction per tag
            interests[tag] *= self.decay_factor

            # Remove interests that have decayed below threshold
            if interests[tag] < 0.1:
                del interests[tag]

        return interests

    def _has_sufficient_interests(self, user_id: int) -> bool:
        """Check if user has enough interests to apply full personalization"""
        user_interests = self._load_user_interests(user_id)
        return len(user_interests) >= 3

    def _update_user_interests(self, user_id: int, tag: str, interaction_strength: float = 1.0):
        """Update user interests based on interaction"""
        if user_id not in self.user_interests:
            self.user_interests[user_id] = self._load_user_interests(user_id)

        current_interests = self.user_interests[user_id]

        # Update or add the tag with new weight
        current_weight = current_interests.get(tag, 0.0)
        new_weight = min(1.0, current_weight + (interaction_strength * 0.1))
        current_interests[tag] = new_weight

        # Save back to database (this might be async in a real implementation)
        try:
            # Convert interest weights to just the tag names for storage
            # In the real implementation, we'd want to store the weights too
            update_user_interests(user_id, list(current_interests.keys()))
        except:
            # Fallback to just updating internal cache
            pass

    def _calculate_content_score(self, user_interests: Dict[str, float], content_tags: List[str]) -> float:
        """Calculate how well content matches user interests"""
        if not content_tags:
            return 0.0

        max_score = 0.0
        total_score = 0.0

        for tag in content_tags:
            tag_score = user_interests.get(tag, 0.0)
            total_score += tag_score
            max_score = max(max_score, tag_score)

        # Use a combination of total match and best match
        combined_score = (total_score / len(content_tags)) * 0.6 + max_score * 0.4
        return min(1.0, combined_score)

    def _get_collaborative_matches(self, user_id: int, content_tags: List[str], max_matches: int = 10) -> List[int]:
        """Lightweight collaborative filtering - find similar users"""
        self.metrics["collaborative_matches"] += 1

        # This is a simplified version - in a real system, you'd have
        # a more sophisticated approach to find similar users
        similar_users = []

        # For this example, we'll return empty list since we don't have
        # a function to find similar users
        return similar_users

    def _apply_time_context(self, user_interests: Dict[str, float]) -> Dict[str, float]:
        """Apply time-of-day adjustments to user interests"""
        self.metrics["time_based_recommendations"] += 1
        time_context = self._get_time_context()

        # Boost interests that match the current time context
        adjusted_interests = user_interests.copy()

        for time_tag in self.time_preferences[time_context]:
            if time_tag in adjusted_interests:
                # Boost time-appropriate content slightly
                adjusted_interests[time_tag] = min(1.0, adjusted_interests[time_tag] * 1.1)

        return adjusted_interests

    def _should_explore(self, user_id: int) -> bool:
        """Determine if we should show an exploratory recommendation"""
        # 20% of recommendations should be exploratory
        exploration_rate = 0.2

        user_exploration_count = self.exploration_tracker.get(user_id, 0)
        total_recommendations = self.metrics["total_recommendations"]

        # Use a simple modulo approach to ensure we get exploration recommendations
        should_explore = (total_recommendations + user_exploration_count) % 5 == 0

        if should_explore:
            self.metrics["exploration_attempts"] += 1

        return should_explore

    def _find_exploration_content(self, user_interests: Dict[str, float]) -> List[str]:
        """Find content in the 'gray zone' - not too low interest but not primary interest"""
        # Find tags with moderate interest (0.3-0.7) for exploration
        exploration_tags = []

        for tag, weight in user_interests.items():
            if 0.3 <= weight <= 0.7:
                exploration_tags.append(tag)

        return exploration_tags[:3]  # Limit to 3 exploration tags

    def _calculate_diversity_score(self, new_tags: List[str], existing_recommendations: List[str]) -> float:
        """Calculate diversity to avoid repetitive content"""
        if not existing_recommendations:
            return 1.0

        # Calculate how similar the new content is to recently recommended content
        common_tags = set(new_tags) & set(existing_recommendations)
        diversity = 1.0 - (len(common_tags) / max(len(new_tags), 1))

        return max(0.0, diversity)

    async def _refine_recommendation_with_llm(self, user_interests: Dict[str, float],
                                            content_category: str,
                                            content_tags: List[str]) -> bool:
        """Use LLM to double-check relevance"""
        # Create a more nuanced prompt that considers the user's interest weights
        interest_summary = ", ".join([f"{tag}: {weight:.2f}" for tag, weight in user_interests.items() if weight > 0.1])

        prompt = f"""User interests: {interest_summary}

Content category: {content_category}
Content tags: {', '.join(content_tags)}

Based on the user's interests, would this content be relevant to them?
Consider the strength of their interest in each tag.
Answer with 'yes' or 'no'."""

        safe_prompt = prompt.replace("{", "{{").replace("}", "}}")
        response = await call_llm(safe_prompt)

        if response == "error":
            # Default to the calculated score if LLM fails
            return True

        return "yes" in response.lower()

    async def is_relevant(self, user_id: int, category: str, tags: List[str],
                         interaction_history: List[Dict[str, Any]] = None) -> bool:
        """Main method for enhanced recommendation decision making"""
        if not tags:
            return False

        # Increment metrics counter at the very beginning
        self.metrics["total_recommendations"] += 1

        # Check if user has sufficient interests to apply full personalization
        has_sufficient_interests = self._has_sufficient_interests(user_id)

        # Load profile to check for "Всё" tag (show everything tag)
        profile = get_user_profile(user_id)
        user_has_all_tag = "Всё" in profile.get("preferred_tags", [])

        if user_has_all_tag:
            # If user has "Всё" tag, show them all non-blocked content
            blocked_tags = profile.get("blocked_tags", [])

            # Check if any tags are blocked
            for tag in tags:
                if tag in blocked_tags:
                    return False

            # For "Всё" tag users, accept content unless LLM explicitly says it's bad
            # But don't fail on API errors - treat as accepted when API unavailable
            user_interests = self._load_user_interests(user_id)
            try:
                llm_validation = await self._refine_recommendation_with_llm(user_interests, category, tags)
                # If LLM is available and says "no", respect that
                is_valid_content = llm_validation
            except:
                # If LLM fails (e.g., 429 errors), default to accepting content for "Всё" users
                is_valid_content = True

            if is_valid_content:
                self.metrics["accepted_recommendations"] += 1
                # Update user interests to start building their profile
                # Remove "Всё" tag if user is starting to build real interests
                if len(profile.get("preferred_tags", [])) == 1 and "Всё" in profile["preferred_tags"]:
                    # Don't update interests if still just "Всё" tag
                    pass
                else:
                    # User has other interests now, update them
                    for tag in tags:
                        if tag != "Всё":
                            self._update_user_interests(user_id, tag, 0.1)

            return is_valid_content
        elif not has_sufficient_interests:
            # For users without sufficient interests (less than 3, and not "Всё"), show them all non-blocked content
            blocked_tags = profile.get("blocked_tags", [])

            # Check if any tags are blocked
            for tag in tags:
                if tag in blocked_tags:
                    return False

            # For new users, apply basic LLM validation to ensure content quality
            user_interests = self._load_user_interests(user_id)
            llm_validation = await self._refine_recommendation_with_llm(user_interests, category, tags)

            if llm_validation:
                self.metrics["accepted_recommendations"] += 1
                # Update user interests to start building their profile
                for tag in tags:
                    self._update_user_interests(user_id, tag, 0.1)

            return llm_validation

        # For users with established interests, apply full personalization logic
        # Load user interests with time decay
        user_interests = self._load_user_interests(user_id)

        # Apply time-of-day adjustments
        adjusted_interests = self._apply_time_context(user_interests)

        # Check if this is an exploration recommendation
        if self._should_explore(user_id):
            exploration_tags = self._find_exploration_content(adjusted_interests)
            if exploration_tags and not any(tag in exploration_tags for tag in tags):
                # For exploration, we might still recommend this content if it's
                # in the middle interest range
                content_score = self._calculate_content_score(adjusted_interests, tags)
                if content_score < 0.3:
                    # Check if it has potential for exploration
                    potential_for_exploration = any(adjusted_interests.get(tag, 0) > 0.2 for tag in tags)
                    if not potential_for_exploration:
                        return False

        # Calculate base relevance score
        content_score = self._calculate_content_score(adjusted_interests, tags)

        # Get recently viewed/interacted tags to check for diversity
        recent_tags = []
        if interaction_history:
            for item in interaction_history[-5:]:  # Last 5 interactions
                recent_tags.extend(item.get("tags", []))

        diversity_score = self._calculate_diversity_score(tags, recent_tags)

        # Combine scores: content relevance and diversity
        final_score = content_score * 0.7 + diversity_score * 0.3

        # Threshold for recommendation
        threshold = 0.3

        # Check blocked tags first
        profile = get_user_profile(user_id)
        blocked_tags = profile.get("blocked_tags", [])

        for tag in tags:
            if tag in blocked_tags:
                return False

        # If score is reasonable, verify with LLM
        is_relevant = final_score >= threshold
        if is_relevant and content_score > 0.2:  # Only validate if score isn't too low
            llm_validation = await self._refine_recommendation_with_llm(adjusted_interests, category, tags)
            is_relevant = llm_validation

        if is_relevant:
            self.metrics["accepted_recommendations"] += 1

            # Update user interests based on this recommendation being accepted
            for tag in tags:
                self._update_user_interests(user_id, tag, 0.1)  # Small positive reinforcement

        return is_relevant

    def get_personalization_metrics(self) -> Dict[str, Any]:
        """Return personalization quality metrics"""
        total = self.metrics["total_recommendations"]
        if total == 0:
            acceptance_rate = 0.0
        else:
            acceptance_rate = self.metrics["accepted_recommendations"] / total

        return {
            **self.metrics,
            "acceptance_rate": acceptance_rate
        }


# Global instance to maintain state
recommend_agent_instance = PersonalizationAgent()

async def run(user_id: int, category: str, tags: List[str]) -> bool:
    """Main run function maintaining backward compatibility"""
    is_relevant = await recommend_agent_instance.is_relevant(user_id, category, tags)

    # Log metrics periodically
    if recommend_agent_instance.metrics["total_recommendations"] % 10 == 0:
        logger.info(f"Recommendation agent metrics: {recommend_agent_instance.get_personalization_metrics()}")

    return is_relevant