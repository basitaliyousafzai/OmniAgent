import React from "react";
import { Mic, Volume2 } from "lucide-react";

interface LiveAudioVisualizerProps {
  isActive: boolean;
  isRecording?: boolean;
  isTranscribing?: boolean;
  label?: string;
}

export const LiveAudioVisualizer: React.FC<LiveAudioVisualizerProps> = ({
  isActive,
  isRecording = false,
  isTranscribing = false,
  label = "MULTIMODAL AUDIO MATRIX"
}) => {
  const isEngaged = isActive || isRecording || isTranscribing;

  return (
    <div className="w-full bg-[#0b0c13]/90 border border-indigo-900/40 rounded-md p-2 flex flex-col gap-1.5 select-none relative overflow-hidden backdrop-blur-sm">
      {/* Subtle top scanline */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />

      {/* Header telemetry */}
      <div className="flex items-center justify-between text-[9px] font-mono text-gray-400">
        <span className="flex items-center gap-1 text-cyan-300 font-semibold tracking-wider uppercase">
          {isRecording ? (
            <Mic className="w-3 h-3 text-red-400 animate-pulse" />
          ) : (
            <Volume2 className="w-3 h-3 text-cyan-400" />
          )}
          <span>{label}</span>
        </span>
        <span className="font-mono text-[9px] text-indigo-400 flex items-center gap-1">
          <span className={`w-1.5 h-1.5 rounded-full ${isEngaged ? "bg-emerald-400 animate-ping" : "bg-cyan-600"}`} />
          {isRecording ? "RECORDING (MIC)" : isTranscribing ? "WHISPER VAD" : isEngaged ? "SYNTHESIZING" : "STANDBY"}
        </span>
      </div>

      {/* 16-Bar Equalizer Canvas */}
      <div className="h-7 w-full flex items-end justify-between gap-1 px-1 py-0.5 bg-black/40 rounded border border-indigo-950/60">
        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16].map((bar) => {
          const barClass = isEngaged ? `eq-bar-${bar}` : "";
          const staticHeight = isEngaged ? "40%" : `${10 + (bar % 4) * 6}%`;

          return (
            <div
              key={bar}
              className="flex-1 flex flex-col justify-end items-center h-full"
            >
              <div
                className={`w-full rounded-t-sm transition-all duration-300 ${
                  isRecording
                    ? "bg-gradient-to-t from-red-500 via-orange-400 to-yellow-300"
                    : isTranscribing
                    ? "bg-gradient-to-t from-purple-600 via-pink-500 to-cyan-300"
                    : "bg-gradient-to-t from-cyan-600 via-indigo-500 to-purple-400"
                } ${barClass}`}
                style={{
                  height: isEngaged ? undefined : staticHeight,
                  boxShadow: isEngaged ? "0 0 6px rgba(6, 182, 212, 0.4)" : "none"
                }}
              />
            </div>
          );
        })}
      </div>

      {/* Spectrum Frequency Markers */}
      <div className="flex justify-between text-[7px] font-mono text-gray-500 px-1 uppercase tracking-wider">
        <span>60Hz</span>
        <span>250Hz</span>
        <span>1kHz</span>
        <span>4kHz</span>
        <span>16kHz</span>
      </div>
    </div>
  );
};

export default LiveAudioVisualizer;
