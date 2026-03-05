/**
 * useSpeechRecognition — wraps browser Web Speech API with lifecycle management.
 *
 * Feature-detects SpeechRecognition/webkitSpeechRecognition.
 * Returns null for isSupported when browser doesn't support it.
 */

import { useState, useCallback, useRef, useEffect } from 'react';

interface UseSpeechRecognitionReturn {
  isSupported: boolean;
  isListening: boolean;
  transcript: string;
  error: string | null;
  start: () => void;
  stop: () => void;
  reset: () => void;
}

const MAX_LISTEN_MS = 30_000;

export function useSpeechRecognition(): UseSpeechRecognitionReturn {
  const SpeechRecognitionAPI =
    typeof window !== 'undefined'
      ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      : null;

  const isSupported = !!SpeechRecognitionAPI;
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const maxTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cleanup = useCallback(() => {
    if (maxTimerRef.current) {
      clearTimeout(maxTimerRef.current);
      maxTimerRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // already stopped
      }
      recognitionRef.current = null;
    }
    setIsListening(false);
  }, []);

  const start = useCallback(() => {
    if (!SpeechRecognitionAPI) {
      setError('Speech recognition not supported in this browser.');
      return;
    }

    setError(null);
    setTranscript('');

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      const result = event.results[0]?.[0]?.transcript ?? '';
      setTranscript(result);
    };

    recognition.onerror = (event: any) => {
      const msg =
        event.error === 'not-allowed'
          ? 'Microphone access denied. You can enable it in browser settings.'
          : event.error === 'no-speech'
            ? 'No speech detected. Try again or type manually.'
            : event.error === 'network'
              ? 'Speech recognition unavailable. Try again or type manually.'
              : `Speech error: ${event.error}`;
      setError(msg);
      cleanup();
    };

    recognition.onend = () => {
      cleanup();
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);

    // Max listen duration
    maxTimerRef.current = setTimeout(() => {
      cleanup();
    }, MAX_LISTEN_MS);
  }, [SpeechRecognitionAPI, cleanup]);

  const stop = useCallback(() => {
    cleanup();
  }, [cleanup]);

  const reset = useCallback(() => {
    cleanup();
    setTranscript('');
    setError(null);
  }, [cleanup]);

  // Cleanup on unmount
  useEffect(() => cleanup, [cleanup]);

  return { isSupported, isListening, transcript, error, start, stop, reset };
}
