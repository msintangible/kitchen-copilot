import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * useCopilotWebSocket Hook
 * Manages the connection to the backend orchestrator and 
 * multiplexes audio/video/json data over a single WebSocket.
 */
export function useCopilotWebSocket(url) {
  const [isConnected, setIsConnected] = useState(false);
  const [sessionState, setSessionState] = useState(null); // Backend updates
  const wsRef = useRef(null);
  
  // Audio playback
  const playbackContextRef = useRef(null);
  const nextPlayTimeRef = useRef(0);

  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      // Initialize playback audio context immediately on user interaction
      // (Browsers auto-suspend AudioContexts if created inside async callbacks)
      if (!playbackContextRef.current) {
        playbackContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
          sampleRate: 24000 // Gemini returns 24kHz audio typically
        });
        nextPlayTimeRef.current = playbackContextRef.current.currentTime;
      } else if (playbackContextRef.current.state === 'suspended') {
        playbackContextRef.current.resume();
      }

      // Step 1: Pre-flight auth to get one-time token
      // Derive HTTP url from WS url (ws://localhost:8000/ws -> http://localhost:8000/session/token)
      const httpUrl = url.replace('ws://', 'http://').replace('wss://', 'https://').replace('/ws', '/session/token');
      const res = await fetch(httpUrl, { method: 'POST' });
      if (!res.ok) throw new Error("Failed to get session token");
      const { token, session_id } = await res.json();
      
      console.log(`Secured session: ${session_id}`);

      // Step 2: Connect with token
      const wsUrlWithToken = `${url}?token=${token}`;
      const ws = new WebSocket(wsUrlWithToken);
      
      // We expect binary data from the server (either PCM audio or JSON as text blocks)
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        console.log("Connected to Copilot Backend");
        setIsConnected(true);
      };

      ws.onclose = () => {
        console.log("Disconnected from Copilot Backend");
        setIsConnected(false);
      };

      ws.onerror = (err) => {
        console.error("WebSocket Error:", err);
      };

      let inChunkCount = 0;
      ws.onmessage = (event) => {
        // Handle incoming data
        if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data);
            console.log("Copilot State Update:", data);
            setSessionState(data);
          } catch (e) {
            console.error("Failed to parse websocket message", e);
          }
        } else if (event.data instanceof ArrayBuffer) {
          // It's raw PCM audio from Gemini (Int16)
          inChunkCount++;
          if (inChunkCount % 20 === 0) console.log(`[Audio In] Received ${event.data.byteLength} bytes from Gemini (x${inChunkCount})`);
          playAudioChunk(new Int16Array(event.data));
        }
      };

      wsRef.current = ws;

    // Listeners for outgoing captures
    let outChunkCount = 0;
    const handleAudioChunk = (e) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) return;
      const float32Array = e.detail;
      
      // Convert Float32 (-1.0 to 1.0) to Int16 (-32768 to 32767)
      const int16Array = new Int16Array(float32Array.length);
      let maxVol = 0;
      for (let i = 0; i < float32Array.length; i++) {
        const s = Math.max(-1, Math.min(1, float32Array[i]));
        if (Math.abs(s) > maxVol) maxVol = Math.abs(s);
        int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      
      // Prefix with 0x00 for Audio
      const buffer = new Uint8Array(int16Array.buffer.byteLength + 1);
      buffer[0] = 0x00;
      buffer.set(new Uint8Array(int16Array.buffer), 1);
      
      outChunkCount++;
      if (outChunkCount % 50 === 0) {
        console.log(`[Audio Out] Vol: ${maxVol.toFixed(4)}, size: ${buffer.byteLength} bytes (x${outChunkCount})`);
      }
      wsRef.current.send(buffer);
    };

    const handleVideoFrame = async (e) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) return;
      const blob = e.detail;
      const arrayBuffer = await blob.arrayBuffer();
      
      // Prefix with 0x01 for Video
      const buffer = new Uint8Array(arrayBuffer.byteLength + 1);
      buffer[0] = 0x01;
      buffer.set(new Uint8Array(arrayBuffer), 1);
      
      wsRef.current.send(buffer);
    };

    window.addEventListener('copilot-audio-chunk', handleAudioChunk);
    window.addEventListener('copilot-video-frame', handleVideoFrame);

    wsRef.current._cleanupListeners = () => {
      window.removeEventListener('copilot-audio-chunk', handleAudioChunk);
      window.removeEventListener('copilot-video-frame', handleVideoFrame);
    };

    } catch (e) {
      console.error("Failed to connect websocket", e);
    }
  }, [url]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      if (wsRef.current._cleanupListeners) wsRef.current._cleanupListeners();
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Simple sequential audio player for PCM chunks
  const playAudioChunk = (int16Array) => {
    const ctx = playbackContextRef.current;
    if (!ctx) return;

    // Convert Int16 back to Float32
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    const audioBuffer = ctx.createBuffer(1, float32Array.length, ctx.sampleRate);
    audioBuffer.getChannelData(0).set(float32Array);

    const source = ctx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(ctx.destination);

    // Schedule playback seamlessly
    const startTime = Math.max(ctx.currentTime, nextPlayTimeRef.current);
    source.start(startTime);
    nextPlayTimeRef.current = startTime + audioBuffer.duration;
  };

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  return {
    isConnected,
    sessionState,
    connect,
    disconnect
  };
}
