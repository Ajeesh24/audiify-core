# AUDIFYY FRONTEND UI/UX SPECIFICATIONS

## 🎯 1. EXECUTIVE SUMMARY

### Product Vision
**Spotify-like Audio Platform for Tech News**
A modern, mobile-first web application that combines daily tech briefings with personal article-to-audio conversion. Built with a "browse-first, authenticate-on-play" model to maximize user engagement and conversion.

### Core User Experience Principles
- **Browse Freely:** All content visible without authentication
- **Authenticate to Consume:** Sign-in required only when users want to play/convert
- **Mobile-First:** Optimized for mobile consumption with progressive enhancement
- **Audio-Centric:** Every interaction optimized for audio content
- **Spotify-Inspired:** Familiar patterns from music streaming platforms

---

## 🔐 2. AUTHENTICATION STRATEGY

### Browse-First Authentication Model

```typescript
interface AuthenticationStrategy {
  guestAccess: {
    canBrowse: true;           // View all pages and content
    canSeeDescriptions: true;   // Read full article summaries
    canPreview: true;          // See story lists and details
    canPlay: false;            // Triggers authentication modal
    canConvert: false;         // Triggers authentication modal
    canSave: false;            // Triggers authentication modal
  };

  authenticatedAccess: {
    canBrowse: true;
    canSeeDescriptions: true;
    canPreview: true;
    canPlay: true;             // Full audio playback
    canConvert: true;          // Personal article conversion
    canSave: true;             // Personal library management
    canSync: true;             // Cross-device synchronization
  };
}
```

### Authentication Triggers
```typescript
type AuthTrigger =
  | { type: 'play_brief'; briefId: string; category: string }
  | { type: 'play_personal'; audioId: string; title: string }
  | { type: 'convert_article'; url?: string }
  | { type: 'save_favorite'; contentId: string }
  | { type: 'access_library' }
  | { type: 'download_offline'; audioId: string };

interface AuthModal {
  trigger: AuthTrigger;
  contextualMessage: string;
  primaryCTA: string;
  valueProps: string[];
  onSuccess: (action: PendingAction) => void;
}
```

---

## 🏗️ 3. APPLICATION ARCHITECTURE

### Overall Layout Structure

```text
┌─────────────────────────────────────────────────────────────┐
│  Header: Logo, Search, Auth/Profile, Settings              │
├─────────────────────────────────────────────────────────────┤
│  Navigation: Home, Briefings, Convert, Library              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    Main Content Area                        │
│                   (Route-Specific)                          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Audio Player: Sticky bottom bar when content playing      │
└─────────────────────────────────────────────────────────────┘
```

### Route Structure
```typescript
const routes = {
  '/': 'Homepage - Daily briefings + Featured audio + Trending content (AUDIO-FOCUSED)',
  '/briefings': 'All briefings overview',
  '/briefings/general': 'General tech category page',
  '/briefings/aiml': 'AI/ML category page',
  '/briefings/devops': 'DevOps category page',
  '/convert': 'Article-to-audio converter (DEDICATED TTS SERVICE)', // 🆕 MAIN TTS TAB
  '/library': 'Personal audio library (auth required)',
  '/settings': 'User preferences (auth required)',
  '/auth': 'Authentication page'
};
```

### Component Hierarchy
```text
App
├── AuthProvider (Context)
├── AudioProvider (Context)
├── Header
│   ├── Logo
│   ├── SearchBar
│   ├── AuthButtons (Guest) / UserMenu (Authenticated)
│   └── SettingsIcon
├── Navigation
│   ├── NavTabs (Desktop)
│   └── BottomNav (Mobile)
├── Router
│   ├── HomePage (AUDIO-FOCUSED)
│   │   ├── DailyBriefs
│   │   │   └── BriefCard[]
│   │   ├── FeaturedContent
│   │   ├── TrendingTopics
│   │   └── ConvertCTA (Link to Convert tab)
│   ├── ConvertPage (DEDICATED TTS SERVICE)
│   │   ├── ArticleConverter
│   │   ├── ProcessingStatus
│   │   ├── RecentConversions
│   │   └── HowItWorks
│   ├── BriefingPages
│   │   ├── CategoryHeader
│   │   ├── AudioPlayer
│   │   ├── StoryList
│   │   └── HistorySection
│   └── LibraryPage (Protected)
│       ├── LibraryStats
│       ├── AudioList
│       └── OrganizationTools
├── AudioPlayer (Sticky)
└── AuthModal (Conditional)
    ├── SignInForm
    ├── SignUpForm
    └── SocialAuth
```

