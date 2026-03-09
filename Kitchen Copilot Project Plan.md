# Kitchen Copilot Project Plan

**A real-time, vision-enabled hands-free cooking assistant**
**Category:** Live Agents
**Deadline:** March 16, 2026
**CONFIDENTIAL — TEAM USE ONLY**

---

## 1. Project Overview

### 1.1 The Vision
Kitchen Copilot is a real-time, hands-free cooking assistant built for the **Gemini Live Agent Challenge** (Live Agents category). The user props up their phone in the kitchen, and the agent watches through the camera, listens via microphone, and guides them through cooking — from identifying ingredients on the counter to walking through each recipe step, setting timers, handling mistakes, and suggesting substitutions.

### 1.2 Core User Flow
1.  **Step 1:** User opens the app, grants camera and mic access, and says something like "Hey, I want to make dinner with whatever I’ve got."
2.  **Step 2:** The agent sees the countertop through the camera, identifies ingredients (tomatoes, pasta, garlic, basil), and suggests matching recipes.
3.  **Step 3:** User picks a recipe by voice. The agent walks through it step-by-step, watching progress, adjusting timing, and answering questions hands-free.
4.  **Step 4:** If something goes wrong ("I accidentally added too much salt"), the agent sees or hears the issue and adapts with a fix.

### 1.3 Why This Wins
*   **Breaks the text-box paradigm completely** — primary interaction is voice + vision, not typing.
*   **Demonstrates real-time interruption handling** (a key Live API feature judges will look for).
*   **Naturally multimodal:** the agent must see, hear, and speak simultaneously.
*   **Solves a real problem** — everyone cooks, and hands-free guidance is genuinely useful.
*   **Rich demo potential** — actual cooking on camera is inherently engaging to watch.

### 1.4 Hackathon Requirements Checklist

| Requirement | How We Satisfy It |
| :--- | :--- |
| **Gemini model** | gemini-2.0-flash-live via Live API |
| **Google GenAI SDK or ADK** | ADK for agent definition + tool management |
| **At least one Google Cloud service** | Cloud Run (hosting), Firestore (data), Cloud Storage |
| **Public code repository** | GitHub repo with full README + spin-up instructions |
| **Architecture diagram** | Included in repo and submission (see Section 2) |
| **Proof of Cloud deployment** | Screen recording of Cloud Run console + logs |
| **Demo video (<4 min)** | Real cooking session with live agent interaction |

#### Bonus Points We’re Targeting
*   Blog post covering how we built it with Google AI + Google Cloud
*   Automated Cloud deployment via Dockerfile + cloudbuild.yaml (IaC)
*   GDG profile links for all team members

---

## 2. System Architecture

### 2.1 Architecture Overview
The system is divided into three layers: a lightweight frontend that captures audio/video and plays back responses, a Python backend on Cloud Run that orchestrates sessions and tools, and the Gemini Live API that powers the conversational intelligence.

### 2.2 Component Breakdown

#### Frontend (Client)
A web app (React or Next.js, or a simple PWA) that captures the camera stream and microphone audio and sends them to the backend via WebSocket. It renders voice responses through the speaker and displays minimal visual elements: a camera viewfinder, recipe sidebar, and floating timer widgets. The primary interaction is voice, so the UI stays minimal and out of the way.

#### Backend (Orchestration Layer)
A Python server (FastAPI) running on Google Cloud Run. It receives audio/video streams from the client via WebSocket, manages the Gemini Live API session, handles conversation state (current recipe, current step, identified ingredients), and routes tool calls. This is the brain of the system.

#### Gemini Live API (Agent Core)
A persistent, bidirectional streaming session with Gemini. Audio flows in both directions continuously. Video frames are sent as periodic JPEG snapshots every 2–3 seconds. The API handles voice activity detection and interruptions natively — if the user speaks while the agent is mid-sentence, the API detects this and signals that the response should stop.

#### ADK Agent (Tool Layer)
The Agent Development Kit structures the agent’s capabilities as typed tool functions. When Gemini decides it needs external data (e.g., searching for recipes or setting a timer), it issues a tool call. The backend executes the corresponding Python function, which queries Firestore or manages state, then returns structured results to Gemini, which incorporates them into its voice response.

