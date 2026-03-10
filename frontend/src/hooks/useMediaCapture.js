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
  const [isMuted, setIsMuted] = useState(false);
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
        let outputData = inputData;
        
        // Guarantee exactly 16kHz for Gemini APIs
        const targetRate = 16000;
        if (audioCtx.sampleRate > targetRate) {
           const ratio = audioCtx.sampleRate / targetRate;
           const step = Math.round(ratio);
           const downsampled = new Float32Array(Math.floor(inputData.length / step));
           for(let i = 0; i < downsampled.length; i++) {
               downsampled[i] = inputData[i * step];
           }
           outputData = downsampled;
        }

        // Dispatch custom event with PCM data
        window.dispatchEvent(new CustomEvent('copilot-audio-chunk', { detail: outputData }));
      };
      
      audioContextRef.current = audioCtx;
      audioProcessorRef.current = processor;
      
      setIsCapturing(true);
      setIsMuted(false);
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
    setIsMuted(false);
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

  const toggleMute = useCallback(() => {
    if (stream) {
      const audioTracks = stream.getAudioTracks();
      const nextMutedState = !isMuted;
      audioTracks.forEach(track => {
        track.enabled = !nextMutedState;
      });
      setIsMuted(nextMutedState);
    }
  }, [stream, isMuted]);

  return {
    stream,
    videoRef,
    isCapturing,
    isMuted,
    error,
    startCapture,
    stopCapture,
    toggleMute
  };
}
