# Kitchen Copilot 🍳

An AI-powered cooking assistant that helps you find recipes and manage cooking timers.

## Features

- **Recipe Search**: Find recipes based on ingredients you have
- **Cooking Timers**: Set, start, pause, and stop multiple concurrent timers for different cooking steps
- **AI Chat Interface**: Natural language interaction with Gemini AI

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up API keys:**
   - Get a [Gemini API key](https://ai.google.dev/gemini-api/docs/api-key)
   - Get a [Spoonacular API key](https://spoonacular.com/food-api)
   - Create a `.env` file:
     ```
     GEMINI_API_KEY=your_gemini_api_key_here
     SPOONACULAR_API_KEY=your_spoonacular_api_key_here
     ```

3. **Run the application:**
   ```bash
   python main.py
   ```

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
- **`.env`**: Environment variables for API keys

## API Integrations

- **Google Gemini**: AI chat and tool calling
- **Spoonacular**: Recipe search and ingredient matching

## Requirements

- Python 3.8+
- Valid API keys for Gemini and Spoonacular
- Asyncio support for concurrent timer management