---

## 🎨 4. DESIGN SYSTEM

### Color Palette
```css
:root {
  /* Brand Colors */
  --primary: #8B5FBF;           /* Purple - main brand */
  --primary-light: #A078D4;     /* Light purple */
  --primary-dark: #6B46A3;      /* Dark purple */

  /* Backgrounds */
  --bg-primary: #0F0F0F;        /* Almost black */
  --bg-secondary: #1A1A1A;      /* Dark gray */
  --bg-tertiary: #2A2A2A;       /* Medium gray */
  --bg-card: #1E1E1E;           /* Card background */
  --bg-modal: rgba(0,0,0,0.8);  /* Modal overlay */

  /* Text Colors */
  --text-primary: #FFFFFF;       /* Pure white */
  --text-secondary: #B3B3B3;     /* Light gray */
  --text-muted: #6B6B6B;        /* Muted gray */
  --text-accent: #1DB954;       /* Success green */

  /* Status Colors */
  --success: #1DB954;           /* Spotify green */
  --warning: #FFA500;           /* Orange */
  --error: #E22134;             /* Red */
  --info: #1E90FF;              /* Blue */

  /* Category Colors */
  --general: #4A90E2;           /* Blue */
  --aiml: #F39C12;              /* Orange */
  --devops: #27AE60;            /* Green */

  /* Interactive States */
  --hover: rgba(255,255,255,0.1);
  --active: rgba(255,255,255,0.2);
  --focus: #8B5FBF;
  --disabled: #404040;
}
```

### Typography Scale
```css
/* Font Families */
--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;

/* Font Sizes */
--text-xs: 0.75rem;     /* 12px - captions, timestamps */
--text-sm: 0.875rem;    /* 14px - secondary text */
--text-base: 1rem;      /* 16px - body text */
--text-lg: 1.125rem;    /* 18px - large body */
--text-xl: 1.25rem;     /* 20px - small headings */
--text-2xl: 1.5rem;     /* 24px - section headings */
--text-3xl: 1.875rem;   /* 30px - page headings */
--text-4xl: 2.25rem;    /* 36px - hero text */

/* Font Weights */
--font-light: 300;
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
--font-black: 900;

/* Line Heights */
--leading-tight: 1.25;
--leading-normal: 1.5;
--leading-relaxed: 1.75;
```

### Spacing System
```css
/* Spacing Scale (4px base) */
--space-1: 0.25rem;    /* 4px */
--space-2: 0.5rem;     /* 8px */
--space-3: 0.75rem;    /* 12px */
--space-4: 1rem;       /* 16px */
--space-5: 1.25rem;    /* 20px */
--space-6: 1.5rem;     /* 24px */
--space-8: 2rem;       /* 32px */
--space-10: 2.5rem;    /* 40px */
--space-12: 3rem;      /* 48px */
--space-16: 4rem;      /* 64px */
--space-20: 5rem;      /* 80px */

/* Component Spacing */
--padding-sm: var(--space-3);
--padding-md: var(--space-4);
--padding-lg: var(--space-6);
--padding-xl: var(--space-8);

--margin-sm: var(--space-2);
--margin-md: var(--space-4);
--margin-lg: var(--space-6);
--margin-xl: var(--space-8);
```

### Border Radius & Shadows
```css
/* Border Radius */
--radius-xs: 0.125rem;   /* 2px */
--radius-sm: 0.25rem;    /* 4px */
--radius-md: 0.375rem;   /* 6px */
--radius-lg: 0.5rem;     /* 8px */
--radius-xl: 0.75rem;    /* 12px */
--radius-2xl: 1rem;      /* 16px */
--radius-full: 9999px;   /* Fully rounded */

/* Box Shadows */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.1);
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06);
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05);
--shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.1), 0 10px 10px rgba(0, 0, 0, 0.04);
--shadow-glow: 0 0 20px rgba(139, 95, 191, 0.3);

/* Elevations for Audio Context */
--elevation-player: var(--shadow-xl);
--elevation-modal: var(--shadow-2xl);
--elevation-card: var(--shadow-md);
```

