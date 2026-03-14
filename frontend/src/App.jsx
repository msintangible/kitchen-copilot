import { useState, useEffect, useCallback, useMemo } from 'react';
import { Camera, Mic, MicOff, Play, Square, Flame } from 'lucide-react';
import { useMediaCapture } from './hooks/useMediaCapture';
import { useCopilotWebSocket } from './hooks/useCopilotWebSocket';
import { RecipeSidebar } from './components/RecipeSidebar';
import { RecipePicker } from './components/RecipePicker';
import { TimerWidget } from './components/TimerWidget';
import './App.css';

// Replace with actual cloud run URL when deploying
const WS_URL = 'ws://localhost:8000/ws';

function App() {
  const { videoRef, isCapturing, isMuted, startCapture, stopCapture, toggleMute } = useMediaCapture();
  const { 
    isConnected, 
    recipes,
    activeRecipe, 
    timers,
    sidebarVisible,
    setSidebarVisible,
    currentStep,
    setCurrentStep,
    uiCommandCallbackRef,
    connect, 
    disconnect,
    sendMessage 
  } = useCopilotWebSocket(WS_URL);
  
  const [isActive, setIsActive] = useState(false);
  const [focusedTimerId, setFocusedTimerId] = useState(null);
  
  // Derive status from session state
  const agentStatus = isActive ? 'listening' : 'idle'; 
  const displayStatus = isActive ? 'Live' : 'Idle';

  // Register generic UI command callback so voice commands work
  useEffect(() => {
    uiCommandCallbackRef.current = (command) => {
      if (command.action === 'toggle_mute') toggleMute();
      if (command.action === 'focus_timer' && command.timer_id) {
        setFocusedTimerId(command.timer_id);
      }
    };
  }, [toggleMute, uiCommandCallbackRef]);

  // Build steps array from active recipe
  const activeSteps = activeRecipe?.steps?.map((text, i) => ({
    num: i + 1,
    text,
    active: i === currentStep,
    done: i < currentStep,
  })) || [];

  // Handle step click from sidebar
  const handleStepClick = (stepNum) => {
    setCurrentStep(stepNum); // Move to the clicked step (marks previous as done)
  };

  // Handle recipe selection from picker
  const handleRecipeSelect = (recipe) => {
    console.log("User clicked recipe:", recipe.name);
    // Send message to Gemini stating the user picked the recipe
    sendMessage({ clientContent: `I want to cook the ${recipe.name} recipe.` });
  };

  // Track which completed timers have finished their 6-second pulse
  const [acknowledgedTimerIds, setAcknowledgedTimerIds] = useState(new Set());

  // When a timer becomes completed, wait 6 seconds then mark it as acknowledged
  useEffect(() => {
    const timeouts = [];
    for (const t of timers) {
      if (t.status === 'completed' && !acknowledgedTimerIds.has(t.id)) {
        const timeout = setTimeout(() => {
          setAcknowledgedTimerIds(prev => new Set([...prev, t.id]));
        }, 6000);
        timeouts.push(timeout);
      }
    }
    return () => timeouts.forEach(clearTimeout);
  }, [timers]);

  // Clean up acknowledged IDs for timers that no longer exist
  useEffect(() => {
    const timerIds = new Set(timers.map(t => t.id));
    setAcknowledgedTimerIds(prev => {
      const cleaned = new Set([...prev].filter(id => timerIds.has(id)));
      return cleaned.size !== prev.size ? cleaned : prev;
    });
  }, [timers]);

  // Derive which timers to show (max 3, focused first, acknowledged-completed last)
  const displayTimers = useMemo(() => {
    let sorted = [...timers];

    // Only push completed timers to the back AFTER they've been acknowledged (6s delay)
    sorted.sort((a, b) => {
      const aDone = acknowledgedTimerIds.has(a.id) ? 1 : 0;
      const bDone = acknowledgedTimerIds.has(b.id) ? 1 : 0;
      return aDone - bDone;
    });

    if (focusedTimerId) {
      const idx = sorted.findIndex(t => t.id === focusedTimerId || t.name === focusedTimerId);
      if (idx !== -1) {
        const [focused] = sorted.splice(idx, 1);
        sorted.unshift(focused);
      }
    }
    return sorted.slice(0, 3);
  }, [timers, focusedTimerId, acknowledgedTimerIds]);

  const toggleActive = () => {
    if (!isActive) {
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

      {/* Top HUD — only Live status dot when active */}
      <div className="hud-top">
        <div className="glass-pill status-pill">
          <div className={`animate-pulse status-dot ${agentStatus}`}></div>
          <span className="capitalize">{displayStatus}</span>
        </div>
        
        {/* Recipe name pill — on mobile: always visible; on desktop: only when sidebar is closed */}
        {isActive && activeRecipe && (
          <div className={`glass-pill px-4 py-2 flex items-center gap-2 ${sidebarVisible ? 'mobile-only' : ''}`}>
            <Flame size={16} className="text-orange-400" />
            <span className="text-sm font-medium">{activeRecipe.name}</span>
          </div>
        )}
      </div>

      {/* Recipe Picker Popup — appears when recipes are returned but none selected */}
      {isActive && recipes.length > 0 && !activeRecipe && (
        <RecipePicker 
          recipes={recipes}
          onSelect={handleRecipeSelect}
          onClose={() => {/* User can dismiss by voice */}}
        />
      )}

      {/* Main Recipe Sidebar — only when a recipe is selected AND sidebar is toggled on */}
      {isActive && activeRecipe && sidebarVisible && (
        <RecipeSidebar 
          recipeName={activeRecipe.name}
          difficulty={activeRecipe.match_percentage >= 70 ? "Easy" : activeRecipe.match_percentage >= 40 ? "Medium" : "Hard"}
          time={`${activeSteps.length} steps`}
          steps={activeSteps}
          identifiedIngredients={activeRecipe.missing_ingredients || []}
          onStepClick={handleStepClick}
          onClose={() => setSidebarVisible(false)}
        />
      )}

      {/* Floating Timers Area — only show top 3 timers */}
      {isActive && timers.length > 0 && (
        <div className="timers-container">
          {displayTimers.map(t => (
            <TimerWidget 
              key={t.id || t.name} 
              label={t.name || t.label} 
              durationSeconds={t.total_seconds || t.durationSeconds}
              remainingSeconds={t.remaining_seconds || t.remainingSeconds}
              status={t.status}
            />
          ))}
          {timers.length > 3 && (
            <div className="text-xs text-slate-400 font-medium mt-2 text-center drop-shadow-md" style={{ position: 'relative', zIndex: 60 }}>
              + {timers.length - 3}
            </div>
          )}
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
          <button 
            className={`btn-icon transition-all duration-300 ${isMuted ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]' : 'hover:bg-white/10'}`}
            onClick={toggleMute}
            title={isMuted ? "Unmute Microphone" : "Mute Microphone"}
          >
            {isMuted ? <MicOff size={20} /> : <Mic size={20} />}
          </button>
        )}
      </div>

    </div>
  );
}

export default App;
