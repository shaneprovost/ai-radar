"""Default values and constants."""

PROVIDER_DEFAULTS = {
    "anthropic": "anthropic/claude-sonnet-4-6",
    "openai": "openai/gpt-4o",
    "google": "gemini/gemini-2.0-flash",
}

DEFAULT_CRON_SCHEDULE = "0 8 * * 1"  # Monday 8am

DEFAULT_MAX_ITEMS = 10
DEFAULT_MAX_TOKENS = 8000
DEFAULT_MIN_HN_SCORE = 50
DEFAULT_RSS_LOOKBACK_DAYS = 8
DEFAULT_ITEM_CAP = 80  # max items before LLM curation

RSS_SOURCES = {
    "anthropic_blog": "https://www.anthropic.com/news/rss.xml",
    "openai_blog": "https://openai.com/news/rss.xml",
    "deepmind_blog": "https://deepmind.google/discover/blog/rss/",
    "mistral_blog": "https://mistral.ai/news/rss/",
    "tldr_ai": "https://tldr.tech/ai/rss",
    "the_batch": "https://read.deeplearning.ai/the-batch/rss/",
    "import_ai": "https://jack-clark.net/feed/",
    "ai_breakfast": "https://aibreakfast.beehiiv.com/feed",
}

INTEREST_TOPICS = [
    "Claude / Anthropic updates",
    "AI coding assistants",
    "Agent frameworks & orchestration",
    "LLM fine-tuning / training",
    "Open-source models",
    "AI infrastructure / MLOps",
    "RAG / vector databases",
    "Multimodal AI (vision/audio)",
    "AI safety & alignment",
    "Productivity & workflow automation",
    "React / frontend tooling",
    "TypeScript / JavaScript ecosystem",
    "Mobile / React Native",
    "DevOps / platform engineering",
    "Database / data engineering",
]