---

## 📱 5. RESPONSIVE BREAKPOINTS

### Breakpoint System
```css
/* Mobile First Approach */
--breakpoint-xs: 320px;   /* Small phones */
--breakpoint-sm: 640px;   /* Large phones */
--breakpoint-md: 768px;   /* Tablets */
--breakpoint-lg: 1024px;  /* Small desktop */
--breakpoint-xl: 1280px;  /* Large desktop */
--breakpoint-2xl: 1536px; /* Extra large */

/* Media Query Mixins */
@media (min-width: 640px) { /* sm+ */ }
@media (min-width: 768px) { /* md+ */ }
@media (min-width: 1024px) { /* lg+ */ }
```

### Layout Adaptations
```typescript
interface ResponsiveLayout {
  mobile: {
    navigation: 'bottom-tabs',
    briefCards: 'stacked-full-width',
    audioPlayer: 'compact-bottom',
    converter: 'simplified-form'
  };
  tablet: {
    navigation: 'top-tabs',
    briefCards: 'two-column-grid',
    audioPlayer: 'expanded-bottom',
    converter: 'full-featured-form'
  };
  desktop: {
    navigation: 'top-tabs-with-sidebar',
    briefCards: 'three-column-grid',
    audioPlayer: 'side-panel-option',
    converter: 'advanced-settings'
  };
}
```

---

## 🏠 6. PAGE SPECIFICATIONS

### 6.1 Homepage Layout

#### Desktop Homepage (NEW AUDIO-FOCUSED DESIGN)
```text
┌───────────────────────────────────────────────────────────────┐
│  🎧 Audifyy                   🔍         [Sign In] [Sign Up]  │ ← Header (h-16)
├───────────────────────────────────────────────────────────────┤
│ 🏠 Home    📻 Briefings    🔄 Convert    📚 Library           │ ← Navigation (h-12) ✨ UPDATED
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Hero Section: Welcome + Value Prop             (py-12)       │
│  🎧 TODAY'S DAILY BRIEFINGS - January 10, 2025               │
│                                                               │
│  Brief Cards Grid (3-column)                   (py-8)        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│  │ 🌐 General Tech │ │ 🤖 AI/ML        │ │ 💻 DevOps       │ │
│  │ BriefCard       │ │ BriefCard       │ │ BriefCard       │ │
│  │ Component       │ │ Component       │ │ Component       │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│                                                               │
│  ⭐ FEATURED AUDIO CONTENT                    (py-12) ✨ NEW  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  🎵 "OpenAI's GPT-4.5 Deep Dive"          [🔒 Play]     │ │
│  │      Featured • AI/ML Brief • 15:32 • ⭐⭐⭐⭐⭐          │ │
│  │                                                         │ │
│  │  🎵 "2025 Startup Funding Trends"         [🔒 Play]     │ │
│  │      Trending • General Tech • 12:45 • ⭐⭐⭐⭐         │ │
│  │                                                         │ │
│  │  🎵 "Kubernetes Security Best Practices"  [🔒 Play]     │ │
│  │      Popular • DevOps • 18:20 • ⭐⭐⭐⭐⭐             │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  📈 TRENDING TOPICS                           (py-8) ✨ NEW  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  #1  "AI Regulation Updates"        🔥 Trending         │ │
│  │  #2  "Apple M4 Performance"         📈 Rising           │ │
│  │  #3  "Cloud Security Breaches"      ⚡ Breaking         │ │
│  │  #4  "React 19 Release"             🆕 New              │ │
│  │  #5  "Startup Acquisitions"         💰 Hot              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  🔄 CONVERT ARTICLES TO AUDIO             (py-8) ✨ NEW CTA  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  👋 Turn any article into professional audio narration  │ │
│  │                                                         │ │
│  │      [Try Converting Your First Article →]              │ │ ← Links to /convert
│  │                                                         │ │
│  │  ✓ Professional narration  ✓ Multiple voices           │ │
│  │  ✓ Adjustable speed       ✓ Offline downloads         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

#### Mobile Homepage (NEW AUDIO-FOCUSED DESIGN)
```text
┌─────────────────────────────┐
│ ☰ Audifyy      [Sign In]    │ ← Compact header
├─────────────────────────────┤
│                             │
│ Welcome Section  (py-6)     │
│ 🎧 Daily Briefs - Jan 10    │
│                             │
│ Brief Cards (stacked)       │
│ ┌─────────────────────────┐ │
│ │ 🌐 General Tech         │ │
│ │ Mobile BriefCard        │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ 🤖 AI/ML                │ │
│ │ Mobile BriefCard        │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ 💻 DevOps               │ │
│ │ Mobile BriefCard        │ │
│ └─────────────────────────┘ │
│                             │
│ ⭐ Featured Audio  ✨ NEW    │
│ • GPT-4.5 Deep Dive [Play] │
│ • Startup Trends   [Play]  │
│ • K8s Security     [Play]  │
│                             │
│ 📈 Trending        ✨ NEW   │
│ 🔥 AI Regulation Updates    │
│ 📈 Apple M4 Performance     │
│ ⚡ Cloud Security Breaches  │
│                             │
│ 🆕 New to Audifyy? ✨ NEW   │
│ [Try Article Converter →]  │ ← Links to /convert
│                             │
├─────────────────────────────┤
│ 🏠 📻 🔄 📚       ✨ UPDATED│ ← Bottom nav with Convert tab
└─────────────────────────────┘
```

### 6.2 Brief Category Pages

#### Category Page Structure
```typescript
interface BriefCategoryPage {
  header: {
    breadcrumbs: string[];
    categoryIcon: string;
    categoryName: string;
    description: string;
  };

