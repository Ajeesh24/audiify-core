"""
LLM Service for News Agency
Uses LangChain for consistent OpenAI API integration
"""

from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import logging

from config import OPENAI_SETTINGS

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM operations using LangChain for provider flexibility."""

    def __init__(self):
        """Initialize LLM service with OpenAI provider."""
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        """Initialize the OpenAI LLM provider."""
        if not OPENAI_SETTINGS['api_key']:
            raise ValueError("OpenAI API key not configured")

        return ChatOpenAI(
            api_key=OPENAI_SETTINGS['api_key'],
            model=OPENAI_SETTINGS['model'],
            temperature=OPENAI_SETTINGS['temperature'],
            max_tokens=OPENAI_SETTINGS['max_tokens'],
            timeout=OPENAI_SETTINGS['timeout']
        )

    def categorize_article(
        self,
        title: str,
        summary: str,
        source: str,
        prompt_template: str
    ) -> Dict[str, Any]:
        """
        Categorize an article using LLM.

        Args:
            title: Article title
            summary: Article summary/description
            source: Article source
            prompt_template: Categorization prompt template

        Returns:
            Dict containing category and confidence
        """
        try:
            # Format the prompt with article data
            formatted_prompt = prompt_template.format(
                title=title,
                summary=summary,
                source=source
            )

            # Create messages
            messages = [
                HumanMessage(content=formatted_prompt)
            ]

            # Generate response using LangChain
            response = self.llm.invoke(messages)

            # Parse the response
            result = self._parse_categorization_response(response.content)

            logger.debug(f"Article categorized: {title[:50]}... -> {result.get('category')}")

            return result

        except Exception as e:
            logger.error(f"Error categorizing article: {str(e)}")
            raise Exception(f"Failed to categorize article: {str(e)}")

    def generate_brief(
        self,
        category: str,
        articles: list,
        date: str,
        prompt_template: str,
        target_word_count: int
    ) -> Dict[str, Any]:
        """
        Generate a brief from articles using LLM.

        Args:
            category: Brief category
            articles: List of articles to include
            date: Date for the brief
            prompt_template: Already formatted prompt (not a template)
            target_word_count: Target word count for the brief

        Returns:
            Dict containing generated brief content and metadata
        """
        try:
            # The prompt_template is already formatted from brief_engine, so use it directly
            formatted_prompt = prompt_template

            # Create messages with system prompt for brief generation
            messages = [
                SystemMessage(content=f"""You are a professional tech news narrator creating long-form audio briefings.

⚠️  ABSOLUTE CRITICAL REQUIREMENT: You MUST write EXACTLY {target_word_count} words (±50 words). This is MANDATORY for proper audio timing. DO NOT write short summaries.

🚨 WORD COUNT IS THE TOP PRIORITY 🚨
- If you write less than {target_word_count - 50} words, the audio will be too short and UNUSABLE
- Target: {target_word_count} words
- Minimum: {target_word_count - 50} words (HARD MINIMUM - anything less is REJECTED)
- Maximum: {target_word_count + 50} words
- NO EXCEPTIONS - Count every single word you write

STRATEGY TO REACH {target_word_count} WORDS:
1. Write a comprehensive 150-200 word introduction setting context
2. Cover each story in depth (150-250 words per story minimum)
3. Include technical details, implications, and industry context
4. Add analysis and expert perspective for each story
5. Write a thorough 200-250 word conclusion with outlook
6. If still under word count, add more depth to each story

You must:
1. Use ALL the full article content provided (not just headlines or summaries)
2. Provide comprehensive coverage of each story with technical details
3. Write detailed analysis, not brief summaries - this is PODCAST-LENGTH content
4. Each story should receive 150-250 words minimum of coverage
5. Include background, context, technical details, and future implications
6. Write conversationally but thoroughly - imagine explaining to an intelligent colleague
7. DO NOT SUMMARIZE - write as if you have unlimited time to explain thoroughly

