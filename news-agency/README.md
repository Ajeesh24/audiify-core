# 📰 Audifyy News Agency

**Automated Daily Tech News Briefing System**

The News Agency is a sophisticated 5-engine pipeline that automatically generates three daily tech audio briefs:
- 🌐 **General Tech** - Consumer tech, business, startups (7-10 min)
- 🤖 **AI/ML** - Research, model releases, applications (7-10 min)
- 💻 **DevOps/Platform** - Cloud, infrastructure, dev tools (7-10 min)

## 🏗️ Architecture

### 5-Engine Pipeline
```text
RSS Engine → Categorization Engine → Ranking Engine → Brief Engine → Audio Engine
```

### Daily Schedule (UTC)
- **05:00** - Engine 1: RSS Collection
- **05:15** - Engine 2: Categorization
- **05:25** - Engine 3: Ranking
- **05:35** - Engine 4: Brief Generation
- **06:00** - Engine 5: Audio Generation
- **06:30** - Pipeline Complete ✅

## 📁 Structure

```
news-agency/
├── engines/           # 5 core processing engines
│   ├── rss_engine.py
│   ├── categorization_engine.py
│   ├── ranking_engine.py
│   ├── brief_engine.py
│   └── audio_engine.py
├── models/           # DynamoDB data models
│   ├── article.py
│   ├── brief.py
│   └── job.py
├── services/         # Shared services and utilities
│   ├── database.py
│   ├── storage.py
│   └── orchestrator.py
├── api/             # API endpoints for briefings
│   ├── briefings.py
│   └── internal.py
├── config/          # Configuration and settings
│   ├── settings.py
│   ├── rss_feeds.py
│   └── categories.py
└── utils/           # Helper utilities
    ├── logger.py
    └── metrics.py
```

## 💰 Cost Optimization

- **Target**: <$0.50/day total processing cost
- **Token Efficient**: 10K tokens/day vs 400K (97.5% reduction)
- **Storage Optimized**: Metadata-only approach (1KB vs 10KB per article)

## 🚀 Getting Started

1. **Set up AWS resources** (DynamoDB tables, S3 buckets)
2. **Configure RSS feeds** in `config/rss_feeds.py`
3. **Deploy Lambda functions** for each engine
4. **Set up CloudWatch scheduling** for daily pipeline execution

## 📊 Monitoring

- **Pipeline Status**: Real-time tracking via DynamoDB `briefing_jobs` table
- **Quality Metrics**: Content categorization accuracy, brief duration
- **Cost Tracking**: Daily AWS usage and token consumption