#### Data Layer (Firestore + Cloud Storage)
Firestore stores recipes (with ingredients, steps, visual cues, common mistakes, and dietary tags) and active session state (current step, identified ingredients, active timers, user preferences). Cloud Storage holds any cached recipe images. Cloud Logging is used for debugging live sessions.

### 2.3 Architecture Diagram

```text
USER’S DEVICE
[Camera] [Microphone] [Speaker/UI]
│ │ ▲
└─────┬─────┘ │
[React/Next.js Frontend (PWA)] ───┘
│ WebSocket (audio + video frames)
▼
GOOGLE CLOUD
[Cloud Run — FastAPI Orchestration Server]
│ │
▼ ▼
[Firestore] [Gemini Live API]
(recipes, (via GenAI SDK / ADK)
sessions,
prefs)
[Cloud Storage] [Cloud Logging]
(recipe images) (debugging)
```

---

## 3. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React / Next.js (PWA) | Camera/mic capture, WebSocket client, minimal UI |
| **Transport** | WebSocket | Bidirectional streaming of audio chunks + video frames |
| **Backend** | Python + FastAPI | Session management, WebSocket server, tool execution |
| **Agent** | Google ADK | Structured agent definition with typed tool functions |
| **AI Model** | Gemini 2.0 Flash (Live) | Real-time multimodal conversation (audio + vision) |
| **Database** | Cloud Firestore | Recipe storage, session state, user preferences |
| **Hosting** | Google Cloud Run | Serverless container hosting for the backend |
| **Storage** | Cloud Storage | Cached recipe images, static assets |
| **CI/CD** | Cloud Build | Automated deployment pipeline (bonus points) |

---

## 4. Data Schema (Firestore)

We use Firestore (NoSQL document store) instead of Cloud SQL for speed of development. No schema migrations, no connection pooling, 3 lines of code to read/write, generous free tier, and more than sufficient for our recipe dataset of 50–100 entries.

### 4.1 Recipes Collection
Each recipe document contains everything the agent needs to guide a cooking session:

| Field | Type | Description |
| :--- | :--- | :--- |
| `name` | string | Recipe title, e.g. "Classic Spaghetti Aglio e Olio" |
| `description` | string | Brief description of the dish |
| `cuisine` | string | Cuisine type (Italian, Mexican, etc.) |
| `difficulty` | string | easy / medium / hard |
| `prep_time_minutes` | integer | Preparation time |
| `cook_time_minutes` | integer | Active cooking time |
| `servings` | integer | Default number of servings |
| `dietary_tags` | array | `["vegetarian", "dairy-free", "nut-free", ...]` |
| `ingredients[]` | array | Each: `{name, quantity, unit, category, essential}` |
| `steps[]` | array | Each: `{order, instruction, duration_minutes, requires_timer, visual_cue}` |
| `tips` | array | Pro tips for the dish |
| `common_mistakes` | array | What to watch out for — feeds into agent’s proactive warnings |

**Key Design Decisions**
*   `visual_cue` on each step lets the agent compare camera frames to expected state ("that looks ready")
*   `common_mistakes` feeds the agent’s proactive awareness — it warns before you make a mistake
*   `category` on ingredients enables smart substitution logic (swap within same category)

### 4.2 Sessions Collection
Stores the live state of each cooking session so the agent can recover from disconnects and track progress:

| Field | Type | Description |
| :--- | :--- | :--- |
| `user_id` | string | Anonymous session identifier |
| `started_at` | timestamp | When the session began |
| `preferences` | map | `{dietary_restrictions, skill_level, language}` |
| `current_recipe_id` | string | Reference to the active recipe document |
| `current_step` | integer | Which step the user is currently on |
| `completed_steps` | array | List of completed step numbers |
| `identified_ingredients` | array | What the camera has identified so far |
| `active_timers` | array | Each: `{name, started_at, duration_seconds}` |

---

## 5. Agent Logic Deep Dive