FAILURE TO MEET WORD COUNT WILL RESULT IN UNUSABLE AUDIO. Write detailed, comprehensive analysis that reaches exactly {target_word_count} words."""),
                HumanMessage(content=formatted_prompt)
            ]

            # Generate response using LangChain
            response = self.llm.invoke(messages)

            # Parse and clean the response
            brief_content = self._clean_brief_content(response.content)
            word_count = len(brief_content.split())

            result = {
                'content': brief_content,
                'word_count': word_count,
                'token_usage': self._estimate_token_usage(formatted_prompt, brief_content)
            }

            # Enhanced logging for debugging word count issues
            logger.info(f"Brief generated for {category}: {word_count} words (target: {target_word_count})")

            # Warn if significantly off target
            if word_count < target_word_count - 100:
                logger.warning(f"⚠️  Brief significantly under target: {word_count}/{target_word_count} words (short by {target_word_count - word_count} words)")
                logger.debug(f"Brief preview: {brief_content[:200]}...")
            elif word_count < target_word_count - 50:
                logger.warning(f"Brief slightly under target: {word_count}/{target_word_count} words")
            elif word_count > target_word_count + 100:
                logger.warning(f"Brief significantly over target: {word_count}/{target_word_count} words (over by {word_count - target_word_count} words)")
            else:
                logger.info(f"✓ Brief word count within acceptable range: {word_count}/{target_word_count} words")

            return result

        except Exception as e:
            logger.error(f"Error generating brief: {str(e)}")
            raise Exception(f"Failed to generate brief: {str(e)}")

    def _parse_categorization_response(self, response: str) -> Dict[str, Any]:
        """Parse categorization response from LLM."""
        try:
            # Look for category in the response
            response_lower = response.lower().strip()

            # Default result
            result = {
                'category': 'general-tech',
                'confidence': 0.5,
                'reasoning': response
            }

            # Simple category detection
            if 'ai' in response_lower or 'artificial intelligence' in response_lower or 'machine learning' in response_lower:
                result['category'] = 'ai-ml'
                result['confidence'] = 0.8
            elif 'devops' in response_lower or 'platform' in response_lower or 'infrastructure' in response_lower or 'cloud' in response_lower:
                result['category'] = 'devops-platform'
                result['confidence'] = 0.8
            elif 'general' in response_lower or 'tech' in response_lower:
                result['category'] = 'general-tech'
                result['confidence'] = 0.7

            return result

        except Exception as e:
            logger.warning(f"Error parsing categorization response: {e}")
            return {
                'category': 'general-tech',
                'confidence': 0.3,
                'reasoning': 'Failed to parse response'
            }

    def _format_articles_for_prompt(self, articles: list) -> str:
        """Format articles for inclusion in brief generation prompt."""
        formatted = []
        for i, article in enumerate(articles, 1):
            # Use full content if available, otherwise use summary
            content = article.get('full_content') or article.get('summary', 'No content available')
            content_type = "Full Content" if article.get('content_extracted') else "Summary"

            formatted.append(f"""
Article {i}: {article.get('title', 'No Title')}
Source: {article.get('source', 'Unknown')}
{content_type}: {content}
URL: {article.get('url', '')}
""")
        return "\n".join(formatted)

    def _clean_brief_content(self, content: str) -> str:
        """Clean and format generated brief content."""
        # Remove any unwanted formatting
        cleaned = content.strip()

        # Ensure proper paragraph breaks
        cleaned = cleaned.replace('\n\n\n', '\n\n')

        # Remove any bullet points or list formatting that might have snuck in
        cleaned = cleaned.replace('• ', '')
        cleaned = cleaned.replace('- ', '')

        return cleaned

    def _estimate_token_usage(self, prompt: str, response: str) -> Dict[str, int]:
        """Estimate token usage for cost tracking."""
        # Rough estimation: 1 token ≈ 4 characters
        input_tokens = len(prompt) // 4
        output_tokens = len(response) // 4

        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens
        }

    def get_token_count(self, text: str) -> int:
        """Estimate token count for the given text."""
        return len(text) // 4


# Global LLM service instance
llm_service = LLMService()