# Halal Cuts

AI-powered video moderation frontend. Upload videos and let AI detect and replace inappropriate scenes seamlessly.

## Features

- 🎬 Drag & drop video upload
- 🔍 AI-powered content detection using OpenAI Vision
- ✨ Automatic scene replacement using fal.ai Veo 3.1
- 📺 Video preview before download
- ⬇️ Direct download from fal.ai CDN

## Getting Started

### Prerequisites

Make sure the backend API is running:

```bash
cd /path/to/ummah
source myenv/bin/activate
python run_api.py
```

### Run the Frontend

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser.

## Tech Stack

- **Next.js 16** - React framework
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **OpenAI Vision** - Content analysis
- **fal.ai Veo 3.1** - Video generation
