"""
RSS Feeds Configuration

Curated list of high-quality tech news sources for automated collection
Organized by category for the 3 daily briefing types
"""

# RSS feeds organized by category
RSS_FEEDS = {
    "general-tech": [
        {
            "name": "TechCrunch",
            "url": "https://techcrunch.com/feed/",
            "priority": 1,
            "description": "Startup and business technology news"
        },
        {
            "name": "The Verge",
            "url": "https://www.theverge.com/rss/index.xml",
            "priority": 1,
            "description": "Consumer technology and digital culture"
        },
        {
            "name": "Ars Technica",
            "url": "https://feeds.arstechnica.com/arstechnica/index",
            "priority": 2,
            "description": "In-depth technology analysis"
        },
        {
            "name": "Wired",
            "url": "https://www.wired.com/feed/rss",
            "priority": 2,
            "description": "Technology, science, culture, and business"
        },
        {
            "name": "Engadget",
            "url": "https://www.engadget.com/rss.xml",
            "priority": 2,
            "description": "Consumer electronics and gadgets"
        },
        {
            "name": "VentureBeat",
            "url": "https://venturebeat.com/feed/",
            "priority": 3,
            "description": "Enterprise technology and startups"
        },
        {
            "name": "TechCrunch Startups",
            "url": "https://techcrunch.com/category/startups/feed/",
            "priority": 2,
            "description": "Startup news and funding"
        },
        {
            "name": "ZDNet",
            "url": "https://www.zdnet.com/news/rss.xml",
            "priority": 2,
            "description": "Business technology news"
        }
    ],

    "ai-ml": [
        {
            "name": "MIT Technology Review AI",
            "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
            "priority": 1,
            "description": "AI research and applications"
        },
        {
            "name": "VentureBeat AI",
            "url": "https://venturebeat.com/feed/",
            "priority": 1,
            "description": "AI business and enterprise applications"
        },
        {
            "name": "AI News",
            "url": "https://www.artificialintelligence-news.com/feed/",
            "priority": 2,
            "description": "Latest AI developments and research"
        },
        {
            "name": "OpenAI Blog",
            "url": "https://openai.com/index/rss.xml",
            "priority": 1,
            "description": "OpenAI research updates and releases"
        },
        {
            "name": "Google AI Blog",
            "url": "https://blog.research.google/feeds/posts/default",
            "priority": 1,
            "description": "Google's AI research and developments"
        },
        {
            "name": "Hugging Face Blog",
            "url": "https://huggingface.co/blog/feed.xml",
            "priority": 2,
            "description": "ML community and model updates"
        },
        {
            "name": "The AI Index",
            "url": "https://aiindex.stanford.edu/feed/",
            "priority": 2,
            "description": "Stanford AI research and trends"
        }
    ],

    "devops-platform": [
        {
            "name": "AWS News Blog",
            "url": "https://aws.amazon.com/blogs/aws/feed/",
            "priority": 1,
            "description": "AWS service updates and announcements"
        },
        {
            "name": "Google Cloud Blog",
            "url": "https://cloud.google.com/blog/rss",
            "priority": 1,
            "description": "Google Cloud platform updates"
        },
        {
            "name": "Microsoft Azure Blog",
            "url": "https://azure.microsoft.com/en-us/blog/feed/",
            "priority": 1,
            "description": "Azure cloud services and updates"
        },
        {
            "name": "Docker Blog",
            "url": "https://www.docker.com/blog/feed/",
            "priority": 2,
            "description": "Container technology and Docker updates"
        },
        {
            "name": "Kubernetes Blog",
            "url": "https://kubernetes.io/feed.xml",
            "priority": 2,
            "description": "Kubernetes orchestration platform news"
        },
        {
            "name": "GitHub Blog",
            "url": "https://github.blog/feed/",
            "priority": 2,
            "description": "GitHub platform and developer tools"
        },
        {
            "name": "HashiCorp Blog",
            "url": "https://www.hashicorp.com/blog/feed",
            "priority": 3,
            "description": "Infrastructure automation and security"
        },
        {
            "name": "DevOps.com",
            "url": "https://devops.com/feed/",
            "priority": 3,
            "description": "DevOps practices and tools"
        }
    ]
}

# Feed collection settings
COLLECTION_SETTINGS = {
    # How many articles to collect per feed (to avoid overwhelming the system)
    "max_articles_per_feed": 10,

    # Maximum age of articles to consider (in hours)
    "max_article_age_hours": 24,

    # Timeout for RSS feed requests (in seconds)
    "request_timeout": 30,

    # Retry settings for failed requests
    "max_retries": 3,
    "retry_delay": 2,

    # User agent for RSS requests
    "user_agent": "Audifyy News Aggregator 1.0 (https://audifyy.com)",

    # Minimum title length (filter out low-quality articles)
    "min_title_length": 10,

    # Maximum title length (truncate overly long titles)
    "max_title_length": 200,

    # Keywords to filter out (avoid spam/low-quality content)
    "filter_keywords": [
        "sponsored", "advertisement", "ad:", "promoted",
        "unsubscribe", "newsletter", "signup"
    ],

    # Duplicate detection settings
    "similarity_threshold": 0.85,  # Cosine similarity threshold for duplicate detection

    # Priority weights (higher priority feeds get more weight in selection)
    "priority_weights": {
        1: 1.0,    # Highest priority
        2: 0.8,    # Medium priority
        3: 0.6     # Lower priority
    }
}

def get_feeds_by_category(category: str) -> list:
    """
    Get RSS feeds for a specific category

    Args:
        category: Category name (general-tech, ai-ml, devops-platform)

    Returns:
        List of feed configurations for the category
    """
    return RSS_FEEDS.get(category, [])

def get_all_feeds() -> dict:
    """
    Get all RSS feeds organized by category

    Returns:
        Dictionary of all RSS feeds
    """
    return RSS_FEEDS

def get_high_priority_feeds(category: str) -> list:
    """
    Get only high priority feeds for a category (priority 1 and 2)
    Useful for cost optimization when token limits are tight

    Args:
        category: Category name

    Returns:
        List of high priority feed configurations
    """
    feeds = get_feeds_by_category(category)
    return [feed for feed in feeds if feed.get("priority", 3) <= 2]