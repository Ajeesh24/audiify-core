# Audifyy MVP - Transform Articles to Audio 🎧

Transform any article into crystal-clear audio with AI-powered summarization. Listen on the go with our modern Progressive Web App.

## ✨ Features

- **Article Extraction**: Smart content extraction from any URL with ad/promotion removal
- **AI Summarization**: LangChain-powered summarization with flexible LLM providers
- **Text-to-Speech**: High-quality audio generation using OpenAI TTS
- **Two Modes**: Full article or AI-generated summary
- **Progressive Web App**: Installable on mobile and desktop
- **Beautiful UI**: Dark theme with smooth animations and modern design
- **Audio Streaming**: In-app audio player with full controls
- **Error Handling**: Comprehensive error handling and user feedback

## 🏗️ Architecture

```
audifyy-mvp/
├── backend/           # FastAPI Python backend
│   ├── app/
│   │   ├── services/  # Article extraction, LLM, TTS services
│   │   ├── api/       # REST API endpoints
│   │   ├── models/    # Pydantic data models
│   │   └── core/      # Configuration and utilities
│   └── requirements.txt
└── frontend/          # React PWA frontend
    ├── src/
    │   ├── components/ # UI components
    │   ├── services/   # API client
    │   └── lib/        # Utilities
    ├── public/         # PWA assets
    └── package.json
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- OpenAI API key

### Backend Setup

1. **Navigate to backend directory**
```bash
cd audifyy-mvp/backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Install Playwright browsers**
```bash
playwright install chromium
```

5. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

6. **Run the backend**
```bash
python -m app.main
# or
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

### Frontend Setup

1. **Navigate to frontend directory**
```bash
cd audifyy-mvp/frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Run development server**
```bash
npm run dev
```

The app will be available at http://localhost:5173

### Production Build

**Backend:**
```bash
# Install production server
pip install gunicorn

# Run with gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Frontend:**
```bash
npm run build
npm run preview
```

## 🔧 Configuration

### Backend Environment Variables

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional
DEBUG=true
HOST=0.0.0.0
PORT=8000
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=3600
MAX_ARTICLE_LENGTH=50000
```

### Frontend Environment Variables

```env
# Optional - defaults to localhost:8000/api
VITE_API_URL=http://localhost:8000/api
```

## 📱 PWA Installation

### Mobile (iOS/Android)
1. Open the app in your mobile browser
2. Tap the share button (iOS) or menu (Android)
3. Select "Add to Home Screen"
4. The app will install like a native app

### Desktop (Chrome/Edge)
1. Visit the app in your browser
2. Look for the install icon in the address bar
3. Click "Install" to add to your desktop

## 🎯 API Endpoints

### Main Endpoints

- `POST /api/process-article` - Process article URL and generate audio
- `GET /api/audio/{audio_id}` - Stream generated audio file
- `POST /api/validate-url` - Validate article URL
- `GET /api/voices` - Get available TTS voices
- `GET /api/health` - Health check

### Example Usage

```javascript
// Process an article
const response = await fetch('/api/process-article', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    url: 'https://example.com/article',
    mode: 'summary'  // or 'full'
  })
});

const result = await response.json();
if (result.success) {
  // Play audio using result.audio.audio_id
  const audioUrl = `/api/audio/${result.audio.audio_id}`;
}
```

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern, fast API framework
- **LangChain** - LLM abstraction for flexibility
- **newspaper3k** - Article content extraction
- **Playwright** - Web scraping with JavaScript support
- **OpenAI SDK** - GPT summarization and TTS
- **Pydantic** - Data validation and serialization

### Frontend
- **React 18** - Modern React with hooks
- **TypeScript** - Type safety and better DX
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Smooth animations
- **Radix UI** - Accessible UI primitives
- **PWA** - Service worker and manifest

## 🔒 Security Features

- Rate limiting (10 requests/hour per IP)
- URL validation and SSRF prevention
- CORS protection
- Input sanitization
- Error message sanitization
- Trusted host middleware

## 🎨 Design System

The UI follows a modern dark theme with:

- **Purple/Violet gradients** for primary actions
- **Slate colors** for backgrounds and borders
- **Glass morphism** effects with backdrop blur
- **Smooth animations** with Framer Motion
- **Responsive design** for all screen sizes
- **Accessible** components with proper focus states

## 🚨 Error Handling

The app handles various error scenarios:

- **Invalid URLs** - User-friendly validation messages
- **Paywalled content** - Clear indication when content is behind paywall
- **Rate limiting** - Graceful handling with retry suggestions
- **Network timeouts** - Helpful messages for long processing times
- **Server errors** - Generic error messages without exposing internals

## 📈 Future Enhancements

### Phase 2: User Accounts
- User registration and authentication
- Article history and favorites
- Personal voice preferences
- Usage analytics

### Phase 3: Advanced Features
- Multiple TTS providers (ElevenLabs)
- Offline mode with downloads
- Batch article processing
- Social sharing
- Custom voice training

### Phase 4: Premium Features
- Priority processing queue
- Advanced summarization options
- Analytics dashboard
- API access for developers

## 🔍 Troubleshooting

### Common Issues

**Backend won't start:**
- Check Python version (3.9+ required)
- Verify OpenAI API key is set
- Install Playwright browsers: `playwright install chromium`

**Frontend won't build:**
- Check Node.js version (18+ required)
- Clear node_modules: `rm -rf node_modules && npm install`

**Audio not playing:**
- Check browser console for CORS errors
- Verify backend is running on correct port
- Test API endpoint directly: `curl http://localhost:8000/api/health`

**Articles not extracting:**
- Some sites block automated access
- Try different article URLs
- Check backend logs for specific errors

### Performance Tips

- Use summary mode for faster processing
- Shorter articles process quicker
- Rate limiting resets every hour
- Backend caches processed articles temporarily

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

For support, please open an issue on GitHub or contact the development team.

---

**Built with ❤️ using Python, React, and AI**