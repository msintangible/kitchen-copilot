import { useEffect, useState } from 'react';
import { Timer as TimerIcon, Pause, CheckCircle2 } from 'lucide-react';

export function TimerWidget({ label, durationSeconds, remainingSeconds, status = 'running', onComplete }) {
  // Use remainingSeconds if provided, fallback to durationSeconds
  const initialTime = remainingSeconds !== undefined ? remainingSeconds : durationSeconds;
  const [timeLeft, setTimeLeft] = useState(initialTime);

  // Sync internal state if the backend sends a new remainingSeconds value
  useEffect(() => {
    if (remainingSeconds !== undefined) {
      setTimeLeft(remainingSeconds);
    }
  }, [remainingSeconds]);

  // Main countdown logic based on status
  useEffect(() => {
    if (status !== 'running') return;
    
    if (timeLeft <= 0) {
      if (onComplete) onComplete();
      return;
    }
    
    const intervalId = setInterval(() => {
      setTimeLeft(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    
    return () => clearInterval(intervalId);
  }, [timeLeft, status, onComplete]);

  // Derived styling states
  const isDone = status === 'completed' || (status === 'running' && timeLeft <= 0);
  const isPaused = status === 'paused';
  const isCreated = status === 'created';

  // Format mm:ss
  const mins = Math.floor(timeLeft / 60);
  const secs = timeLeft % 60;
  const timeString = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

  let wrapperClasses = "timer-widget ";
  if (isDone) wrapperClasses += "timer-done animate-pulse ";
  else if (isPaused) wrapperClasses += "timer-paused ";
  else if (isCreated) wrapperClasses += "timer-created ";

  let iconColor = "";
  if (isDone) iconColor = "text-error-color";
  else if (isPaused) iconColor = "text-orange-400";
  else if (isCreated) iconColor = "text-slate-400";
  else iconColor = "text-blue-400";

  return (
    <div className={wrapperClasses.trim()}>
      <div className="timer-info">
        <span className="timer-label">{label}</span>
        <span className={`timer-time ${isDone ? 'text-error-color' : ''} ${isPaused ? 'text-orange-400' : ''}`}>
          {isDone ? '00:00' : timeString}
        </span>
      </div>
      <div className={`timer-icon ${iconColor}`}>
        {isDone ? <CheckCircle2 size={24} /> : isPaused ? <Pause size={24} /> : <TimerIcon size={24} />}
      </div>
    </div>
  );
}
