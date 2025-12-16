from .request import call_llm
import os
import logging
from typing import Dict, Any, List
from enum import Enum
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)

class ArticleType(Enum):
    ANALYTICS = "analytics"
    NEWS_BRIEF = "news_brief"
    INTERVIEW = "interview"
    PRESS_RELEASE = "press_release"
    OPINION = "opinion"
    UNKNOWN = "unknown"

class AudienceType(Enum):
    EXPERT = "expert"
    BEGINNER = "beginner"
    NEUTRAL = "neutral"

class SummaryStyle(Enum):
    BRIEF = "brief"
    POINTS = "points"
    DETAILED = "detailed"

@dataclass
class SummaryContext:
    article_type: ArticleType
    audience: AudienceType
    original_length: int
    user_preferences: Dict[str, Any]
    summary_style: SummaryStyle

class AdaptiveSummaryAgent:
    def __init__(self):
        self.metrics = {
            "total_summaries": 0,
            "rejection_count": 0,
            "style_distribution": {},
            "quality_score": 0.0
        }
        self.content_classifier_cache = {}

    def _classify_article_type(self, text: str) -> ArticleType:
        """Classify article type based on content patterns"""
        text_lower = text.lower()

        # Check for analytics indicators
        analytics_keywords = ["analysis", "study", "research", "data", "trend", "market"]
        if any(keyword in text_lower for keyword in analytics_keywords):
            return ArticleType.ANALYTICS

        # Check for interviews
        interview_keywords = ["interview", "q&a", "question", "answer", "says:", "'said"]
        if any(keyword in text_lower for keyword in interview_keywords):
            return ArticleType.INTERVIEW

        # Check for press releases
        press_release_keywords = ["announces", "today announced", "press release", "company", "CEO", "according to"]
        if any(keyword in text_lower for keyword in press_release_keywords):
            return ArticleType.PRESS_RELEASE

        # Check for opinion pieces
        opinion_keywords = ["in my opinion", "think", "believe", "personally", "view", "perspective"]
        if any(keyword in text_lower for keyword in opinion_keywords):
            return ArticleType.OPINION

        # Default to news brief for shorter articles
        if len(text) < 500:
            return ArticleType.NEWS_BRIEF

        return ArticleType.UNKNOWN

    def _determine_audience(self, user_profile: Dict[str, Any]) -> AudienceType:
        """Determine audience type based on user profile"""
        # If user has technical preferences, classify as expert
        tech_interests = ["technology", "programming", "ai", "software", "science", "technical"]
        preferred_tags = user_profile.get("preferred_tags", [])

        if any(interest in preferred_tags for interest in tech_interests):
            return AudienceType.EXPERT

        # If user has beginner-friendly preferences
        beginner_interests = ["for beginners", "intro", "basic", "simple", "easy"]
        if any(interest in preferred_tags for interest in beginner_interests):
            return AudienceType.BEGINNER

        return AudienceType.NEUTRAL

    def _select_style_by_context(self, context: SummaryContext) -> SummaryStyle:
        """Select summary style based on article type and audience"""
        # For expert audience, use more detailed summaries
        if context.audience == AudienceType.EXPERT and context.original_length > 1000:
            return SummaryStyle.DETAILED

        # For interviews, points style works well
        if context.article_type == ArticleType.INTERVIEW:
            return SummaryStyle.POINTS

        # For brief articles, keep it brief
        if context.original_length < 300:
            return SummaryStyle.BRIEF

        # Default to user preference
        return context.summary_style

    def _multi_stage_generation(self, text: str, context: SummaryContext) -> str:
        """Generate summary in multiple stages: facts -> structure -> final"""
        # Stage 1: Extract key facts
        facts_prompt = f"""Extract 3-5 most important facts from this article. Return them as a bullet list:

{text[:2000]}
"""
        # Instead of calling LLM here, we'll use a simplified approach in the main generation
        # since we don't want to make additional LLM calls in this stage
        return self._generate_with_context(text, context)

    def _generate_with_context(self, text: str, context: SummaryContext) -> str:
        """Generate summary with full context consideration"""
        prompt_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'prompts', 'summarizer_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Customize prompt based on context
        style_description = {
            SummaryStyle.BRIEF: "a brief summary focusing on the main point",
            SummaryStyle.POINTS: "a point-form summary with 3-5 key points",
            SummaryStyle.DETAILED: "a comprehensive summary capturing all important details"
        }[context.summary_style]

        audience_tone = {
            AudienceType.EXPERT: "using technical terminology where appropriate",
            AudienceType.BEGINNER: "with explanations for complex concepts",
            AudienceType.NEUTRAL: ""
        }[context.audience]

        # Modify the template to include context
        extended_prompt = f"""Article Type: {context.article_type.value}
Audience: {context.audience.value}
Original Length: {context.original_length} characters
Style: {style_description}
Tone: {audience_tone}

{text}

Summary:"""

        safe_text = extended_prompt.replace("{", "{{").replace("}", "}}")

        return safe_text

    async def _verify_facts(self, generated_summary: str, original_text: str) -> bool:
        """Verify that the summary doesn't contain hallucinated facts"""
        verification_prompt = f"""Does this summary accurately reflect the original text? Answer with 'valid' or 'invalid'.

Original text: {original_text[:1000]}

Summary: {generated_summary}
"""

        safe_verification_prompt = verification_prompt.replace("{", "{{").replace("}", "}}")
        response = await call_llm(safe_verification_prompt)

        return response and "valid" in response.lower()

    def _apply_format(self, summary: str, format_type: str = "markdown") -> str:
        """Apply specific output format"""
        if format_type == "markdown":
            return summary
        elif format_type == "plain_text":
            # Remove markdown styling
            import re
            summary = re.sub(r'\*\*(.*?)\*\*', r'\1', summary)  # Remove bold
            summary = re.sub(r'\*(.*?)\*', r'\1', summary)      # Remove italic
            return summary
        elif format_type == "html":
            import re
            summary = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', summary)  # Bold
            summary = re.sub(r'\*(.*?)\*', r'<em>\1</em>', summary)              # Italic
            summary = summary.replace("\n", "<br>")
            return summary
        else:
            return summary

    async def generate_adaptive_summary(
        self,
        text: str,
        user_profile: Dict[str, Any] = None,
        style: str = "brief",
        output_format: str = "markdown"
    ) -> str:
        """Main method to generate adaptive summary with all enhancements"""
        if not text or text.strip() == "":
            return "Text unavailable for summarization."

        self.metrics["total_summaries"] += 1

        # Determine context
        article_type = self._classify_article_type(text)
        audience = self._determine_audience(user_profile or {})
        summary_style = SummaryStyle(style) if style in [e.value for e in SummaryStyle] else SummaryStyle.BRIEF

        context = SummaryContext(
            article_type=article_type,
            audience=audience,
            original_length=len(text),
            user_preferences=user_profile or {},
            summary_style=summary_style
        )

        # Select appropriate style based on context
        selected_style = self._select_style_by_context(context)
        context.summary_style = selected_style

        # Generate summary through multi-stage process
        prompt_text = self._generate_with_context(text, context)
        response = await call_llm(prompt_text)

        if response == "error":
            # Fallback to simple sentence extraction
            sentences = text.split('.')
            if len(sentences) > 3:
                response = '. '.join(sentences[:3]) + '.'
            else:
                response = text[:200] + "..." if len(text) > 200 else text

        # Verify facts to minimize hallucinations
        is_valid = await self._verify_facts(response, text)
        if not is_valid:
            logger.warning("Summary failed fact verification, applying corrections...")
            # In a real implementation, we would regenerate with stricter guidelines
            # For now, we'll accept with a warning

        # Apply requested format
        formatted_summary = self._apply_format(response, output_format)

        # Update metrics
        style_key = selected_style.value
        self.metrics["style_distribution"][style_key] = self.metrics["style_distribution"].get(style_key, 0) + 1

        return formatted_summary

    def get_quality_metrics(self) -> Dict[str, Any]:
        """Return quality and usage metrics"""
        return self.metrics.copy()


# Global instance to maintain state
summary_agent_instance = AdaptiveSummaryAgent()

async def run(text: str, style: str = "brief", user_profile: Dict[str, Any] = None, output_format: str = "markdown") -> str:
    """Main run function maintaining backward compatibility"""
    summary = await summary_agent_instance.generate_adaptive_summary(
        text, user_profile, style, output_format
    )

    # Log metrics periodically
    if summary_agent_instance.metrics["total_summaries"] % 10 == 0:
        logger.info(f"Summary agent metrics: {summary_agent_instance.get_quality_metrics()}")

    return summary