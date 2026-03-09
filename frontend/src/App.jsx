import { useState } from 'react';
import { Camera, Mic, Play, Pause, Square, Flame, CheckCircle2, ChevronRight, Timer as TimerIcon } from 'lucide-react';
import { useMediaCapture } from './hooks/useMediaCapture';
import { useCopilotWebSocket } from './hooks/useCopilotWebSocket';
import { RecipeSidebar } from './components/RecipeSidebar';
import { TimerWidget } from './components/TimerWidget';
import './App.css';

// Replace with actual cloud run URL when deploying
const WS_URL = 'ws://localhost:8000/ws';

function App() {
  const { videoRef, isCapturing, startCapture, stopCapture } = useMediaCapture();
  const { isConnected, sessionState, connect, disconnect } = useCopilotWebSocket(WS_URL);
  
  const [isActive, setIsActive] = useState(false);
  
  // Derive status from session state
  const agentStatus = isActive ? 'listening' : 'idle'; 
  const displayStatus = isActive ? 'Live' : 'Idle';
  
  // Mock Data for layout testing - using state so steps can be clicked to complete
  const recipeInfo = {
    name: "Classic Spaghetti Aglio e Olio",
    difficulty: "Easy",
    time: "25 min"
  };

  const initialSteps = [
    { num: 1, text: "Bring a large pot of salted water to boil. Add spaghetti and cook until al dente.", active: true, done: false, ingredients: ["Spaghetti"] },
    { num: 2, text: "Meanwhile, thinly slice the garlic and finely chop the parsley.", active: false, done: false, ingredients: ["Garlic"] },
    { num: 3, text: "Heat olive oil in a large skillet over medium heat. Sauté garlic until golden.", active: false, done: false, ingredients: ["Olive Oil", "Garlic", "Chili Flakes"] },
    { num: 4, text: "Add a ladle of pasta water to the skillet, then toss in the drained spaghetti.", active: false, done: false, ingredients: [] },
    { num: 5, text: "Toss vigorously over low heat until an emulsified sauce forms.", active: false, done: false, ingredients: [] },
    { num: 6, text: "Remove from heat, stir in fresh parsley, and season with salt and pepper.", active: false, done: false, ingredients: [] },
    { num: 7, text: "Serve immediately, optionally topped with freshly grated parmesan cheese.", active: false, done: false, ingredients: [] },
  ];

  const [mockSteps, setMockSteps] = useState(initialSteps);

  const identifiedIngredients = ["Garlic", "Spaghetti", "Olive Oil", "Chili Flakes"];

  // Click a step to mark it as done and advance to the next
  const handleStepClick = (stepNum) => {
    setMockSteps(prev => prev.map(s => {
      if (s.num === stepNum && !s.done) {
        return { ...s, done: true, active: false };
      }
      if (s.num === stepNum + 1) {
        return { ...s, active: true };
      }
      return s;
    }));
  };

  // If sessionState is populated from the backend, use it. Otherwise, use mock.
  const activeRecipe = sessionState?.recipe || recipeInfo;
  const activeSteps = sessionState?.steps || mockSteps;
  const activeIngredients = sessionState?.ingredients || identifiedIngredients;
  const activeTimers = sessionState?.timers || [
    { id: '1', label: "Boil Pasta", durationSeconds: 600, remainingSeconds: 600, status: "created" },
    { id: '2', label: "Bake Chicken", durationSeconds: 1500, remainingSeconds: 420, status: "running" },
    { id: '3', label: "Chill Dessert", durationSeconds: 3600, remainingSeconds: 3600, status: "paused" }
  ];

  const toggleActive = () => {
    if (!isActive) {
      setMockSteps(initialSteps); // Reset steps to fresh state
      startCapture();
      connect();
      setIsActive(true);
    } else {
      stopCapture();
      disconnect();
      setIsActive(false);
    }
  };

  return (
    <div className="app-container">
      
      {/* Background Video Layer */}
      <div className={`main-viewport ${!isActive ? 'no-video' : ''}`}>
        {!isActive && (
          <div className="flex flex-col items-center gap-4 text-center">
            <Camera className="placeholder-icon" />
            <h1 className="text-2xl font-light tracking-wide text-white">Kitchen Copilot</h1>
            <p className="text-slate-400">Ready to start cooking?</p>
          </div>
        )}
        {/* The active video feed */}
        <video 
          ref={videoRef}
          autoPlay 
          playsInline 
          muted 
          className={`w-full h-full object-cover ${!isActive ? 'hidden' : ''}`}
        />
        {isActive && (
          <div className="absolute inset-0 bg-slate-800/20"></div>
        )}
      </div>

      {/* Top HUD */}
      <div className="hud-top">
        <div className="glass-pill status-pill">
          <div className={`animate-pulse status-dot ${agentStatus}`}></div>
          <span className="capitalize">{displayStatus}</span>
        </div>
        
        {isActive && (
          <div className="glass-pill px-4 py-2 flex items-center gap-2">
            <Flame size={16} className="text-orange-400" />
            <span className="text-sm font-medium">{recipeInfo.name}</span>
          </div>
        )}
      </div>

      {/* Main Recipe Sidebar (Visible only when active) */}
      {isActive && (
        <RecipeSidebar 
          recipeName={activeRecipe.name}
          difficulty={activeRecipe.difficulty}
          time={activeRecipe.time}
          steps={activeSteps}
          identifiedIngredients={activeIngredients}
          onStepClick={handleStepClick}
        />
      )}

      {/* Floating Timers Area */}
      {isActive && activeTimers.length > 0 && (
        <div className="timers-container">
          {activeTimers.map(t => (
            <TimerWidget 
              key={t.id} 
              label={t.label} 
              durationSeconds={t.durationSeconds}
              remainingSeconds={t.remainingSeconds}
              status={t.status}
            />
          ))}
        </div>
      )}

      {/* Bottom Controls */}
      <div className="controls-dock glass-pill">
        <button 
          onClick={toggleActive}
          className={`btn ${isActive ? 'btn-danger' : 'btn-primary'}`}
        >
          {isActive ? <Square size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
          {isActive ? 'Stop Session' : 'Start Copilot'}
        </button>
        
        {isActive && (
          <button className="btn-icon">
            <Mic size={20} />
          </button>
        )}
      </div>

    </div>
  );
}

export default App;