  currentBrief: {
    audioPlayer: AudioPlayerComponent;
    storyList: StoryListComponent;
    briefSettings: SettingsComponent;
  };

  history: {
    recentBriefs: BriefHistoryComponent;
    pagination: PaginationComponent;
  };

  sidebar?: {
    relatedCategories: CategoryLinksComponent;
    personalRecommendations: RecommendationsComponent;
  };
}
```

### 6.3 Authentication Modal

#### Modal Specifications
```typescript
interface AuthModalProps {
  isOpen: boolean;
  trigger: AuthTrigger;
  onClose: () => void;
  onSuccess: (user: User) => void;
}

interface AuthModalContent {
  contextualHeader: string;
  valueProposition: string[];
  primaryCTA: string;
  socialOptions: ('google' | 'github' | 'apple')[];
  alternativeActions: {
    label: string;
    action: () => void;
  }[];
}

// Example contextual content:
const authContent = {
  play_brief: {
    contextualHeader: "Sign in to listen to daily tech briefings",
    valueProposition: [
      "Access all daily briefings instantly",
      "High-quality audio narration",
      "Sync progress across devices",
      "Download for offline listening"
    ],
    primaryCTA: "Sign In & Start Listening"
  },
  convert_article: {
    contextualHeader: "Sign in to convert articles to audio",
    valueProposition: [
      "Convert unlimited articles",
      "Choose from 6 professional voices",
      "Build your personal audio library",
      "Advanced playback controls"
    ],
    primaryCTA: "Create Account & Convert"
  }
};
```

### 6.4 Convert Page (NEW DEDICATED TTS SERVICE)

#### Desktop Convert Page Layout
```text
┌───────────────────────────────────────────────────────────────┐
│  🎧 Audifyy                   🔍         [Sign In] [Sign Up]  │
├───────────────────────────────────────────────────────────────┤
│ 🏠 Home    📻 Briefings    🔄 Convert    📚 Library           │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  🔄 ARTICLE TO AUDIO CONVERTER                                │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │  📰 PASTE ARTICLE URL                                   │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │ https://techcrunch.com/2025/01/10/ai-breakthrough   │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                                                         │ │
│  │  ⚙️ CONVERSION SETTINGS                                 │ │
│  │                                                         │ │
│  │  📄 Mode: ● Full Article    ○ Summary Only             │ │
│  │  🎤 Voice: [Alloy ▼] Natural, Professional [🔊 Preview]│ │
│  │  ⚡ Speed: [1.0x ▼] 0.5x - 2.0x                        │ │
│  │  📱 Format: [MP3 ▼] High Quality [Advanced Settings ▼] │ │
│  │                                                         │ │
│  │  📊 ESTIMATION                                          │ │
│  │  Duration: ~8 minutes • Cost: $0.12 • Size: ~8MB      │ │
│  │                                                         │ │
│  │            [🚀 Generate Audio] or [🔒 Sign In First]    │ │
│  │                                                         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  💡 HOW IT WORKS                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  1️⃣ Paste any article URL (news, blog, research paper) │ │
│  │  2️⃣ Choose your preferred voice and settings           │ │
│  │  3️⃣ We extract and convert to professional audio      │ │
│  │  4️⃣ Listen instantly or download for offline          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  📚 RECENT CONVERSIONS (if authenticated)                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  🎵 "Kubernetes Scaling Guide"         [▶️] [📱] [⭐]   │ │
│  │      TechCrunch • Yesterday • 12:34 • Full Article      │ │
│  │                                                         │ │
│  │  🎵 "AI Healthcare Applications"       [▶️] [📱] [⭐]   │ │
│  │      Nature • 2 days ago • 8:12 • Summary [View All →] │ │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

