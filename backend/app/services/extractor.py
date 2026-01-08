import re
import asyncio
from typing import Optional, Tuple
from urllib.parse import urlparse
import newspaper
from newspaper import Article
from bs4 import BeautifulSoup
import requests
import logging
import ssl
import urllib3
import time

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

        # Pre-compile regex patterns for better performance
        self._compile_cleaning_patterns()

        # Social media domains that require special handling
        self.social_media_domains = [
            'facebook.com', 'fb.com', 'm.facebook.com',
            'twitter.com', 'x.com', 'mobile.twitter.com',
            'instagram.com', 'linkedin.com', 'tiktok.com',
            'snapchat.com', 'pinterest.com'
        ]

    def _compile_cleaning_patterns(self):
        """Pre-compile regex patterns for better performance."""
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

        self.compiled_promotional_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in promotional_patterns
        ]

    def _is_social_media_url(self, url: str) -> bool:
        """Check if URL is from a social media platform."""
        url_lower = url.lower()
        return any(domain in url_lower for domain in self.social_media_domains)

    async def extract_article(self, url: str) -> Tuple[str, str, bool]:
        """
        Extract article content from URL.

        Args:
            url: Article URL to extract

        Returns:
            Tuple of (title, content, is_paywalled)
        """
        try:
            # Check if this is a social media URL and provide better error handling
            if self._is_social_media_url(url):
                logger.info(f"Attempting extraction from social media URL: {url}")
                try:
                    return await self._extract_social_media_content(url)
                except Exception as social_error:
                    logger.warning(f"Social media extraction failed for {url}: {str(social_error)}")
                    # Provide helpful error message for social media URLs
                    raise Exception(
                        "Social media posts often require login or have restricted access. "
                        "Try using a direct link to a news article or blog post instead. "
                        "For Twitter/X posts, try using a screenshot or copying the text manually."
                    )

            # Existing extraction logic remains unchanged
            # First try with newspaper3k (fastest and most reliable)
            article = Article(url)

            # Configure requests session to disable SSL verification
            article.config.requests_params = {'verify': False}
            article.config.http_success_only = False

            article.download()
            article.parse()

            # Check if we got meaningful content
            if len(article.text.strip()) > 500:
                return article.title or "", article.text, False

            # If newspaper3k didn't get much content, try advanced BeautifulSoup approach
            logger.info(f"Newspaper3k got limited content for {url}, trying advanced extraction...")
            return await self._extract_with_beautifulsoup(url)

        except Exception as e:
            logger.error(f"Error extracting article from {url}: {str(e)}")
            # Try BeautifulSoup as fallback
            try:
                return await self._extract_with_beautifulsoup(url)
            except Exception as fallback_error:
                logger.error(f"BeautifulSoup fallback also failed: {str(fallback_error)}")
                raise Exception(f"Failed to extract article: {str(e)}")

    async def _extract_social_media_content(self, url: str) -> Tuple[str, str, bool]:
        """
        Attempt to extract content from social media URLs using specialized headers.

        Args:
            url: Social media URL to extract

        Returns:
            Tuple of (title, content, is_paywalled)
        """
        # Use social media specific headers for better access
        social_headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

        # Add platform-specific headers
        if 'facebook.com' in url or 'fb.com' in url:
            social_headers['User-Agent'] = 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'
        elif 'twitter.com' in url or 'x.com' in url:
            social_headers['User-Agent'] = 'Twitterbot/1.0'

        try:
            # Shorter timeout for social media to fail fast
            response = self.session.get(url, headers=social_headers, timeout=10, verify=False)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract Open Graph data (common on social media)
            title = ""
            content = ""

            # Try Open Graph title
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '')

            # Try Open Graph description
            og_description = soup.find('meta', property='og:description')
            if og_description:
                content = og_description.get('content', '')

            # Try Twitter Card data
            if not title:
                twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
                if twitter_title:
                    title = twitter_title.get('content', '')

            if not content:
                twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
                if twitter_desc:
                    content = twitter_desc.get('content', '')

            # If still no content, try basic meta description
            if not content:
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    content = meta_desc.get('content', '')

            # Validate we got meaningful content
            if len(content.strip()) < 50:
                raise Exception("Insufficient content extracted from social media post")

            return title.strip(), content.strip(), False

        except Exception as e:
            logger.error(f"Social media extraction failed for {url}: {str(e)}")
            raise e

    async def _extract_with_beautifulsoup(self, url: str) -> Tuple[str, str, bool]:
        """Extract article using BeautifulSoup with advanced content detection."""
        try:
            # Use multiple user agents to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            # Add delay to be respectful to servers
            await asyncio.sleep(0.5)

            # Use shorter timeout for faster failure, but keep existing logic
            timeout = 15  # Reduced from 30 to 15 seconds for faster processing
            response = self.session.get(url, headers=headers, timeout=timeout, verify=False)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'aside', 'header']):
                element.decompose()

            # Check for paywall indicators
            paywall_indicators = [
                'paywall', 'subscription', 'premium', 'subscriber-only',
                'sign-up', 'register', 'login-required', 'members-only'
            ]

            is_paywalled = False
            page_text = soup.get_text().lower()
            for indicator in paywall_indicators:
                if indicator in page_text and ('subscribe' in page_text or 'sign up' in page_text):
                    is_paywalled = True
                    break

            # Extract title with multiple strategies
            title = ""
            title_selectors = [
                'h1[class*="title"]', 'h1[class*="headline"]',
                '.article-title', '.post-title', '.entry-title',
                'h1', 'title', 'meta[property="og:title"]', 'meta[name="title"]'
            ]

            for selector in title_selectors:
                element = soup.select_one(selector)
                if element:
                    if element.name == 'meta':
                        title = element.get('content', '')
                    else:
                        title = element.get_text(strip=True)
                    if title and len(title) > 10:  # Ensure meaningful title
                        break

            # Extract content with comprehensive selectors
            content_selectors = [
                'article[class*="content"]', 'div[class*="article-body"]',
                'div[class*="post-content"]', 'div[class*="entry-content"]',
                '.article-text', '.post-text', '.story-body',
                'article', 'main[role="main"]', '.content',
                'div[itemprop="articleBody"]', '[data-module="ArticleBody"]'
            ]

            content = ""
            content_length = 0

            for selector in content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Remove ads and promotional content
                    for ad_element in element.select('[class*="ad"], [class*="advertisement"], [class*="promo"]'):
                        ad_element.decompose()

                    text = element.get_text(separator='\n', strip=True)
                    if len(text) > content_length:
                        content = text
                        content_length = len(text)

                    if content_length > 1000:  # Good amount of content found
                        break

                if content_length > 1000:
                    break

            # If still insufficient content, try paragraph-based extraction
            if content_length < 500:
                paragraphs = []
                for p in soup.select('p'):
                    text = p.get_text(strip=True)
                    if len(text) > 50 and not any(x in text.lower() for x in ['advertisement', 'cookie', 'privacy']):
                        paragraphs.append(text)

                content = '\n\n'.join(paragraphs)
                content_length = len(content)

            # Final content validation
            if content_length < 200:
                # Last resort: get all meaningful text
                all_text = soup.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                meaningful_lines = [
                    line for line in lines
                    if len(line) > 30 and not any(
                        x in line.lower() for x in [
                            'menu', 'navigation', 'footer', 'copyright', 'cookie',
                            'advertisement', 'subscribe', 'follow us', 'share'
                        ]
                    )
                ]
                content = '\n'.join(meaningful_lines[:50])  # Limit to reasonable amount

            if len(content.strip()) < 100:
                raise Exception("Insufficient content extracted after all attempts")

            return title.strip(), content.strip(), is_paywalled

        except Exception as e:
            logger.error(f"BeautifulSoup extraction failed for {url}: {str(e)}")
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

        # Use pre-compiled patterns for better performance
        cleaned_content = content
        for compiled_pattern in self.compiled_promotional_patterns:
            cleaned_content = compiled_pattern.sub('', cleaned_content)

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

            # For social media URLs, provide more specific validation
            if self._is_social_media_url(url):
                logger.info(f"Social media URL detected: {url}")
                # Still try validation but with shorter timeout
                try:
                    response = self.session.head(url, timeout=5, allow_redirects=True)
                    return response.status_code == 200
                except Exception:
                    # Don't fail validation for social media - let extraction handle it
                    return True

            # Check if URL is accessible with shorter timeout for faster processing
            timeout = 8  # Reduced from 10 to 8 seconds
            response = self.session.head(url, timeout=timeout, allow_redirects=True)

            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                return False

            return response.status_code == 200

        except Exception:
            return False