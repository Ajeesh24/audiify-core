from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
import httpx
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """Service for LLM operations using LangChain for provider flexibility."""

    def __init__(self):
        """Initialize LLM service with default provider."""
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        """Initialize the default LLM provider."""
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        # Create httpx client with SSL verification disabled for corporate environments
        http_client = httpx.AsyncClient(verify=False)

        return ChatOpenAI(
            api_key=settings.openai_api_key,
            model="gpt-3.5-turbo",
            temperature=0.3,  # Lower temperature for more consistent summaries
            max_tokens=2000,
            timeout=30,
            http_async_client=http_client
        )

    async def summarize_article(
        self,
        title: str,
        content: str,
        max_length: Optional[int] = None
    ) -> str:
        """
        Generate a comprehensive summary of an article.

        Args:
            title: Article title
            content: Article content to summarize
            max_length: Maximum summary length in characters

        Returns:
            Generated summary text
        """
        try:
            # Prepare the prompt
            system_prompt = """You are an expert content summarizer. Your task is to create comprehensive,
            engaging summaries of articles that are perfect for audio narration.

            Guidelines:
            1. Create a summary that captures all key points and important details
            2. Write in a natural, conversational tone suitable for listening
            3. Maintain the original article's tone and style
            4. Include relevant examples, statistics, or quotes when important
            5. Structure the summary with clear flow between ideas
            6. Aim for 3-5 paragraphs that tell a complete story
            7. Avoid bullet points or lists - use narrative prose
            8. Make it engaging and informative for audio consumption"""

            length_guidance = ""
            if max_length:
                words = max_length // 5  # Rough estimate: 5 chars per word
                length_guidance = f"Keep the summary to approximately {words} words."

            human_prompt = f"""Please create a comprehensive summary of this article:

            Title: {title}

            Content: {content[:8000]}  # Limit input to avoid token limits

            {length_guidance}

            Focus on making this summary perfect for audio narration - natural, flowing, and engaging."""

            # Create messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            # Generate summary using LangChain 1.2.0 API
            response = await self.llm.ainvoke(messages)
            summary = response.content

            logger.info("Summary generated successfully")

            return self._clean_summary(summary)

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            raise Exception(f"Failed to generate summary: {str(e)}")

    def _clean_summary(self, summary: str) -> str:
        """Clean and format the generated summary."""
        # Remove any unwanted formatting
        cleaned = summary.strip()

        # Ensure proper paragraph breaks
        cleaned = cleaned.replace('\n\n\n', '\n\n')

        # Remove any bullet points or list formatting that might have snuck in
        cleaned = cleaned.replace('• ', '')
        cleaned = cleaned.replace('- ', '')

        return cleaned

    async def enhance_content_for_audio(self, content: str) -> str:
        """
        Enhance content to be more suitable for audio narration.

        Args:
            content: Original content

        Returns:
            Enhanced content optimized for TTS
        """
        try:
            system_prompt = """You are an expert at adapting written content for audio narration.
            Your task is to make the text more suitable for text-to-speech while preserving all information.

            Guidelines:
            1. Expand abbreviations and acronyms on first use
            2. Replace symbols with words (e.g., & becomes "and", % becomes "percent")
            3. Spell out numbers in a natural way for speech
            4. Add natural pauses and transitions between sections
            5. Ensure proper pronunciation cues for difficult words
            6. Maintain all original information and meaning
            7. Keep the tone and style of the original"""

            human_prompt = f"""Please optimize this content for audio narration:

            {content[:10000]}  # Limit to avoid token limits

            Make it sound natural when spoken aloud while keeping all the original information."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            response = await self.llm.ainvoke(messages)
            enhanced = response.content

            return enhanced.strip()

        except Exception as e:
            logger.error(f"Error enhancing content for audio: {str(e)}")
            # Return original content if enhancement fails
            return content

    def switch_provider(self, provider: str, **kwargs):
        """
        Switch LLM provider (for future extensibility).

        Args:
            provider: Provider name ('openai', 'anthropic', 'ollama', etc.)
            **kwargs: Provider-specific configuration
        """
        if provider == "openai":
            # Create httpx client with SSL verification disabled for corporate environments
            http_client = httpx.AsyncClient(verify=False)

            self.llm = ChatOpenAI(
                api_key=kwargs.get('api_key', settings.openai_api_key),
                model=kwargs.get('model', 'gpt-3.5-turbo'),
                temperature=kwargs.get('temperature', 0.3),
                http_async_client=http_client
            )
        # Add other providers as needed
        # elif provider == "anthropic":
        #     from langchain_anthropic import ChatAnthropic
        #     self.llm = ChatAnthropic(...)
        # elif provider == "ollama":
        #     from langchain_ollama import ChatOllama
        #     self.llm = ChatOllama(...)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        logger.info(f"Switched LLM provider to: {provider}")

    def get_token_count(self, text: str) -> int:
        """Estimate token count for the given text."""
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4