#### Mobile Convert Page Layout
```text
┌─────────────────────────────┐
│ ☰ 🔄 Convert    [Sign In]   │
├─────────────────────────────┤
│                             │
│ 📰 Article URL              │
│ ┌─────────────────────────┐ │
│ │ Paste URL here...       │ │
│ └─────────────────────────┘ │
│                             │
│ ⚙️ Settings                 │
│ Mode: ● Full  ○ Summary     │
│ Voice: [Alloy ▼] [🔊]       │
│ Speed: [1.0x ▼]             │
│                             │
│ 📊 ~8 min • $0.12 • 8MB     │
│                             │
│ [🚀 Generate Audio]         │
│                             │
│ 💡 How It Works             │
│ 1️⃣ Paste article URL       │
│ 2️⃣ Choose settings         │
│ 3️⃣ AI converts to audio    │
│ 4️⃣ Listen & download       │
│                             │
│ 📚 Recent (if signed in)    │
│ • K8s Scaling   [▶️] [⭐]    │
│ • AI Healthcare [▶️] [⭐]    │
│                             │
├─────────────────────────────┤
│ 🏠 📻 🔄 📚             │
└─────────────────────────────┘
```

---

## 🎵 7. AUDIO PLAYER SPECIFICATIONS

### 7.1 Sticky Bottom Player

#### Component Structure
```typescript
interface StickyAudioPlayer {
  isVisible: boolean;
  currentTrack: {
    id: string;
    title: string;
    subtitle: string;
    coverArt?: string;
    duration: number;
    category?: 'general' | 'aiml' | 'devops' | 'personal';
  };

  playbackState: {
    isPlaying: boolean;
    currentTime: number;
    volume: number;
    speed: number;
    isLoading: boolean;
  };

  controls: {
    onPlay: () => void;
    onPause: () => void;
    onSeek: (time: number) => void;
    onNext?: () => void;
    onPrevious?: () => void;
    onSpeedChange: (speed: number) => void;
    onVolumeChange: (volume: number) => void;
  };

  interactions: {
    onExpand: () => void;
    onFavorite: () => void;
    onShare: () => void;
    onDownload?: () => void;
  };
}
```

#### Visual States
```css
/* Collapsed State (Mobile) */
.audio-player-collapsed {
  height: 64px;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* Expanded State (Desktop) */
.audio-player-expanded {
  height: 80px;
  padding: 12px 24px;
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: 16px;
}

/* Full Screen Modal (Mobile) */
.audio-player-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: var(--bg-primary);
  padding: 24px;
  display: flex;
  flex-direction: column;
}
```

### 7.2 Enhanced Audio Player (Modal)

#### Features & Layout
```text
┌─────────────────────────────────────────┐
│                    ✕                    │ ← Close button
│                                         │
│          ┌─────────────────────┐        │
│          │                     │        │ ← Large cover art
│          │    Category Icon    │        │   (180x180 desktop)
│          │   or Album Art      │        │   (120x120 mobile)
│          └─────────────────────┘        │
│                                         │
│            Track Title                  │ ← Primary text
│           Track Subtitle                │ ← Secondary text
│                                         │
│         ████████████████████            │ ← Progress bar
│              2:15 / 8:30                │ ← Time display
│                                         │
│        ⏮️     ⏸️/▶️     ⏭️              │ ← Primary controls
│                                         │
│   🔄 🔀 🔊 ═══○═══ ⏱️ 1.0x 📱         │ ← Secondary controls
│                                         │
│        ⭐ Favorite    📤 Share          │ ← Action buttons
│                                         │
│   📋 UP NEXT / QUEUE (if applicable)    │ ← Queue section
│   • Next story title                    │
│   • Following story title               │
│                                         │
└─────────────────────────────────────────┘
```

