"""
Categories Configuration

Defines the categorization system for tech news articles
Used by the categorization engine for LLM-based classification
"""

# Main categories for daily briefings
MAIN_CATEGORIES = {
    "general-tech": {
        "name": "General Tech",
        "description": "Consumer technology, business tech, startups, and general tech news",
        "briefing_duration_target": "7-10 minutes",
        "keywords": [
            "startup", "funding", "IPO", "acquisition", "merger",
            "consumer tech", "gadgets", "smartphone", "laptop",
            "tech industry", "silicon valley", "venture capital",
            "product launch", "earnings", "stock", "business"
        ]
    },
    "ai-ml": {
        "name": "AI/ML",
        "description": "Artificial intelligence, machine learning research, and applications",
        "briefing_duration_target": "7-10 minutes",
        "keywords": [
            "artificial intelligence", "machine learning", "deep learning",
            "neural network", "transformer", "LLM", "GPT", "Claude",
            "computer vision", "natural language processing", "NLP",
            "research", "model", "algorithm", "data science",
            "OpenAI", "Anthropic", "Google AI", "DeepMind"
        ]
    },
    "devops-platform": {
        "name": "DevOps/Platform",
        "description": "Cloud infrastructure, development tools, and platform engineering",
        "briefing_duration_target": "7-10 minutes",
        "keywords": [
            "cloud", "AWS", "Azure", "Google Cloud", "GCP",
            "DevOps", "CI/CD", "containers", "Docker", "Kubernetes",
            "infrastructure", "serverless", "microservices",
            "deployment", "monitoring", "observability",
            "security", "compliance", "automation"
        ]
    }
}

# Sub-categories for more granular classification
SUB_CATEGORIES = {
    "general-tech": [
        "consumer-electronics",
        "mobile-technology",
        "business-software",
        "fintech",
        "e-commerce",
        "social-media",
        "gaming",
        "cybersecurity",
        "startup-news",
        "tech-policy"
    ],
    "ai-ml": [
        "research-papers",
        "model-releases",
        "ai-applications",
        "computer-vision",
        "nlp-language",
        "robotics",
        "autonomous-systems",
        "ai-ethics",
        "ml-tools",
        "ai-hardware"
    ],
    "devops-platform": [
        "cloud-services",
        "container-orchestration",
        "ci-cd-tools",
        "infrastructure-as-code",
        "monitoring-observability",
        "security-tools",
        "database-technology",
        "networking",
        "serverless-computing",
        "platform-engineering"
    ]
}

# Relevance scoring factors
RELEVANCE_FACTORS = {
    # Content quality indicators
    "quality_indicators": {
        "official_announcement": 2.0,   # Official company/org announcements
        "breaking_news": 1.8,          # Breaking news indicators
        "exclusive_interview": 1.6,     # Exclusive content
        "detailed_analysis": 1.4,       # In-depth analysis pieces
        "research_findings": 1.5,       # Research or study results
        "product_launch": 1.3,          # New product/service launches
        "partnership_news": 1.2,        # Business partnerships
        "opinion_piece": 0.8            # Opinion/editorial content
    },

    # Source credibility (multiplier based on feed priority)
    "source_credibility": {
        1: 1.0,     # Highest priority sources
        2: 0.9,     # Medium priority sources
        3: 0.8      # Lower priority sources
    },

    # Recency bonus (articles get higher score if more recent)
    "recency_bonus": {
        "0-2_hours": 1.2,
        "2-6_hours": 1.1,
        "6-12_hours": 1.0,
        "12-24_hours": 0.9
    },

    # Engagement indicators (if available from RSS)
    "engagement_bonus": {
        "high_social_shares": 1.3,
        "many_comments": 1.2,
        "featured_content": 1.1
    }
}

# Classification prompts for LLM
CLASSIFICATION_PROMPTS = {
    "category_classification": """
You are a tech news classifier. Analyze the following article and determine which category it belongs to:

1. **general-tech**: Consumer technology, business tech, startups, tech industry news
2. **ai-ml**: Artificial intelligence, machine learning, AI research, AI applications
3. **devops-platform**: Cloud infrastructure, development tools, DevOps, platform engineering

Article Title: {title}
Article Summary: {summary}
Source: {source}

Respond with just the category name: general-tech, ai-ml, or devops-platform

Category:""",

    "relevance_scoring": """
Rate the relevance and importance of this tech news article on a scale of 1-10, where:
- 10: Major breaking news, significant product launches, important research breakthroughs
- 8-9: Notable announcements, meaningful updates, interesting developments
- 6-7: Regular news, minor updates, niche but relevant content
- 4-5: Less important news, routine updates
- 1-3: Low relevance, promotional content, minor news

Article Title: {title}
Article Summary: {summary}
Category: {category}
Source: {source}

Consider factors like:
- Impact on the tech industry
- Relevance to developers/tech professionals
- Newsworthiness and timeliness
- Quality of the source

Respond with just a number between 1-10:

Score:""",

    "duplicate_detection": """
Compare these two articles and determine if they are about the same story or event:

Article 1:
Title: {title1}
Summary: {summary1}

Article 2:
Title: {title2}
Summary: {summary2}

Respond with "YES" if they are duplicates/same story, "NO" if they are different stories:

Duplicate:"""
}

def get_category_info(category: str) -> dict:
    """Get detailed information about a category"""
    return MAIN_CATEGORIES.get(category, {})

def get_category_keywords(category: str) -> list:
    """Get keywords for a specific category"""
    return MAIN_CATEGORIES.get(category, {}).get("keywords", [])

def get_subcategories(category: str) -> list:
    """Get sub-categories for a main category"""
    return SUB_CATEGORIES.get(category, [])

def get_all_categories() -> list:
    """Get list of all main category names"""
    return list(MAIN_CATEGORIES.keys())

def get_classification_prompt(prompt_type: str, **kwargs) -> str:
    """
    Get a formatted classification prompt

    Args:
        prompt_type: Type of prompt to get
        **kwargs: Variables to format into the prompt

    Returns:
        Formatted prompt string
    """
    template = CLASSIFICATION_PROMPTS.get(prompt_type, "")
    return template.format(**kwargs)