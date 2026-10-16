import React, { useState } from "react";
import { 
  Sparkles, 
  Cpu, 
  Activity, 
  ShieldAlert, 
  Zap, 
  Compass, 
  ChevronDown, 
  ChevronUp, 
  Layers,
  Flame
} from "lucide-react";

interface NeuralReactorCoreProps {
  isThinking: boolean;
  isExecuting?: boolean;
  hasAlert?: boolean;
  currentStep?: number;
  streamingThought?: string;
}

export const NeuralReactorCore: React.FC<NeuralReactorCoreProps> = ({
  isThinking,
  isExecuting = false,
  hasAlert = false,
  currentStep = 0,
  streamingThought
}) => {
  const [expanded, setExpanded] = useState(false);

  // Determine state styling
  let stateColor = "cyan";
  let statusText = "STANDBY // SOVEREIGN CORE ONLINE";
  let ringBorder1 = "border-cyan-500/40";
  let ringBorder2 = "border-indigo-500/50";
  let glowClass = "glow-cyan";
  let coreBg = "radial-gradient(circle, #06b6d4 0%, #3b82f6 50%, #1e1b4b 100%)";

  if (hasAlert) {
    stateColor = "red";
    statusText = "CRITICAL // SAFETY INTERVENTION ARMED";
    ringBorder1 = "border-red-500/80";
    ringBorder2 = "border-red-600/60";
    glowClass = "glow-red";
    coreBg = "radial-gradient(circle, #ef4444 0%, #b91c1c 60%, #450a0a 100%)";
  } else if (isThinking) {
    stateColor = "magenta";
    statusText = `NEURAL SYNAPSE ACTIVE // STEP ${currentStep}`;
    ringBorder1 = "border-pink-500/70";
    ringBorder2 = "border-purple-500/60";
    glowClass = "glow-magenta";
    coreBg = "radial-gradient(circle, #ec4899 0%, #a855f7 50%, #3b0764 100%)";
  } else if (isExecuting) {
    stateColor = "emerald";
    statusText = "DISPATCHING OS TELEMETRY // DESKTOP USE";
    ringBorder1 = "border-emerald-500/70";
    ringBorder2 = "border-teal-500/60";
    glowClass = "glow-emerald";
    coreBg = "radial-gradient(circle, #10b981 0%, #06b6d4 50%, #064e3b 100%)";
  }

  return (
    <div className="relative flex flex-col items-center bg-[#0d0f17]/90 border-b border-indigo-900/40 p-3 select-none backdrop-blur-md overflow-hidden">
      {/* Background Micro Grid */}
      <div className="absolute inset-0 cyber-grid-dense opacity-20 pointer-events-none" />

      {/* Top HUD Telemetry Ribbon */}
      <div className="w-full flex items-center justify-between text-[10px] font-mono tracking-widest text-gray-400 mb-2 z-10">
        <span className="flex items-center gap-1.5 font-bold uppercase text-gray-300">
          <Activity className="w-3 h-3 text-cyan-400 animate-pulse" />
          <span>NEURAL REACTOR v2.5</span>
        </span>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-indigo-950/60 hover:bg-indigo-900/60 text-indigo-300 border border-indigo-800/40 transition-colors text-[9px]"
          title="Toggle Core Diagnostics"
        >
          {expanded ? <ChevronUp className="w-2.5 h-2.5" /> : <ChevronDown className="w-2.5 h-2.5" />}
          <span>{expanded ? "COLLAPSE" : "DIAGNOSTICS"}</span>
        </button>
      </div>

      {/* 3D Holographic Concentric Reactor Orb */}
      <div 
        className="relative flex items-center justify-center my-1 cursor-pointer transition-transform duration-300 hover:scale-105"
        onClick={() => setExpanded(!expanded)}
        title="Click to toggle AI telemetry matrix"
      >
        {/* Outermost Radar Ring */}
        <div className={`w-28 h-28 rounded-full border border-dashed ${ringBorder1} animate-spin-slow flex items-center justify-center relative`}>
          {/* Degree Markers */}
          <span className="absolute top-0 text-[8px] font-mono text-cyan-400/60">0°</span>
          <span className="absolute right-0 text-[8px] font-mono text-cyan-400/60">90°</span>
          <span className="absolute bottom-0 text-[8px] font-mono text-cyan-400/60">180°</span>
          <span className="absolute left-0 text-[8px] font-mono text-cyan-400/60">270°</span>
        </div>

        {/* Counter-Rotating Intermediate Ring with Tech Tabs */}
        <div className={`absolute w-20 h-20 rounded-full border ${ringBorder2} animate-spin-reverse flex items-center justify-center`}>
          <div className="absolute -top-1 w-2 h-2 bg-cyan-400 rounded-full shadow-[0_0_8px_#22d3ee]" />
          <div className="absolute -bottom-1 w-2 h-2 bg-indigo-400 rounded-full shadow-[0_0_8px_#818cf8]" />
        </div>

        {/* High-Velocity Inner Orbiting Ring */}
        <div className={`absolute w-14 h-14 rounded-full border border-dotted ${isThinking ? "border-pink-400" : "border-cyan-400/80"} ${isThinking ? "animate-pulse-thinking" : "animate-radar"}`} />

        {/* Central Glowing AI Quantum Core */}
        <div
          className={`w-10 h-10 rounded-full flex items-center justify-center shadow-lg relative ${isThinking ? "animate-pulse-thinking" : "animate-pulse-core"} ${glowClass}`}
          style={{ background: coreBg }}
        >
          {hasAlert ? (
            <ShieldAlert className="w-5 h-5 text-white animate-bounce" />
          ) : isThinking ? (
            <Zap className="w-5 h-5 text-white animate-spin" />
          ) : isExecuting ? (
            <Flame className="w-5 h-5 text-white animate-pulse" />
          ) : (
            <Cpu className="w-5 h-5 text-cyan-100" />
          )}

          {/* Core Specular Flare */}
          <div className="absolute top-1 left-2 w-2 h-2 rounded-full bg-white/60 blur-[0.5px]" />
        </div>
      </div>

      {/* Cyber Status Banner */}
      <div className="mt-2 text-center z-10 w-full px-2">
        <div className="font-cyber font-bold text-[11px] tracking-wider text-cyan-300 drop-shadow-[0_0_10px_rgba(6,182,212,0.5)] truncate">
          {statusText}
        </div>
        {streamingThought && isThinking && (
          <div className="text-[10px] text-pink-300/90 font-mono italic mt-0.5 truncate max-w-[360px] animate-pulse">
            "{streamingThought}"
          </div>
        )}
      </div>

      {/* Expandable Holographic Telemetry Deck */}
      {expanded && (
        <div className="w-full mt-3 pt-2.5 border-t border-indigo-900/40 grid grid-cols-2 gap-2 text-[10px] font-mono z-10 bg-black/40 rounded p-2">
          <div className="flex flex-col bg-slate-900/60 p-1.5 rounded border border-indigo-800/30">
            <span className="text-gray-400 text-[9px] flex items-center gap-1">
              <Zap className="w-2.5 h-2.5 text-yellow-400" /> SYNAPSE RATE
            </span>
            <span className="text-cyan-400 font-bold text-xs">
              {isThinking ? "142.8 t/s" : "0.0 t/s"}
            </span>
          </div>

          <div className="flex flex-col bg-slate-900/60 p-1.5 rounded border border-indigo-800/30">
            <span className="text-gray-400 text-[9px] flex items-center gap-1">
              <Layers className="w-2.5 h-2.5 text-indigo-400" /> QUANTUM STACK
            </span>
            <span className="text-purple-300 font-bold text-xs">
              STEP {currentStep} / MAX 25
            </span>
          </div>

          <div className="flex flex-col bg-slate-900/60 p-1.5 rounded border border-indigo-800/30">
            <span className="text-gray-400 text-[9px] flex items-center gap-1">
              <Compass className="w-2.5 h-2.5 text-emerald-400" /> RETICLE CALIBRATION
            </span>
            <span className="text-emerald-300 font-bold text-xs">
              0-1000 COORD MATRIX
            </span>
          </div>

          <div className="flex flex-col bg-slate-900/60 p-1.5 rounded border border-indigo-800/30">
            <span className="text-gray-400 text-[9px] flex items-center gap-1">
              <Sparkles className="w-2.5 h-2.5 text-pink-400" /> SOVEREIGN SHIELD
            </span>
            <span className="text-cyan-300 font-bold text-xs">
              L4 INTERLOCK READY
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default NeuralReactorCore;