---

## 🎛️ 8. COMPONENT LIBRARY

### 8.1 BriefCard Component

#### Props Interface
```typescript
interface BriefCardProps {
  brief: {
    id: string;
    category: 'general' | 'aiml' | 'devops';
    title: string;
    date: string;
    duration: number;        // seconds
    storyCount: number;
    stories: Story[];
    status: 'ready' | 'processing' | 'error';
    coverArt?: string;
  };

  user: {
    isAuthenticated: boolean;
    canPlay: boolean;
  };

  interactions: {
    onPlay: (briefId: string) => void;
    onPreview: (briefId: string) => void;
    onAuthRequired: (trigger: AuthTrigger) => void;
  };

  variant?: 'default' | 'compact' | 'featured';
  className?: string;
}

interface Story {
  id: string;
  title: string;
  summary: string;
  source: string;
  url: string;
  duration: number;        // seconds
  timestamp?: string;      // when in the brief this story appears
}
```

#### Visual Variants
```css
/* Default Card (Desktop 3-column) */
.brief-card-default {
  width: 100%;
  max-width: 320px;
  min-height: 280px;
  padding: 24px;
  border-radius: var(--radius-xl);
  background: var(--bg-card);
  border: 1px solid rgba(255,255,255,0.1);
}

/* Compact Card (Mobile/List view) */
.brief-card-compact {
  width: 100%;
  padding: 16px;
  border-radius: var(--radius-lg);
  background: var(--bg-card);
}

/* Featured Card (Hero/Spotlight) */
.brief-card-featured {
  width: 100%;
  min-height: 200px;
  padding: 32px;
  border-radius: var(--radius-2xl);
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
}
```

### 8.2 AuthModal Component

#### Modal Structure
```typescript
interface AuthModalComponent {
  props: AuthModalProps;

  layout: {
    backdrop: ModalBackdrop;
    container: ModalContainer;
    content: {
      header: ModalHeader;
      body: AuthForm;
      footer: ModalFooter;
    };
  };

  forms: {
    signIn: SignInForm;
    signUp: SignUpForm;
    forgotPassword: ForgotPasswordForm;
  };

  socialAuth: {
    providers: SocialProvider[];
    onSocialLogin: (provider: string) => void;
  };
}

// Auth form validation
interface AuthFormValidation {
  email: {
    required: true;
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    message: "Please enter a valid email address";
  };

  password: {
    required: true;
    minLength: 8;
    pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/;
    message: "Password must be 8+ characters with uppercase, lowercase, and number";
  };
}
```

### 8.3 ArticleConverter Component

#### Component Structure
```typescript
interface ArticleConverterProps {
  user: {
    isAuthenticated: boolean;
    canConvert: boolean;
  };

  config: {
    url: string;
    mode: 'full' | 'summary';
    voice: VoiceOption;
    speed: number;
    format: 'mp3' | 'm4a';
  };

  processing: {
    isProcessing: boolean;
    progress?: ProcessingProgress;
    estimatedCost?: number;
    estimatedDuration?: number;
  };

  onSubmit: (config: ConversionConfig) => void;
  onAuthRequired: () => void;
}

interface ProcessingProgress {
  step: 'validating' | 'extracting' | 'processing' | 'generating' | 'complete';
  percentage: number;
  message: string;
  estimatedTimeRemaining?: number;
}

interface VoiceOption {
  id: string;
  name: string;
  description: string;
  gender: 'male' | 'female' | 'neutral';
  accent?: string;
  sampleUrl?: string;
}
```

---

## 📱 9. MOBILE-SPECIFIC PATTERNS

### 9.1 Mobile Navigation

