import React, { useRef } from "react";
import { Mic24Filled, MicOff24Filled } from "@fluentui/react-icons";
import { encodeWavMono, mergeFloat32Chunks } from "../../utils/wavEncode";

interface Props {
  setQuestion: (q: string) => void;
  onSend: (question: string, ...args: unknown[]) => void;
  setaudio: (v: boolean) => void;
  audio: boolean;
}

type CaptureState = {
  ctx: AudioContext;
  stream: MediaStream;
  processor: ScriptProcessorNode;
  source: MediaStreamAudioSourceNode;
  chunks: Float32Array[];
};

/**
 * Mic -> 16-bit PCM WAV -> FastAPI /speech/transcribe -> NVIDIA Riva ASR (local gRPC).
 * Set VITE_RIVA_SPEECH=false to disable (shows alert on mic use).
 */
export const Audioconvert = ({ setQuestion, onSend, setaudio, audio }: Props) => {
  const capRef = useRef<CaptureState | null>(null);

  const useRiva = import.meta.env.VITE_RIVA_SPEECH !== "false";
  const baseURL = import.meta.env.VITE_APP_API_URL as string | undefined;

  const startListening = async (e: { preventDefault: () => void }) => {
    e.preventDefault();

    if (!useRiva) {
      alert("Riva speech is disabled (VITE_RIVA_SPEECH=false).");
      return;
    }
    if (!baseURL) {
      alert("Missing VITE_APP_API_URL for speech transcription.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const ctx = new AudioContext();
      const source = ctx.createMediaStreamSource(stream);
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      const chunks: Float32Array[] = [];

      processor.onaudioprocess = (ev) => {
        const ch = ev.inputBuffer.getChannelData(0);
        chunks.push(new Float32Array(ch));
      };

      source.connect(processor);
      processor.connect(ctx.destination);

      capRef.current = { ctx, stream, processor, source, chunks };
      setaudio(true);
    } catch (err) {
      console.error(err);
      alert("Could not access microphone.");
    }
  };

  const stopListening = async () => {
    const cap = capRef.current;
    capRef.current = null;

    if (!cap) {
      setaudio(false);
      return;
    }

    const sampleRate = cap.ctx.sampleRate;

    try {
      cap.processor.disconnect();
      cap.source.disconnect();
      cap.stream.getTracks().forEach((t) => t.stop());
      await cap.ctx.close();

      const merged = mergeFloat32Chunks(cap.chunks);
      if (merged.length === 0) {
        setaudio(false);
        return;
      }

      const wavBlob = encodeWavMono(merged, sampleRate);
      const form = new FormData();
      form.append("file", wavBlob, "speech.wav");

      const res = await fetch(`${baseURL}/speech/transcribe`, {
        method: "POST",
        body: form,
      });

      let data: unknown = {};
      try {
        data = await res.json();
      } catch {
        data = {};
      }

      const text =
        typeof data === "object" && data !== null && typeof (data as { text?: string }).text === "string"
          ? (data as { text: string }).text.trim()
          : "";

      if (!res.ok) {
        const detail =
          typeof data === "object" && data !== null && typeof (data as { detail?: string }).detail === "string"
            ? (data as { detail: string }).detail
            : "";
        throw new Error(detail || `HTTP ${res.status}`);
      }

      if (text) {
        setQuestion(text);
        onSend(text);
      }
    } catch (err) {
      console.error(err);
      alert(`Speech transcription failed. Is Riva running and nvidia-riva-client installed? ${err}`);
    } finally {
      setaudio(false);
    }
  };

  return (
    <div>
      {audio ? (
        <MicOff24Filled
          style={{ marginTop: -20, cursor: "pointer" }}
          primaryFill="#fa3d37"
          onClick={() => void stopListening()}
        />
      ) : (
        <Mic24Filled
          primaryFill="rgba(115, 118, 225, 1)"
          onClick={(e) => void startListening(e)}
          style={{ marginTop: -20, cursor: "pointer" }}
        />
      )}
    </div>
  );
};
