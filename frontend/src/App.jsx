import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Camera, Mic, MicOff, Play, Square, Flame } from 'lucide-react';
import { useMediaCapture } from './hooks/useMediaCapture';
import { useCopilotWebSocket } from './hooks/useCopilotWebSocket';
import { RecipeSidebar } from './components/RecipeSidebar';
import { RecipePicker } from './components/RecipePicker';
import { TimerWidget } from './components/TimerWidget';
import './App.css';
import logoUrl from './assets/logo.png';

// Replace with actual cloud run URL when deploying
const WS_URL = 'wss://kitchen-copilot-backend-769490847746.us-central1.run.app/ws';

// Command hints that rotate on the idle start screen
const COMMAND_HINTS = [
  '"I have x ingredients"',
  '"Set a 10 minute timer"',
  '"Next step"',
  '"I\'m done with this step"',
  '"Show recipe"',
  '"Hide recipe"',
  '"Mute"',
  '"What step am I on?"',
  '"How much time is left?"',
  '"Show x timer"',
  '"What can I cook with these ..."',
  '"Stop session"',
];

const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const RECIPE_COMPLETE_COUNTDOWN = 60; // seconds

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
  const [targetStep, setTargetStep] = useState(null);
  
  // Sequential step check-off effect
  useEffect(() => {
    if (targetStep === null || !isActive) return;
    if (currentStep < targetStep) {
      const timer = setTimeout(() => {
        setCurrentStep(prev => prev + 1);
      }, 400); // Clean 400ms pace
      return () => clearTimeout(timer);
    } else {
      // Animation finished!
      setTargetStep(null);
    }
  }, [currentStep, targetStep, isActive, setCurrentStep]);

  // Rotating hint state
  const [hintIndex, setHintIndex] = useState(0);
  const [hintVisible, setHintVisible] = useState(true);

  // Recipe completion auto-end state
  const [completionCountdown, setCompletionCountdown] = useState(null);

  // Inactivity detection state
  const lastActivityRef = useRef(Date.now());
  const [showInactivityPrompt, setShowInactivityPrompt] = useState(false);
  const [showEndSessionConfirm, setShowEndSessionConfirm] = useState(false);
  
  // Derive status from session state
  const agentStatus = isActive ? 'listening' : 'idle'; 
  const displayStatus = isActive ? 'Live' : 'Idle';

  // Register generic UI command callback so voice commands work
  useEffect(() => {
    uiCommandCallbackRef.current = (command) => {
      console.log("Frontend received UI command:", command.action, command);
      if (command.action === 'toggle_mute') toggleMute();
      if (command.action === 'focus_timer' && command.timer_id) {
        setFocusedTimerId(command.timer_id);
      }
      if (command.action === 'stop_session') {
        setShowEndSessionConfirm(true);
      }
      if (command.action === 'all_steps_done' && activeRecipe) {
        const total = activeRecipe.steps.length;
        console.log(`Setting target step: ${total}`);
        setTargetStep(total);
      }
    };
  }, [toggleMute, uiCommandCallbackRef, activeRecipe]);

  // Build steps array from active recipe
  const activeSteps = activeRecipe?.steps?.map((text, i) => ({
    num: i + 1,
    text,
    active: i === currentStep,
    done: i < currentStep,
  })) || [];

  // Handle step click from sidebar
  const handleStepClick = (stepNum) => {
    setCurrentStep(stepNum);
  };

  // Handle recipe selection from picker
  const handleRecipeSelect = (recipe) => {
    console.log("User clicked recipe:", recipe.name);
    sendMessage({ clientContent: `I want to cook the ${recipe.name} recipe.` });
  };

  // ── Rotating Command Hints ──────────────────────────────────
  useEffect(() => {
    if (isActive) return;
    const interval = setInterval(() => {
      setHintIndex(prev => (prev + 1) % COMMAND_HINTS.length);
    }, 2500);
    return () => clearInterval(interval);
  }, [isActive]);

  // ── Timer Acknowledgment (6-second pulse) ──────────────────
  const [acknowledgedTimerIds, setAcknowledgedTimerIds] = useState(new Set());
  const pendingAckTimeouts = useRef(new Set());

  useEffect(() => {
    for (const t of timers) {
      if (t.status === 'completed' && !pendingAckTimeouts.current.has(t.id)) {
        pendingAckTimeouts.current.add(t.id);
        setTimeout(() => {
          setAcknowledgedTimerIds(prev => new Set([...prev, t.id]));
          pendingAckTimeouts.current.delete(t.id);
        }, 6000);
      }
    }
    const currentIds = new Set(timers.map(t => t.id));
    setAcknowledgedTimerIds(prev => {
      const cleaned = new Set([...prev].filter(id => currentIds.has(id)));
      return cleaned.size !== prev.size ? cleaned : prev;
    });
  }, [timers]);

  const displayTimers = useMemo(() => {
    let sorted = [...timers];
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

  // ── Recipe Completion Auto-End ──────────────────────────────
  const allStepsDone = activeSteps.length > 0 && activeSteps.every(s => s.done);
  const completionTriggered = useRef(false);

  useEffect(() => {
    // Only trigger celebration if all steps are done and AFTER any sequential animation finishes
    if (allStepsDone && isActive && !completionTriggered.current && targetStep === null) {
      completionTriggered.current = true;
      sendMessage({ clientContent: `System: The user has completed all recipe steps. Congratulate them briefly and let them know the session will end in ${RECIPE_COMPLETE_COUNTDOWN} seconds unless they want to continue.` });
      setCompletionCountdown(RECIPE_COMPLETE_COUNTDOWN);
    }
    if (!allStepsDone) {
      completionTriggered.current = false;
      setCompletionCountdown(null);
    }
  }, [allStepsDone, isActive, sendMessage, targetStep]);

  useEffect(() => {
    if (completionCountdown === null || completionCountdown < 0) return;
    if (completionCountdown === 0) {
      stopCapture();
      disconnect();
      setIsActive(false);
      setCompletionCountdown(null);
      completionTriggered.current = false;
      return;
    }
    const timer = setTimeout(() => setCompletionCountdown(prev => prev - 1), 1000);
    return () => clearTimeout(timer);
  }, [completionCountdown]);

  const handleContinueSession = () => {
    setCompletionCountdown(null);
    completionTriggered.current = true; // Prevent re-triggering
  };

  // ── Inactivity Detection ──────────────────────────────────
  useEffect(() => {
    if (!isActive) return;

    const resetActivity = () => {
      lastActivityRef.current = Date.now();
      setShowInactivityPrompt(false);
    };

    window.addEventListener('copilot-audio-chunk', resetActivity);
    window.addEventListener('click', resetActivity);
    window.addEventListener('touchstart', resetActivity);

    const checkInterval = setInterval(() => {
      const elapsed = Date.now() - lastActivityRef.current;
      if (elapsed >= INACTIVITY_TIMEOUT_MS && !showInactivityPrompt) {
        setShowInactivityPrompt(true);
        sendMessage({ clientContent: "System: The user has been inactive for a while. Ask them briefly if they are still there." });
      }
    }, 30000); // Check every 30 seconds

    return () => {
      window.removeEventListener('copilot-audio-chunk', resetActivity);
      window.removeEventListener('click', resetActivity);
      window.removeEventListener('touchstart', resetActivity);
      clearInterval(checkInterval);
    };
  }, [isActive, showInactivityPrompt, sendMessage]);

  const handleInactivityYes = () => {
    lastActivityRef.current = Date.now();
    setShowInactivityPrompt(false);
  };

  const handleInactivityNo = () => {
    setShowInactivityPrompt(false);
    stopCapture();
    disconnect();
    setIsActive(false);
  };

  const toggleActive = () => {
    if (!isActive) {
      startCapture();
      connect();
      setIsActive(true);
      lastActivityRef.current = Date.now();
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
          <div className="flex flex-col items-center gap-4 text-center mb-6">
            <img 
              src={logoUrl} 
              alt="Kitchen Copilot Logo" 
              style={{ width: '120px', height: '120px', objectFit: 'contain' }} 
            />
            <h1 className="text-2xl font-light tracking-wide text-white">Kitchen Copilot</h1>
            <p 
              key={hintIndex}
              className="text-slate-400 command-hint"
              style={{ minHeight: '1.5em' }}
            >
              {COMMAND_HINTS[hintIndex]}
            </p>
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

      {/* Recipe Completion Countdown Popup */}
      {completionCountdown !== null && (
        <div className="popup-overlay">
          <div className="glass-panel animate-in">
            <span className="popup-emoji">🎉</span>
            <h2>Recipe Complete!</h2>
            <p>
              Session ending in <span className="countdown-number">{completionCountdown}s</span>
            </p>
            <div className="popup-actions">
              <button 
                onClick={handleContinueSession}
                className="btn btn-primary"
              >
                Keep Cooking
              </button>
              <button 
                onClick={() => { stopCapture(); disconnect(); setIsActive(false); setCompletionCountdown(null); }}
                className="btn btn-danger"
              >
                End Session
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Inactivity Check Popup */}
      {showInactivityPrompt && (
        <div className="popup-overlay">
          <div className="glass-panel animate-in">
            <span className="popup-emoji">👋</span>
            <h2>Are you still there?</h2>
            <p>
              You've been quiet for a while. Want to keep cooking?
            </p>
            <div className="popup-actions">
              <button onClick={handleInactivityYes} className="btn btn-primary">
                Yes, I'm here!
              </button>
              <button onClick={handleInactivityNo} className="btn btn-danger">
                End Session
              </button>
            </div>
          </div>
        </div>
      )}

      {/* End Session Confirmation Popup (Voice triggered) */}
      {showEndSessionConfirm && (
        <div className="popup-overlay">
          <div className="glass-panel animate-in">
            <span className="popup-emoji">👋</span>
            <h2>End Session?</h2>
            <p>
              Are you sure you want to stop the cooking session?
            </p>
            <div className="popup-actions">
              <button 
                onClick={() => {
                  stopCapture();
                  disconnect();
                  setIsActive(false);
                  setShowEndSessionConfirm(false);
                }} 
                className="btn btn-danger"
              >
                End Session
              </button>
              <button onClick={() => setShowEndSessionConfirm(false)} className="btn btn-primary">
                Keep Cooking
              </button>
            </div>
          </div>
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