#### Bottom Tab Navigation
```typescript
interface BottomNavigation {
  tabs: [
    {
      id: 'home',
      label: 'Home',
      icon: 'home-outline',
      activeIcon: 'home-filled',
      badge?: number;
    },
    {
      id: 'briefings',
      label: 'Briefings',
      icon: 'radio-outline',
      activeIcon: 'radio-filled',
      submenu: CategorySubmenu;
    },
    {
      id: 'library',
      label: 'Library',
      icon: 'library-outline',
      activeIcon: 'library-filled',
      authRequired: true;
    },
    {
      id: 'profile',
      label: 'Profile',
      icon: 'person-outline',
      activeIcon: 'person-filled',
    }
  ];
}
```

#### Mobile Header Patterns
```css
/* Collapsed Header (scroll up) */
.header-collapsed {
  transform: translateY(-100%);
  transition: transform 0.3s ease;
}

/* Expanded Header (scroll down / top) */
.header-expanded {
  transform: translateY(0);
  backdrop-filter: blur(10px);
  background: rgba(15, 15, 15, 0.9);
}

/* Search Active State */
.header-search-active {
  .logo, .nav-items { opacity: 0; }
  .search-bar { width: 100%; }
}
```

### 9.2 Touch Interactions

#### Gesture Support
```typescript
interface TouchGestures {
  audioPlayer: {
    swipeUp: 'expand-to-fullscreen',
    swipeDown: 'collapse-to-mini',
    swipeLeft: 'next-track',
    swipeRight: 'previous-track',
    doubleTap: 'play-pause',
    longPress: 'show-context-menu'
  };

  briefCards: {
    tap: 'show-preview-or-auth',
    longPress: 'show-quick-actions',
    swipeRight: 'add-to-favorites'
  };

  audioProgress: {
    tap: 'seek-to-position',
    drag: 'scrub-timeline'
  };
}
```

#### Safe Area Handling
```css
/* iOS Safe Area Support */
.safe-area-top {
  padding-top: env(safe-area-inset-top);
}

.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
}

/* Android Navigation Bar */
@supports (padding: max(0px)) {
  .safe-area-bottom {
    padding-bottom: max(16px, env(safe-area-inset-bottom));
  }
}
```

---

## 🔄 10. STATE MANAGEMENT

### 10.1 Global State Architecture

#### State Structure
```typescript
interface AppState {
  auth: {
    isAuthenticated: boolean;
    user: User | null;
    loading: boolean;
    error: string | null;
  };

  audio: {
    currentTrack: Track | null;
    isPlaying: boolean;
    currentTime: number;
    duration: number;
    volume: number;
    speed: number;
    queue: Track[];
    isLoading: boolean;
  };

  briefs: {
    daily: {
      [date: string]: {
        general?: Brief;
        aiml?: Brief;
        devops?: Brief;
      };
    };
    loading: boolean;
    error: string | null;
  };

  library: {
    articles: PersonalAudio[];
    favorites: string[];
    recentlyPlayed: string[];
    loading: boolean;
  };

  ui: {
    authModal: {
      isOpen: boolean;
      trigger: AuthTrigger | null;
      pendingAction: PendingAction | null;
    };

    audioPlayer: {
      isExpanded: boolean;
      isFullscreen: boolean;
    };

    navigation: {
      currentRoute: string;
      previousRoute: string;
    };
  };
}
```

### 10.2 Context Providers

#### Auth Context
```typescript
interface AuthContextValue {
  // State
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;

  // Actions
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name: string) => Promise<void>;
  signOut: () => Promise<void>;
  socialSignIn: (provider: string) => Promise<void>;

  // Utils
  requireAuth: (action: () => void, trigger?: AuthTrigger) => void;
  hasPermission: (permission: Permission) => boolean;
}
```

#### Audio Context
```typescript
interface AudioContextValue {
  // State
  currentTrack: Track | null;
  isPlaying: boolean;
  currentTime: number;
  duration: number;

  // Playback Controls
  play: (track?: Track) => void;
  pause: () => void;
  seek: (time: number) => void;
  setSpeed: (speed: number) => void;
  setVolume: (volume: number) => void;

  // Queue Management
  addToQueue: (track: Track) => void;
  removeFromQueue: (trackId: string) => void;
  playNext: () => void;
  playPrevious: () => void;

  // Player UI
  expandPlayer: () => void;
  collapsePlayer: () => void;
  toggleFullscreen: () => void;
}
```

---

## 🎯 11. CONVERSION & ENGAGEMENT STRATEGIES

### 11.1 Guest-to-User Conversion