### 5.1 Gemini Live API Session Lifecycle
The Live API is fundamentally different from the standard chat API. It creates a persistent, bidirectional stream — like a phone call, not a series of HTTP requests.

1.  **Session creation:** When the user opens the app and grants camera/mic, the frontend opens a WebSocket to our FastAPI backend, which then establishes a Live API session with Gemini using the GenAI SDK.
2.  **Audio streaming:** The frontend captures mic audio as raw PCM (16-bit, 16kHz mono) and sends chunks over WebSocket. The backend forwards these to Gemini. Gemini streams audio response chunks back via the same path.
3.  **Video snapshots:** Every 2–3 seconds, the frontend captures a JPEG frame from the camera at 640×480 and sends it as a binary blob. The backend forwards it to Gemini as an image/jpeg media chunk.
4.  **Interruption:** If the user speaks while Gemini is responding, the API detects voice activity and signals the interruption. The frontend stops playing the current audio buffer and prepares for a new response.
5.  **Tool calls:** When Gemini needs data (search recipes, set timer), it emits a `tool_call` event. The backend catches it, executes the corresponding Python function, and sends the result back. Gemini incorporates the data into its next voice response.

### 5.2 Video Frame Pipeline (2–3 Second Snapshots)
We do not stream continuous video — that would flood the context window and add unacceptable latency. Instead, we capture a keyframe every 2.5 seconds at reduced resolution.

*   **Frontend:** A `setInterval` draws the video element onto a hidden canvas at 640×480, converts to JPEG at 0.7 quality (~30–50KB per frame), and sends it over the WebSocket with a type header byte (0x01 for video, 0x00 for audio) so the backend can distinguish.
*   **Backend:** Reads the header byte, then forwards the payload to the Gemini session with the appropriate `mime_type` (audio/pcm or image/jpeg). Gemini accumulates visual context and uses it when relevant.

**Why 2–3 seconds?** Faster than 2s floods the context with redundant frames. Slower than 4s misses critical moments. 2.5s is the sweet spot for cooking where things change gradually. This can be made adaptive later (faster during active cooking, slower when idle).

### 5.3 ADK Agent Tools

| Tool Name | What It Does |
| :--- | :--- |
| `identify_ingredients` | Triggers Gemini to analyse the current camera frame and return a structured list of visible ingredients |
| `search_recipes` | Queries Firestore for recipes matching the identified ingredients, filtered by dietary preferences. Returns top 5 ranked by match percentage |
| `set_timer` | Creates a cooking timer with a label and duration. Stores in session state and triggers a frontend notification when done |
| `get_substitution` | Given a missing ingredient, available ingredients, and recipe context, suggests the best swap |
| `convert_units` | Handles conversions between metric and imperial (grams to cups, ml to tbsp, etc.) |
| `get_nutritional_info` | Returns estimated nutritional information for the current recipe at the current serving size |
| `advance_step` | Moves the session to the next recipe step, updates Firestore, returns the new step’s instruction and visual cue |

### 5.4 Tool Response Formatting
The critical insight: how you format tool responses determines whether the agent sounds smart or confused. Keep responses concise and decision-relevant. Don’t dump entire recipe documents — summarise what the agent needs for the current moment.

For example, a `search_recipes` response should include: recipe name, match percentage, difficulty, total time, and which ingredients are missing. The agent then naturally says something like: "I found a 90% match for Aglio e Olio — you have everything you need and it takes about 25 minutes."

### 5.5 The System Prompt
This is the single most important piece of text in the project. It defines the agent’s personality, workflow, visual monitoring behaviour, error handling, and safety awareness. Key principles:
*   Be concise — the user has messy hands and can’t scroll through long responses.
*   Walk through steps **ONE AT A TIME**. Wait for verbal or visual confirmation before advancing.
*   Always confirm visual observations verbally: "I can see the onions browning" not silently noting it.
*   If unsure about what you see, **ASK** rather than guess.
*   Stay positive when mistakes happen. Suggest a fix, don’t blame.
*   Warn about hot surfaces, sharp tools, and allergens proactively.
*   During idle moments (waiting for a timer), share fun facts, suggest what to prep next, or ask about serving size.

