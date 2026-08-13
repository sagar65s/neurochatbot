"use client";

import { useRef, KeyboardEvent, useState, useEffect } from "react";

// Web Speech API isn't in default TS lib types — declared loosely here
// rather than pulling in an extra @types package for one feature.
type SpeechRecognitionLike = any;

export default function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<SpeechRecognitionLike>(null);

  // Tracks intent: true while the user wants recording to keep going.
  // Set to false only when the user explicitly taps the mic to stop —
  // this is what lets us tell "user stopped it" apart from "the browser
  // auto-ended the session after a pause," so we can transparently
  // restart in the latter case and keep behaving like a continuous
  // WhatsApp-style voice note instead of cutting off on silence.
  const shouldListenRef = useRef(false);
  const finalTranscriptRef = useRef("");

  useEffect(() => {
    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    setVoiceSupported(Boolean(SpeechRecognitionCtor));
  }, []);

  function autoResize() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }

  function handleSend() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function startRecognition() {
    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setVoiceSupported(false);
      return;
    }

    const recognition: SpeechRecognitionLike = new SpeechRecognitionCtor();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    // continuous = true is the key fix: without it, the browser stops
    // listening the moment it detects a short pause in speech. With it,
    // recording stays open — like holding a WhatsApp voice note — until
    // the user explicitly taps the mic again.
    recognition.continuous = true;

    recognition.onresult = (event: any) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscriptRef.current += transcript + " ";
        } else {
          interim += transcript;
        }
      }
      setValue((finalTranscriptRef.current + interim).trim());
      autoResize();
    };

    recognition.onerror = (event: any) => {
      // "aborted" fires when we call .stop() ourselves — expected, not
      // an error. "no-speech" can fire during a long pause even in
      // continuous mode; onend (below) decides whether to restart.
      if (event.error === "aborted") return;
    };

    recognition.onend = () => {
      if (shouldListenRef.current) {
        // The browser ended the session on its own (common after a long
        // pause or an internal timeout) but the user hasn't tapped stop
        // yet — restart transparently so recording keeps going.
        try {
          recognition.start();
          return;
        } catch {
          // Instance can't be restarted — fall through and finalize.
        }
      }

      setIsListening(false);
      const text = finalTranscriptRef.current.trim();
      finalTranscriptRef.current = "";
      if (text) {
        onSend(text);
        setValue("");
        if (textareaRef.current) textareaRef.current.style.height = "auto";
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
  }

  /**
   * WhatsApp-style voice message: tap the mic once to start — it keeps
   * recording continuously, ignoring pauses in speech, until you tap the
   * mic again to stop. On stop, the transcribed text is sent
   * automatically, like releasing a voice note.
   */
  function toggleVoiceInput() {
    if (disabled) return;

    if (isListening) {
      // User wants to stop now — trigger onend, which finalizes and sends.
      shouldListenRef.current = false;
      recognitionRef.current?.stop();
      return;
    }

    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setVoiceSupported(false);
      return;
    }

    finalTranscriptRef.current = "";
    shouldListenRef.current = true;
    setIsListening(true);
    startRecognition();
  }

  return (
    <div className="border-t border-paper-border bg-paper-bg px-4 py-3 dark:border-ink-border dark:bg-ink-bg">
      <div className="mx-auto flex max-w-3xl items-end gap-2 rounded border border-paper-border bg-paper-surface px-3 py-2 dark:border-ink-border dark:bg-ink-surface">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            autoResize();
          }}
          onKeyDown={handleKeyDown}
          placeholder={isListening ? "Listening... tap mic to stop" : "Message NeuroChat..."}
          rows={1}
          disabled={disabled}
          className="max-h-[200px] flex-1 resize-none bg-transparent py-1.5 text-[15px] outline-none placeholder:text-ink-muted disabled:opacity-50"
        />

        {voiceSupported && (
          <button
            onClick={toggleVoiceInput}
            disabled={disabled}
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded transition disabled:opacity-30 ${
              isListening
                ? "bg-red-500 text-white animate-pulse"
                : "text-ink-muted hover:bg-ink-border/40 hover:text-accent"
            }`}
            aria-label={isListening ? "Stop voice message" : "Start voice message"}
            title={isListening ? "Recording — tap to stop and send" : "Voice message"}
          >
            <MicIcon />
          </button>
        )}

        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-accent text-white transition hover:bg-accent-hover disabled:opacity-30"
          aria-label="Send message"
        >
          <ArrowUpIcon />
        </button>
      </div>
      <p className="mx-auto mt-1.5 max-w-3xl text-center text-[11px] text-ink-muted">
        {isListening
          ? "Recording... tap the mic again to stop and send"
          : "Enter to send · Shift + Enter for new line · Tap the mic for a voice message"}
      </p>
    </div>
  );
}

function ArrowUpIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M12 19V5M5 12l7-7 7 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0M12 19v3" strokeLinecap="round" />
    </svg>
  );
}