#### Conversion Triggers
```typescript
interface ConversionStrategy {
  primaryTriggers: [
    {
      trigger: 'play_attempt',
      timing: 'immediate',
      message: 'Sign in to listen to this briefing',
      incentive: 'instant_access',
      cta: 'Sign In & Play Now'
    },
    {
      trigger: 'convert_attempt',
      timing: 'immediate',
      message: 'Create account to convert articles',
      incentive: 'unlimited_conversions',
      cta: 'Start Converting Free'
    },
    {
      trigger: 'third_visit',
      timing: 'delayed_500ms',
      message: 'Join thousands who listen daily',
      incentive: 'social_proof',
      cta: 'Get Your Free Account'
    }
  ];

  secondaryTriggers: [
    {
      trigger: 'scroll_to_library',
      timing: 'on_enter',
      message: 'Save articles to your personal library',
      incentive: 'organization',
      cta: 'Create Library'
    },
    {
      trigger: 'mobile_usage',
      timing: 'session_end',
      message: 'Download our app for offline listening',
      incentive: 'convenience',
      cta: 'Get Mobile App'
    }
  ];
}
```

### 11.2 Engagement Features

#### Progress & Achievement
```typescript
interface EngagementFeatures {
  listeningStreak: {
    currentStreak: number;
    longestStreak: number;
    nextMilestone: number;
    rewards: Achievement[];
  };

  personalStats: {
    totalListeningTime: number;
    articlesConverted: number;
    favoriteCategory: string;
    averageSpeed: number;
  };

  socialFeatures: {
    shareProgress: boolean;
    friendActivity: FriendActivity[];
    groupListening: boolean;
  };
}
```

---

## 🚀 12. IMPLEMENTATION GUIDELINES

### 12.1 Development Priorities

#### Phase 1: Core Browsing (Week 1-2)
```typescript
const phase1Features = [
  'Homepage with brief cards (guest view)',
  'Category pages with story previews',
  'Basic responsive layout',
  'Authentication modal',
  'Simple article converter form'
];
```

#### Phase 2: Audio Integration (Week 3-4)
```typescript
const phase2Features = [
  'Audio player components',
  'Playback controls and state',
  'Brief playback (authenticated)',
  'Progressive audio loading',
  'Mobile audio controls'
];
```

#### Phase 3: Personal Features (Week 5-6)
```typescript
const phase3Features = [
  'Article conversion flow',
  'Personal library interface',
  'User preferences/settings',
  'Offline download support',
  'Advanced audio controls'
];
```

#### Phase 4: Optimization (Week 7-8)
```typescript
const phase4Features = [
  'Performance optimization',
  'Advanced mobile features',
  'PWA capabilities',
  'Analytics integration',
  'A/B testing setup'
];
```

### 12.2 Technical Stack Recommendations

#### Frontend Framework
```typescript
const techStack = {
  framework: 'React 18+ with TypeScript',
  styling: 'Tailwind CSS + CSS-in-JS for dynamic styles',
  stateManagement: 'Zustand or React Context + useReducer',
  routing: 'React Router v6',
  audio: 'Howler.js or native HTML5 Audio API',
  animations: 'Framer Motion',
  forms: 'React Hook Form + Zod validation',
  http: 'Axios with interceptors',
  storage: 'localStorage + IndexedDB for offline',
  pwa: 'Workbox for service workers'
};
```

### 12.3 Performance Requirements

#### Core Web Vitals Targets
```typescript
const performanceTargets = {
  LCP: '<2.5s',      // Largest Contentful Paint
  FID: '<100ms',     // First Input Delay
  CLS: '<0.1',       // Cumulative Layout Shift
  FCP: '<1.8s',      // First Contentful Paint
  TTI: '<3.9s',      // Time to Interactive
};

const audioTargets = {
  initialLoad: '<500ms',     // Time to first audio byte
  seekLatency: '<200ms',     // Seek response time
  bufferHealth: '>30s',      // Buffer ahead time
  networkResilience: '3G+',  // Minimum network support
};
```

---

This comprehensive frontend specification provides a complete blueprint for building the Audifyy platform with a focus on user experience, performance, and conversion optimization. The browse-first approach ensures maximum engagement while the authentication gates provide clear value propositions for sign-up conversion.

**Ready to start implementation?** 🚀