---

## 6. Codebase Structure

```text
kitchen-copilot/
├── frontend/
│   ├── index.html
│   ├── app.js             # camera/mic capture, WebSocket client
│   └── styles.css
├── backend/
│   ├── main.py            # FastAPI app, WebSocket endpoint
│   ├── session_manager.py # Gemini Live API session mgmt
│   ├── agent.py           # ADK agent, system prompt, tools
│   ├── tools/
│   │   ├── recipe_search.py   # Firestore recipe queries
│   │   ├── ingredient_id.py   # parse vision output
│   │   ├── timer.py           # cooking timer management
│   │   ├── substitution.py    # ingredient swap logic
│   │   └── nutrition.py       # nutritional info lookup
│   ├── models/
│   │   ├── recipe.py      # Pydantic models
│   │   ├── session.py
│   │   └── ingredient.py
│   ├── db/
│   │   ├── firestore_client.py
│   │   └── seed_recipes.py    # populate recipe DB
│   └── config.py          # env vars, GCP config
├── infra/
│   ├── Dockerfile
│   ├── cloudbuild.yaml    # CI/CD (bonus points)
│   └── terraform/         # optional IaC (bonus)
├── docs/
│   ├── architecture.png
│   └── deployment-proof.md
├── README.md
└── requirements.txt
```

---

## 7. Task Delegation & Timeline

**Philosophy:** vertical slices, not horizontal layers. Everyone works together to get the minimum viable loop working first, then we layer features and polish. A working ugly prototype beats a beautiful broken one.

Assuming ~8–12 hours per person per week (evenings/weekends), that gives us roughly 50–70 person-hours total across the two weeks.

### Phase 1: Core Loop (Days 1–5)
**Goal:** Open browser → talk to agent → show kitchen counter → agent responds. No styling, no recipe logic. Just the bidirectional stream working end-to-end.

| Person | Tasks |
| :--- | :--- |
| **Person A** | Frontend camera/mic capture using MediaStream API. Plain HTML page with `<video>` element and a connect button. Stream raw audio chunks + video frames over WebSocket. No styling. |
| **Person B** | FastAPI server with WebSocket endpoint. Establish Gemini Live API session. Forward audio bidirectionally. Get the agent talking back first — video frames come second. Define basic ADK agent with system prompt. |
| **Person C** | Google Cloud project setup. Cloud Run deployment from Dockerfile. Firestore with basic recipe collection (10–20 recipes to start). Repo structure and CI setup. |

**Phase 1 Milestone:** By end of Day 5: you should be able to open a browser, talk to the agent, show it your kitchen counter, and have it respond with voice. This is the make-or-break milestone.

### Phase 2: Intelligence (Days 6–10)
**Goal:** Make it a cooking agent, not just a generic voice bot. Add recipe search, ingredient identification, step-by-step guidance, timers, and substitution handling.

| Person | Tasks |
| :--- | :--- |
| **Person A** | Build tool implementations — the actual Python functions the ADK agent calls. Recipe search against Firestore, ingredient parsing, timer management, unit conversion, substitution logic. |
| **Person B** | Agent brain — refine system prompt, build state machine for recipe progression (which step, what’s completed), handle edge cases (substitutions, mistakes, skipped steps), tune video frame sampling. |
| **Person C** | Enrich data layer — expand to 50–100 recipes, add dietary tags, build nutritional lookup, start architecture diagram and README draft. |

### Phase 3: Polish & Submission (Days 11–14)

| Person | Tasks |
| :--- | :--- |
| **Person A** | Make the frontend look good — recipe sidebar, timer widgets, listening/speaking indicators, mobile responsive. Camera positioning guide. |
| **Person B** | Hardening — error handling, latency optimization, multi-language test (quick win for demo), 2–3 full end-to-end cooking sessions as tests. |
| **Person C** | Lead demo video production (script + rehearse + record). Cloud deployment proof recording. Blog post. Final README polish. GDG profile signups. |

**Days 12–14 (all 3):** Integration testing, bug fixing, and recording the final demo video. Do at least 2–3 full end-to-end cooking sessions.
