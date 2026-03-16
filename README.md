# Kitchen Copilot 🍳

An AI-powered cooking assistant that helps you find recipes and manage cooking timers.

## Features

- **Recipe Search**: Find recipes based on ingredients you have
- **Cooking Timers**: Set, start, pause, and stop multiple concurrent timers for different cooking steps
- **AI Chat Interface**: Natural language interaction with Gemini AI

## 🚀 Setup & Running Locally

Kitchen Copilot is built with a decoupled architecture: a FastAPI backend and a React/Vite frontend. You will need two terminal windows to run the application locally.

### 1. Backend Setup

1. Open your first terminal and navigate to the project root.
2. Install the necessary Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the `backend/` directory (or project root) and add your API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
4. Start the FastAPI WebSocket server:
   ```bash
   python backend/app/main.py
   # Or alternatively: uvicorn backend.app.main:app --reload --port 8000
   ```

### 2. Frontend Setup

1. Open your second terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install the Node.js dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to `http://localhost:5173` (or the port Vite provides). Grant camera and microphone permissions when prompted!


## 🧪 Trying it Out

Curious to see what Kitchen Copilot can do? Once you have the app running, try these things:

1. **Connect**: Click the "Start Cooking" microphone button. Make sure your browser has Camera and Microphone permissions.
2. **Find a Recipe**: Hold up an ingredient to your camera or say, *"I have an onion, garlic, and chicken. What can we make?"*
3. **Hands-Free Navigation**: When the recipe options appear, don't tap the screen! Just say *"I'll take the first one"* to see the app select it and show the steps.
4. **Voice Timers**: Tell the copilot: *"Set a timer for 10 seconds"* and watch the floating widget handle the countdown.
5. **Natural Interruptions**: While it's reading a step, try interrupting it with *"Wait, actually..."* to see how it pauses gracefully.
6. **Finish Up**: Say *"Stop session"* when you're done to safely disconnect.

## Timer Functionality

The Kitchen Copilot supports comprehensive timer management:

### Timer Commands
- **Set a timer**: "Set a timer for boiling pasta for 10 minutes"
- **Start a timer**: "Start the pasta timer"
- **Pause a timer**: "Pause the chicken timer"
- **Stop a timer**: "Stop the baking timer"
- **Check timer status**: "How much time left on the pasta timer?"
- **List all timers**: "What timers do I have running?"

### Multiple Concurrent Timers
You can run multiple timers simultaneously for different cooking steps:
- Boil pasta (10 minutes)
- Bake chicken (25 minutes)
- Chill dessert (60 minutes)

### Timer States
- **Created**: Timer is set but not started
- **Running**: Timer is actively counting down
- **Paused**: Timer is temporarily stopped
- **Completed**: Timer has finished
- **Stopped**: Timer is reset and stopped

## Usage Examples

### Recipe Search
```
You: I have pasta, garlic, eggs, and parmesan. What can I make?
Kitchen Copilot: I found some great recipes for you! Here are the top matches...
```

### Timer Management
```
You: Set a timer for boiling pasta for 10 minutes
Kitchen Copilot: Timer 'Boil pasta' set for 10 minutes. Use start_timer to begin.

You: Start the pasta timer
Kitchen Copilot: Timer 'Boil pasta' is now running for 10 minutes.

You: How much time left on the pasta timer?
Kitchen Copilot: Timer 'Boil pasta' is running with 7 minutes remaining (30.0% complete)

You: What timers do I have?
Kitchen Copilot: You have 1 active timer.
  - Boil pasta: running (7 min left)
```

## Architecture

- **`main.py`**: Main chat interface with Gemini AI integration
- **`tool.py`**: Tool definitions and handlers for recipes and timers
- **`timer.py`**: Timer management system with async support
- **`.env`**: Environment variables for API key and Project configuration
- **Firestore**: NoSQL database for recipe caching and search history

## API Integrations

- **Google Gemini 2.5 Flash Native Audio**: Multimodal Live API for real-time voice, video, and tool calling
- **Google Gemini 2.5 Flash**: Recipe search and step sanitization via text generation
- **Google Cloud Firestore**: Scalable NoSQL database for persistent recipe storage and global search caching

## Requirements

- Python 3.8+
- Valid API key for Gemini
- Asyncio support for concurrent timer management
