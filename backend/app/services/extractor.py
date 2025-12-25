import re
import asyncio
from typing import Optional, Tuple
from urllib.parse import urlparse
import newspaper
from newspaper import Article
from bs4 import BeautifulSoup
import requests
from playwright.async_api import async_playwright
import logging
import ssl
import urllib3

# Disable SSL warnings for corporate environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ArticleExtractor:
    """Service for extracting and cleaning article content from URLs."""

    def __init__(self):
        """Initialize the article extractor."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # Disable SSL verification for corporate environments
        self.session.verify = False

    async def extract_article(self, url: str) -> Tuple[str, str, bool]:
        """
        Extract article content from URL.

        Args:
            url: Article URL to extract

        Returns:
            Tuple of (title, content, is_paywalled)
        """
        try:
            # First try with newspaper3k
            article = Article(url)

            # Configure requests session to disable SSL verification
            article.config.requests_params = {'verify': False}
            article.config.http_success_only = False

            article.download()
            article.parse()

            # Check if we got meaningful content
            if len(article.text.strip()) > 500:
                return article.title or "", article.text, False

            # If newspaper3k didn't get much content, try with Playwright
            logger.info(f"Newspaper3k got limited content for {url}, trying Playwright...")
            return await self._extract_with_playwright(url)

        except Exception as e:
            logger.error(f"Error extracting article from {url}: {str(e)}")
            # Try Playwright as fallback
            try:
                return await self._extract_with_playwright(url)
            except Exception as fallback_error:
                logger.error(f"Playwright fallback also failed: {str(fallback_error)}")
                raise Exception(f"Failed to extract article: {str(e)}")

    async def _extract_with_playwright(self, url: str) -> Tuple[str, str, bool]:
        """Extract article using Playwright for JavaScript-heavy sites."""
        async with async_playwright() as p:
            # Launch browser with ignore certificate errors
            browser = await p.chromium.launch(
                headless=True,
                args=['--ignore-certificate-errors', '--ignore-ssl-errors', '--ignore-certificate-errors-spki-list']
            )
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()

            try:
                # Navigate to page
                await page.goto(url, wait_until='networkidle')

                # Check for paywall indicators
                paywall_selectors = [
                    '[class*="paywall"]',
                    '[class*="subscription"]',
                    '[class*="premium"]',
                    '[id*="paywall"]',
                    'text="Subscribe"',
                    'text="Sign up"',
                    'text="Already a subscriber"'
                ]

                is_paywalled = False
                for selector in paywall_selectors:
                    if await page.locator(selector).count() > 0:
                        is_paywalled = True
                        break

                # Extract title
                title_selectors = ['h1', '.article-title', '.headline', '[class*="title"]']
                title = ""
                for selector in title_selectors:
                    title_element = page.locator(selector).first
                    if await title_element.count() > 0:
                        title = await title_element.inner_text()
                        break

                # Extract main content
                content_selectors = [
                    'article',
                    '.article-content',
                    '.post-content',
                    '.entry-content',
                    '[class*="article-body"]',
                    '.content',
                    'main'
                ]

                content = ""
                for selector in content_selectors:
                    content_element = page.locator(selector).first
                    if await content_element.count() > 0:
                        content = await content_element.inner_text()
                        if len(content.strip()) > 500:  # Got meaningful content
                            break

                # If still no good content, get all p tags
                if len(content.strip()) < 500:
                    paragraphs = await page.locator('p').all_inner_texts()
                    content = '\n\n'.join([p.strip() for p in paragraphs if len(p.strip()) > 50])

                await browser.close()

                if len(content.strip()) < 100:
                    raise Exception("Insufficient content extracted")

                return title.strip(), content.strip(), is_paywalled

            except Exception as e:
                await browser.close()
                raise e

    def clean_content(self, content: str) -> str:
        """
        Clean extracted content by removing ads, promotions, and unwanted elements.

        Args:
            content: Raw article content

        Returns:
            Cleaned content suitable for TTS
        """
        if not content:
            return ""

        # Remove common promotional phrases and elements
        promotional_patterns = [
            r'Subscribe to.*?newsletter',
            r'Sign up for.*?updates',
            r'Follow us on.*?',
            r'Click here to.*?',
            r'Read more:.*?',
            r'Related:.*?',
            r'ADVERTISEMENT',
            r'Advertisement',
            r'Sponsored content',
            r'This article is premium content',
            r'Subscribe now to read',
            r'Already a subscriber\?',
            r'Continue reading with.*?',
            r'Get unlimited access',
            r'Join.*?today',
            r'Share on.*?',
            r'Cookie Policy',
            r'Privacy Policy',
            r'Terms of Service',
            r'\[.*?\]',  # Remove content in square brackets
            r'\(Ad\)',
            r'\(Advertisement\)',
        ]

        cleaned_content = content
        for pattern in promotional_patterns:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.IGNORECASE | re.MULTILINE)

        # Remove excessive whitespace and newlines
        cleaned_content = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_content)  # Max 2 consecutive newlines
        cleaned_content = re.sub(r' +', ' ', cleaned_content)  # Multiple spaces to single space

        # Remove social media handles and hashtags
        cleaned_content = re.sub(r'@\w+', '', cleaned_content)
        cleaned_content = re.sub(r'#\w+', '', cleaned_content)

        # Remove URLs
        cleaned_content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', cleaned_content)

        # Clean up formatting characters
        cleaned_content = cleaned_content.replace('\u00a0', ' ')  # Non-breaking space
        cleaned_content = cleaned_content.replace('\u2019', "'")  # Smart apostrophe
        cleaned_content = cleaned_content.replace('\u201c', '"')  # Smart quote
        cleaned_content = cleaned_content.replace('\u201d', '"')  # Smart quote

        return cleaned_content.strip()

    def calculate_reading_time(self, text: str) -> int:
        """Calculate estimated reading time in minutes."""
        words = len(text.split())
        # Average reading speed is 200-250 words per minute
        return max(1, round(words / 225))

    async def validate_url(self, url: str) -> bool:
        """
        Validate if URL is accessible and likely contains an article.

        Args:
            url: URL to validate

        Returns:
            True if URL seems valid for article extraction
        """
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False

            # Check if URL is accessible
            response = self.session.head(url, timeout=10, allow_redirects=True)

            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                return False

            return response.status_code == 200

        except Exception:
            return False