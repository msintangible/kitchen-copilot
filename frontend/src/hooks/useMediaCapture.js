import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * useMediaCapture Hook
 * Handles getting user media (camera + mic) and provides references
 * and streams for downstream WebSockets or UI playback.
 */
export function useMediaCapture() {
  const [stream, setStream] = useState(null);
  const [error, setError] = useState(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const videoRef = useRef(null);
  
  // Audio Refs
  const audioContextRef = useRef(null);
  const audioProcessorRef = useRef(null);
  const isCapturingRef = useRef(false);

  const startCapture = useCallback(async () => {
    try {
      setError(null);
      // We request both video and audio. 
      // The Gemini Live API expects 16kHz PCM audio, we will handle that downsampling elsewhere.
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: "environment" // Prefer back camera on mobile (kitchen context)
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });
      
      setStream(mediaStream);
      
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }

      // Initialize Audio Context for 16kHz downsampling
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000,
      });
      const source = audioCtx.createMediaStreamSource(mediaStream);
      // We use script processor for direct PCM access (simpler for 16-bit mono conversion)
      // Note: ScriptProcessor is deprecated but widely used for raw PCM access until AudioWorklet is standard everywhere.
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      
      source.connect(processor);
      processor.connect(audioCtx.destination);
      
      processor.onaudioprocess = (e) => {
        if (!isCapturingRef.current) return;
        const inputData = e.inputBuffer.getChannelData(0);
        // Dispatch custom event with PCM data
        window.dispatchEvent(new CustomEvent('copilot-audio-chunk', { detail: inputData }));
      };
      
      audioContextRef.current = audioCtx;
      audioProcessorRef.current = processor;
      
      setIsCapturing(true);
      isCapturingRef.current = true;
    } catch (err) {
      console.error("Error accessing media devices.", err);
      setError(err.message || "Could not access camera/microphone");
    }
  }, []);

  const stopCapture = useCallback(() => {
    isCapturingRef.current = false;
    if (audioProcessorRef.current) {
      audioProcessorRef.current.disconnect();
      audioProcessorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    }
    setIsCapturing(false);
  }, [stream]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [stream]);

  // Video Frame Snapshot Timer
  useEffect(() => {
    let intervalId;
    if (isCapturing && videoRef.current) {
      const canvas = document.createElement('canvas');
      canvas.width = 640;
      canvas.height = 480;
      const ctx = canvas.getContext('2d');

      intervalId = setInterval(() => {
        if (!videoRef.current || videoRef.current.readyState < 2) return;
        
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
        
        // Convert to highly compressed JPEG to save bandwidth (~30kb)
        canvas.toBlob((blob) => {
          if (blob) {
             window.dispatchEvent(new CustomEvent('copilot-video-frame', { detail: blob }));
          }
        }, 'image/jpeg', 0.7);

      }, 2500); // 2.5 seconds as per project plan
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isCapturing]);

  return {
    stream,
    videoRef,
    isCapturing,
    error,
    startCapture,
    stopCapture
  };
}
