import { CheckCircle2 } from 'lucide-react';
import { useRef, useEffect } from 'react';

export function RecipeSidebar({ recipeName, difficulty, time, steps, identifiedIngredients, onStepClick }) {
  const stepsContainerRef = useRef(null);
  const activeStepRef = useRef(null);

  // Auto-scroll to next active step — pin it to the top of the container
  useEffect(() => {
    if (activeStepRef.current) {
      activeStepRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
  let displayIngredients = identifiedIngredients;
  
  if (!allDone && steps && identifiedIngredients) {
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

  return (
    <aside className="recipe-sidebar glass-panel animate-in" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header - fixed at top */}
      <div style={{ flexShrink: 0 }}>
        <h2 className="text-xl font-semibold tracking-tight">{recipeName}</h2>
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
      >
        <div className="space-y-3">
          {steps?.map((step) => (
            <div 
              key={step.num} 
              ref={step.num === scrollTargetNum ? activeStepRef : null}
              onClick={() => !step.done && onStepClick?.(step.num)}
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

      {/* Ingredients - always visible, pinned below steps */}
      {displayIngredients?.length > 0 && (
        <div style={{ flexShrink: 0, paddingTop: '12px', paddingBottom: '8px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <h3 className="text-xs uppercase tracking-wider text-slate-400 mb-2 font-semibold">Identified ({displayIngredients.length})</h3>
          <div className="flex flex-wrap gap-2">
            {displayIngredients.map(ing => (
              <span 
                key={ing} 
                className="ingredient-tag px-3 py-1.5 rounded-full text-xs font-medium bg-slate-800/80 border border-slate-700/50 text-slate-200 shadow-sm backdrop-blur-md flex items-center gap-2"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400/80"></div>
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
    </aside>
  );
}
