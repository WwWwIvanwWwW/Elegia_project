from typing import List, Dict, Any, Optional
from .request import call_llm
import os
import logging
import asyncio
import re
from enum import Enum
from dataclasses import dataclass
from urllib.parse import urlparse
import aiohttp

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    MOBILE = "mobile"
    DESKTOP = "desktop"
    TABLET = "tablet"

class ToneStyle(Enum):
    FORMAL = "formal"
    FRIENDLY = "friendly"
    IRONIC = "ironic"
    NEUTRAL = "neutral"

class OutputFormat(Enum):
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    HTML = "html"
    TELEGRAM = "telegram"

@dataclass
class RenderContext:
    device_type: DeviceType
    tone_style: ToneStyle
    output_format: OutputFormat
    platform_specific: Dict[str, Any]
    user_preferences: Dict[str, Any]

class MultimodalDeliveryAgent:
    def __init__(self):
        self.metrics = {
            "total_renders": 0,
            "image_attachments": 0,
            "format_conversions": 0,
            "tone_applications": 0
        }

        # Emojis for different categories and tones
        self.category_emojis = {
            "technology": ["💻", "📱", "🤖", "🔗"],
            "business": ["💼", "💰", "📈", "🏢"],
            "science": ["🔬", "🔭", "🧬", "⚛️"],
            "culture": ["🎭", "🎨", "🎬", "🎤"],
            "politics": ["🏛️", "📜", "🗳️", "⚖️"],
            "sports": ["⚽", "🏀", "🏈", "🎾"],
            "health": ["🏥", "💊", "🌡️", "⚕️"],
            "general": ["📰", "🗞️", "📋", "🎯"]
        }

        self.tone_emojis = {
            ToneStyle.FORMAL: ["📋", "📑", "✅"],
            ToneStyle.FRIENDLY: ["😊", "👍", "🤗"],
            ToneStyle.IRONIC: ["😏", "🤔", "🙄", "😅"],
            ToneStyle.NEUTRAL: ["🔹", "🔸", "▪️"]
        }

    def _determine_device_type(self, platform_info: Dict[str, Any]) -> DeviceType:
        """Determine device type from platform information"""
        agent = platform_info.get("user_agent", "").lower()

        if "mobile" in agent or "android" in agent or "iphone" in agent:
            return DeviceType.MOBILE
        elif "tablet" in agent:
            return DeviceType.TABLET
        else:
            return DeviceType.DESKTOP

    def _apply_device_adaptation(self, content: str, device_type: DeviceType) -> str:
        """Adapt content for different devices"""
        if device_type == DeviceType.MOBILE:
            # Shorter lines for mobile
            lines = content.split('\n')
            adapted_lines = []
            for line in lines:
                if len(line) > 60:  # Break long lines for mobile
                    # Simple word wrap
                    words = line.split()
                    current_line = ""
                    for word in words:
                        if len(current_line + " " + word) <= 60:
                            current_line += " " + word if current_line else word
                        else:
                            adapted_lines.append(current_line)
                            current_line = word
                    if current_line:
                        adapted_lines.append(current_line)
                else:
                    adapted_lines.append(line)
            return '\n'.join(adapted_lines)
        else:
            return content  # Desktop/tablet can handle longer lines

    def _get_appropriate_emoji(self, category: str, tone: ToneStyle) -> str:
        """Get appropriate emoji based on category and tone"""
        # First try to get emoji based on tone
        tone_emojis = self.tone_emojis.get(tone, ["🔹"])

        # If category-specific emojis exist, use those; otherwise use tone-based
        category_emojis = self.category_emojis.get(category.lower(),
                                                 self.category_emojis["general"])

        # If tone is neutral or formal, prefer category emojis
        if tone in [ToneStyle.NEUTRAL, ToneStyle.FORMAL]:
            return category_emojis[0] if category_emojis else "🔹"
        else:
            # For friendly or ironic, blend based on content
            return tone_emojis[0] if tone_emojis else "🔹"

    def _apply_tone_style(self, content: str, tone: ToneStyle, category: str) -> str:
        """Apply specific tone to content"""
        self.metrics["tone_applications"] += 1

        if tone == ToneStyle.FORMAL:
            # More professional, structured tone
            content = content.replace("!", ".").replace("?", ".")
        elif tone == ToneStyle.FRIENDLY:
            # Add friendly expressions
            if "!" not in content[:20]:  # Only add if not already excited
                content += "!"
        elif tone == ToneStyle.IRONIC:
            # Add ironic or skeptical language
            irony_phrases = ["(очередная сенсация)", "(наверняка)", "(вот это да)", "(не иначе как)"]
            import random
            content += f" {random.choice(irony_phrases)}"

        return content

    def _format_for_platform(self, content: str, format_type: OutputFormat) -> str:
        """Format content for specific output format"""
        self.metrics["format_conversions"] += 1

        if format_type == OutputFormat.PLAIN_TEXT:
            # Remove all markdown formatting
            content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Bold
            content = re.sub(r'\*(.*?)\*', r'\1', content)      # Italic
            content = re.sub(r'#(.*?) ', r'[\1] ', content)     # Links
            return content
        elif format_type == OutputFormat.HTML:
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
            content = content.replace("\n", "<br>")
            return content
        elif format_type == OutputFormat.TELEGRAM:
            # Telegram already supports markdown, but we may need to adapt for limits
            # Check if content is too long for Telegram
            if len(content) > 4096:  # Telegram message limit
                content = content[:4090] + "... (continued)"
            return content
        else:
            # Markdown format
            return content

    async def _fetch_image(self, url: str) -> Optional[str]:
        """Try to fetch image from URL if available"""
        try:
            # Check if the URL contains image extensions
            parsed = urlparse(url)
            if any(parsed.path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                return url  # Assume it's an image URL

            # In a real implementation, we might extract image from the article URL
            # For now, return None
            return None
        except Exception as e:
            logger.warning(f"Could not process image URL {url}: {e}")
            return None

    def _apply_length_optimization(self, summary: str, device_type: DeviceType) -> str:
        """Optimize summary length for different devices"""
        if device_type == DeviceType.MOBILE and len(summary) > 300:
            # Truncate for mobile with a "Read more" hint
            sentences = summary.split('.')
            optimized = []
            length = 0
            for sentence in sentences:
                if length + len(sentence) > 250:
                    optimized.append(sentence.strip() + "...")
                    break
                optimized.append(sentence.strip())
                length += len(sentence) + 1
            return '. '.join(optimized)
        return summary

    def _create_dynamic_buttons(self, tags: List[str]) -> str:
        """Create dynamic buttons for user interaction"""
        buttons = []
        if tags:
            # Add search button for first tag
            buttons.append(f"🔍 Похожие по #{tags[0]}: `/search {tags[0]}`")

            # Add bookmark button
            buttons.append("🔖 В закладки: `/bookmark`")

            # Add share button
            buttons.append("📤 Поделиться: `/share`")

        return "\n".join(buttons)

    async def _generate_audio_digest(self, summary: str) -> Optional[str]:
        """Generate audio digest (placeholder - in real app, use TTS service)"""
        # This would call a TTS service in a real implementation
        # Returning None as a placeholder
        return None

    def _optimize_for_telegram_limits(self, content: str) -> List[str]:
        """Split content to comply with Telegram limits"""
        max_length = 4096
        if len(content) <= max_length:
            return [content]

        # Split by paragraphs if possible
        paragraphs = content.split('\n\n')
        messages = []
        current_message = ""

        for paragraph in paragraphs:
            if len(current_message) + len(paragraph) <= max_length:
                current_message += paragraph + "\n\n"
            else:
                if current_message:
                    messages.append(current_message.strip())
                current_message = paragraph + "\n\n"

        if current_message.strip():
            messages.append(current_message.strip())

        return messages

    async def render_news_with_enhancements(
        self,
        title: str,
        summary: str,
        category: str,
        tags: List[str],
        url: str,
        user_preferences: Dict[str, Any] = None,
        platform_info: Dict[str, Any] = None,
        tone: str = "neutral"
    ) -> List[str]:  # Return list to handle split messages
        """Main method for enhanced news rendering"""
        self.metrics["total_renders"] += 1

        # Set default context
        user_prefs = user_preferences or {}
        platform_info = platform_info or {}

        # Determine context
        device_type = self._determine_device_type(platform_info)
        output_format = OutputFormat(user_prefs.get("format", "telegram"))
        tone_style = ToneStyle(tone) if tone in [e.value for e in ToneStyle] else ToneStyle.NEUTRAL

        # Apply device-specific optimizations
        optimized_summary = self._apply_length_optimization(summary, device_type)

        # Get appropriate emoji
        emoji = self._get_appropriate_emoji(category, tone_style)

        # Build the message with proper formatting
        tags_str = " ".join([f"#{tag}" for tag in tags]) if tags else ""

        # Create the base message with tone-appropriate language
        message_parts = [
            f"{emoji} **{category.title()}**",
            "",
            f"**{title}**",
            "",
            optimized_summary,
        ]

        if tags_str:
            message_parts.extend(["", tags_str])

        message_parts.extend(["", f"🌐 [Читать оригинал]({url})"])

        # Apply tone style to the summary part
        content_with_tone = "\n".join(message_parts)
        content_with_tone = self._apply_tone_style(content_with_tone, tone_style, category)

        # Add dynamic buttons
        buttons = self._create_dynamic_buttons(tags)
        if buttons:
            content_with_tone += f"\n\n{buttons}"

        # Apply platform-specific formatting
        formatted_content = self._format_for_platform(content_with_tone, output_format)

        # Optimize for platform limits (especially Telegram)
        final_messages = self._optimize_for_telegram_limits(formatted_content)

        # In a real app, we might also generate audio digest here
        # audio_digest = await self._generate_audio_digest(summary)

        return final_messages

    def get_rendering_metrics(self) -> Dict[str, Any]:
        """Return rendering quality metrics"""
        return self.metrics.copy()


# Global instance to maintain state
render_agent_instance = MultimodalDeliveryAgent()

async def run(title: str, summary: str, category: str, tags: List[str], url: str, style: str = "full",
             user_preferences: Dict[str, Any] = None, platform_info: Dict[str, Any] = None,
             tone: str = "neutral") -> str:
    """Main run function maintaining backward compatibility"""
    messages = await render_agent_instance.render_news_with_enhancements(
        title, summary, category, tags, url, user_preferences, platform_info, tone
    )

    # Return first message for backward compatibility, but log if there are multiple
    if len(messages) > 1:
        logger.info(f"Render agent created {len(messages)} messages due to platform limits")

    # Log metrics periodically
    if render_agent_instance.metrics["total_renders"] % 10 == 0:
        logger.info(f"Render agent metrics: {render_agent_instance.get_rendering_metrics()}")

    return messages[0] if messages else ""