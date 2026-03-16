import { CheckCircle2, X } from 'lucide-react';
import { useRef, useEffect, useState } from 'react';

export function RecipeSidebar({ recipeName, difficulty, time, steps, identifiedIngredients, onStepClick, onClose }) {
  const stepsContainerRef = useRef(null);
  const activeStepRef = useRef(null);
  const touchStartY = useRef(0);
  const touchEndY = useRef(0);
  
  // Mobile expands/collapses the sidebar like a mini-player
  const [isExpanded, setIsExpanded] = useState(false);

  const handleTouchStart = (e) => {
    touchStartY.current = e.targetTouches[0].clientY;
  };

  const handleTouchMove = (e) => {
    touchEndY.current = e.targetTouches[0].clientY;
  };

  const handleTouchEnd = () => {
    if (!touchStartY.current || !touchEndY.current) return;
    const distance = touchEndY.current - touchStartY.current;
    
    // Swipe down
    if (distance > 50) {
      if (isExpanded) {
        setIsExpanded(false); // Collapse to pill
      } else if (onClose) {
        onClose(); // Close completely if already a pill
      }
    }
    // Swipe up
    else if (distance < -50 && !isExpanded) {
      setIsExpanded(true); // Expand to full sheet
    }
    
    touchStartY.current = 0;
    touchEndY.current = 0;
  };

  // Auto-scroll to the active step only on user-initiated step changes,
  // NOT on every re-render. This lets users freely scroll to completed steps.
  const lastScrolledStep = useRef(null);

  useEffect(() => {
    const activeNum = steps?.find(s => s.active)?.num;
    if (activeNum && activeNum !== lastScrolledStep.current) {
      lastScrolledStep.current = activeNum;
      // Small delay so DOM updates first, then scroll the element into view.
      // 'nearest' is non-aggressive: only scrolls if out of view, by the minimum
      // amount needed — so users can freely scroll up between step completions.
      setTimeout(() => {
        if (activeStepRef.current) {
          activeStepRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }, 150);
    }
  }, [steps]);

  if (!recipeName) return null;

  const difficultyColor = {
    'Easy': 'text-emerald-400',
    'Medium': 'text-orange-400',
    'Hard': 'text-red-500',
  }[difficulty] || 'text-emerald-400';

  // Calculate remaining ingredients
  const allDone = steps?.every(s => s.done) || false;
  let displayIngredients = identifiedIngredients || [];
  
  if (!allDone && steps && identifiedIngredients?.length > 0) {
    const futureIngredients = new Set();
    steps.forEach(s => {
      if (!s.done && s.ingredients) {
        s.ingredients.forEach(i => futureIngredients.add(i));
      }
    });
    const hasIngredientData = steps.some(s => s.ingredients?.length > 0);
    if (hasIngredientData) {
      displayIngredients = identifiedIngredients.filter(i => futureIngredients.has(i));
    }
  }

  // Find the first non-done step to auto-scroll to
  const scrollTargetNum = steps?.find(s => !s.done)?.num;

  // Progress calculation
  const completedCount = steps?.filter(s => s.done).length || 0;
  const totalSteps = steps?.length || 1;
  const percentage = Math.round((completedCount / totalSteps) * 100);

  // For the collapsed mini-player view, we only show the current step
  const currentStepData = steps?.find(s => s.active) || steps?.[0];

  return (
    <aside 
      className={`recipe-sidebar glass-panel animate-in ${isExpanded ? 'mobile-expanded-sheet' : 'mobile-collapsed-pill'}`} 
      style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
    >
      {/* Mobile drag handle (Only visible on mobile) */}
      <div 
        className="w-full flex justify-center pb-2 cursor-pointer mobile-only"
        style={{ touchAction: 'pan-y', flexShrink: 0 }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="w-12 h-1.5 bg-slate-600/50 rounded-full mt-2"></div>
      </div>

      {/* --- COLLAPSED MOBILE VIEW (Mini-Player) --- */}
      {!isExpanded && currentStepData && (
        <div className="flex-1 flex flex-col justify-between px-3 pb-3 mobile-only" onClick={() => setIsExpanded(true)}>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold text-accent-color uppercase tracking-widest">Step {currentStepData.num} of {totalSteps}</span>
            <span className="text-[10px] font-bold text-slate-400">{percentage}%</span>
          </div>
          <p className="text-sm font-semibold text-white line-clamp-2 leading-tight">
            {currentStepData.text}
          </p>
          <div className="h-1.5 w-full bg-slate-800/80 rounded-full overflow-hidden mt-3 border border-white/5">
            <div className="h-full bg-accent-color shadow-[0_0_8px_rgba(59,130,246,0.5)] transition-all duration-700 ease-out" style={{ width: `${percentage}%` }}></div>
          </div>
        </div>
      )}

      {/* --- EXPANDED VIEW (Desktop or Expanded Mobile) --- */}
      <div className={`flex-1 flex-col overflow-hidden ${isExpanded ? 'flex' : 'desktop-only flex shadow-none border-none bg-transparent'}`}>
        {/* Header - fixed at top */}
        <div style={{ flexShrink: 0 }} className="p-1 desktop-p-0">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold tracking-tight" style={{ flex: 1 }}>{recipeName}</h2>
            {onClose && (
              <button 
                onClick={(e) => { e.stopPropagation(); onClose(); }} 
                className="btn-icon" 
                style={{ width: 44, height: 44, flexShrink: 0 }}
                title="Close sidebar"
              >
                <X size={20} />
              </button>
            )}
          </div>
          <p className="mt-1.5 text-[0.9rem]" style={{ marginBottom: '16px' }}>
            <span className={`${difficultyColor} font-medium`}>{difficulty}</span> 
            <span className="text-slate-500 mx-2">•</span> 
            <span className="text-slate-300 font-medium">{time}</span>
          </p>
          <h3 className="text-xs uppercase tracking-wider text-slate-400 mb-3 font-semibold">Steps</h3>
        </div>

        {/* Steps - scrollable, fills remaining space */}
        <div 
          ref={stepsContainerRef} 
          style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: '8px', paddingBottom: '8px' }}
          className="custom-scrollbar"
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          <div className="space-y-3">
            {steps?.map((step) => (
              <div 
                key={step.num} 
                ref={step.num === scrollTargetNum ? activeStepRef : null}
                onClick={() => step.active && onStepClick?.(step.num)}
                className={`step-card relative ${!step.done ? 'cursor-pointer hover:brightness-110' : ''} ${step.active ? 'active scale-[1.02] shadow-lg border-accent-color/30' : ''} ${step.done ? 'border-emerald-500/20 bg-emerald-500/5' : ''}`}
              >
                {step.active && (
                   <div className="absolute -left-[1px] top-4 bottom-4 w-1 bg-accent-color rounded-r-full shadow-[0_0_8px_rgba(59,130,246,0.6)]"></div>
                )}
                {step.done && (
                   <div className="absolute -left-[1px] top-4 bottom-4 w-1 bg-emerald-400 rounded-r-full opacity-50"></div>
                )}
                <span className={`step-number ${step.active ? 'text-blue-100 font-bold tracking-widest' : step.done ? 'text-emerald-400/80 font-semibold' : ''}`}>
                  <span>Step {step.num}</span>
                  {step.done && <CheckCircle2 size={16} className="text-emerald-400 drop-shadow-md" />}
                </span>
                <p className={`text-sm leading-relaxed ${step.active ? 'text-white font-medium text-[0.95rem]' : step.done ? 'text-slate-400 line-through decoration-slate-600/50' : 'text-slate-300'}`}>
                  {step.text}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Ingredients — capped at ~25% of the combined area, vertical scroll if overflow */}
        {displayIngredients?.length > 0 && (
          <div style={{
            flexShrink: 0,
            paddingTop: '10px',
            paddingBottom: '6px',
            borderTop: '1px solid rgba(255,255,255,0.05)',
          }}>
            <h3 className="text-xs uppercase tracking-wider text-slate-400 mb-2 font-semibold">
              Identified ({displayIngredients.length})
            </h3>
            <div
              className="custom-scrollbar"
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '8px',
                maxHeight: '90px',
                overflowY: 'auto',
                paddingRight: '4px',
                paddingBottom: '4px',
              }}
            >
              {displayIngredients.map(ing => (
                <span
                  key={ing}
                  className="ingredient-tag flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-800/80 border border-slate-700/50 text-slate-200 shadow-sm backdrop-blur-md flex items-center gap-2"
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400/80 flex-shrink-0"></div>
                  {ing}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Progress bar - always visible at bottom */}
        {steps && steps.length > 0 && (
          <div style={{ flexShrink: 0, padding: '12px 0 4px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">Total Progress</span>
              <span className="text-sm font-bold text-accent-color">{percentage}%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden shadow-inner">
              <div 
                className="h-full bg-accent-color transition-all duration-700 ease-out rounded-full relative"
                style={{ width: `${percentage}%` }}
              >
                <div className="absolute inset-0 bg-white/20 w-full" style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)' }}></div>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
