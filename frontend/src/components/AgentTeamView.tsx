import React, { useState, useEffect } from "react";
import { 
  Users, 
  Cpu, 
  Eye, 
  Hammer, 
  ShieldCheck, 
  Code, 
  Mic, 
  Zap, 
  Activity, 
  CheckCircle2, 
  Radio, 
  Sparkles, 
  Play, 
  RefreshCw,
  Layers,
  ArrowRight
} from "lucide-react";

interface AgentMember {
  id: string;
  name: string;
  codename: string;
  role: string;
  specialty: string;
  status: "ACTIVE" | "REASONING" | "EXECUTING" | "STANDBY";
  color: string;
  icon: any;
  tasksCompleted: number;
  autonomy: "FULL" | "SUPERVISED";
}

interface AgentTeamViewProps {
  isThinking?: boolean;
  currentStep?: number;
  activeTarget?: string;
}

export const AgentTeamView: React.FC<AgentTeamViewProps> = ({
  isThinking = false,
  currentStep = 0,
  activeTarget = "Windows Desktop OS"
}) => {
  const [agents, setAgents] = useState<AgentMember[]>([
    {
      id: "apex",
      name: "Commander APEX",
      codename: "AGENT-01 // ORCHESTRATOR",
      role: "Strategic Goal Synthesis & ReAct Planner",
      specialty: "High-level plan decomposition, multi-turn reasoning, token budget management",
      status: isThinking ? "REASONING" : "STANDBY",
      color: "cyan",
      icon: Cpu,
      tasksCompleted: 42,
      autonomy: "FULL"
    },
    {
      id: "argus",
      name: "Perception ARGUS",
      codename: "AGENT-02 // VISION RETICLE",
      role: "Multimodal Vision & Screen Spatial Mapping",
      specialty: "1080p color buffer analysis, 0-1000 coordinate reticle, OCR UI tree resolution",
      status: isThinking ? "EXECUTING" : "STANDBY",
      color: "purple",
      icon: Eye,
      tasksCompleted: 118,
      autonomy: "FULL"
    },
    {
      id: "forge",
      name: "Operator FORGE",
      codename: "AGENT-03 // OS CONTROLLER",
      role: "Native Windows API & Input Automation",
      specialty: "Win32 window focus, PyAutoGUI hardware mouse/keyboard events, SSMS/VS control",
      status: isThinking ? "EXECUTING" : "STANDBY",
      color: "emerald",
      icon: Hammer,
      tasksCompleted: 87,
      autonomy: "FULL"
    },
    {
      id: "sentinel",
      name: "Guardian SENTINEL",
      codename: "AGENT-04 // SAFETY GATE",
      role: "Zero-Trust Safety & Human-in-the-Loop Interlock",
      specialty: "Regex command firewall, SQL drop interception, global Ctrl+Esc hardware kill switch",
      status: "ACTIVE",
      color: "amber",
      icon: ShieldCheck,
      tasksCompleted: 215,
      autonomy: "SUPERVISED"
    },
    {
      id: "cipher",
      name: "Engineer CIPHER",
      codename: "AGENT-05 // CODE & SHELL",
      role: "Monaco Code Editor & Terminal PTY Multiplexer",
      specialty: "File tree semantic indexing, diff patch engine, isolated PowerShell subprocesses",
      status: "STANDBY",
      color: "pink",
      icon: Code,
      tasksCompleted: 64,
      autonomy: "FULL"
    },
    {
      id: "echo",
      name: "Liaison ECHO",
      codename: "AGENT-06 // AUDIO & SPEECH",
      role: "Multimodal Voice STT & Neural Audio Synthesizer",
      specialty: "Offline Whisper VAD listener, neural voice TTS, proactive spoken dialogue",
      status: "ACTIVE",
      color: "yellow",
      icon: Mic,
      tasksCompleted: 53,
      autonomy: "FULL"
    }
  ]);

  const [swarmLogs, setSwarmLogs] = useState<string[]>([
    "[SWARM_INIT] 6/6 Agentic cores initialized & bound to Sovereign Event Bus.",
    "[SENTINEL] Zero-Trust regex guardrails armed. Interlock status: ACTIVE.",
    "[ECHO] Neural Speech synthesis and Whisper STT loop calibrated.",
    "[APEX] Standing by for operator goals via Voice or Chat HUD."
  ]);

  const [activeTabFilter, setActiveTabFilter] = useState<"ALL" | "ACTIVE">("ALL");

  useEffect(() => {
    if (isThinking) {
      setSwarmLogs((prev) => [
        `[APEX ➔ ARGUS] Goal received. Step #${currentStep}: Analyzing target desktop view...`,
        `[ARGUS ➔ FORGE] Reticle calibrated on target: ${activeTarget}. Coordinating inputs.`,
        ...prev.slice(0, 8)
      ]);
      setAgents((prev) =>
        prev.map((a) =>
          a.id === "apex"
            ? { ...a, status: "REASONING" }
            : a.id === "argus" || a.id === "forge"
            ? { ...a, status: "EXECUTING" }
            : a
        )
      );
    } else {
      setAgents((prev) =>
        prev.map((a) =>
          a.id === "apex" || a.id === "argus" || a.id === "forge"
            ? { ...a, status: "STANDBY" }
            : a
        )
      );
    }
  }, [isThinking, currentStep, activeTarget]);

  const runSwarmDiagnostic = () => {
    setSwarmLogs((prev) => [
      `[DIAGNOSTIC] Operator triggered full swarm neural resonance check...`,
      `[APEX] Core OK. Context buffer: 28% capacity.`,
      `[ARGUS] Primary Display 1920x1080 mapped. Reticle precision: 0.1%.`,
      `[FORGE] Win32 SwitchToThisWindow API loaded.`,
      `[SENTINEL] Safety interlock hotkey Ctrl+Esc active.`,
      `[ECHO] Speech synthesizers online.`,
      ...prev.slice(0, 10)
    ]);
  };

  const getStatusBadge = (status: AgentMember["status"]) => {
    switch (status) {
      case "REASONING":
        return "bg-pink-500/20 text-pink-300 border-pink-500/60 animate-pulse";
      case "EXECUTING":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/60 animate-bounce";
      case "ACTIVE":
        return "bg-cyan-500/20 text-cyan-300 border-cyan-500/60";
      default:
        return "bg-slate-800 text-gray-400 border-slate-700";
    }
  };

  return (
    <div className="flex-1 h-full bg-[#0a0b12] flex flex-col overflow-y-auto p-4 space-y-4 cyber-scanline select-none">
      {/* View Header with Cyber HUD */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-indigo-900/40 gap-3">
        <div>
          <h2 className="text-sm font-bold text-gray-100 flex items-center gap-2 font-hud tracking-wide">
            <Users className="w-4 h-4 text-cyan-400" />
            <span className="uppercase text-cyan-300">OmniAgent Sovereign Swarm & Multi-Agent Organization</span>
          </h2>
          <p className="text-xs text-gray-400 font-mono">
            Autonomous multi-agent management division: 6 specialized agents collaborating in real-time
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={runSwarmDiagnostic}
            className="px-3 py-1.5 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-800/50 text-cyan-300 font-mono text-xs flex items-center gap-1.5 transition-all glow-cyan"
            title="Ping all agents"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>PING SWARM</span>
          </button>

          <div className="px-2.5 py-1 rounded-lg bg-indigo-950/50 border border-indigo-800/40 text-[10px] font-mono text-indigo-300 flex items-center gap-1.5">
            <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
            <span>6/6 MESH SYNCED</span>
          </div>
        </div>
      </div>

      {/* Swarm Hierarchy & Active Roster Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {agents.map((ag) => {
          const Icon = ag.icon;
          return (
            <div
              key={ag.id}
              className={`p-3.5 rounded-xl border bg-[#0e101a]/90 backdrop-blur-md transition-all duration-300 flex flex-col justify-between ${
                ag.status === "REASONING"
                  ? "border-pink-500/70 shadow-[0_0_20px_rgba(236,72,153,0.25)]"
                  : ag.status === "EXECUTING"
                  ? "border-emerald-500/70 shadow-[0_0_20px_rgba(16,185,129,0.25)]"
                  : "border-indigo-900/40 hover:border-cyan-500/50"
              }`}
            >
              {/* Agent Card Top Bar */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-indigo-950/60 border border-indigo-800/50 text-cyan-400">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="font-bold text-xs text-white font-hud tracking-wide">{ag.name}</div>
                      <div className="text-[9px] text-gray-500 font-mono">{ag.codename}</div>
                    </div>
                  </div>

                  <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold border ${getStatusBadge(ag.status)}`}>
                    {ag.status}
                  </span>
                </div>

                {/* Role Description */}
                <div className="text-[11px] font-semibold text-cyan-300/90 font-sans mt-1">
                  {ag.role}
                </div>
                <div className="text-[10px] text-gray-400 font-mono mt-1 leading-relaxed">
                  {ag.specialty}
                </div>
              </div>

              {/* Agent Card Footer */}
              <div className="mt-3 pt-2.5 border-t border-indigo-950 flex items-center justify-between text-[10px] font-mono text-gray-500">
                <span className="flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span>Tasks: {ag.tasksCompleted}</span>
                </span>

                <span className="px-1.5 py-0.2 rounded bg-black/50 text-indigo-300 border border-indigo-950">
                  {ag.autonomy === "FULL" ? "⚡ FULL AUTO" : "🛡️ SUPERVISED"}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Live Inter-Agent Neural Bus & Communication Feed */}
      <div className="bg-[#0c0d16]/95 border border-indigo-900/40 rounded-xl p-3 flex flex-col space-y-2 flex-1 min-h-[160px]">
        <div className="flex items-center justify-between pb-1 border-b border-indigo-950 text-xs font-mono">
          <span className="text-cyan-400 font-bold flex items-center gap-1.5 font-hud uppercase">
            <Activity className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span>Inter-Agent Neural Communication Bus</span>
          </span>
          <span className="text-[10px] text-gray-500">AES-256 ZERO-LATENCY IPC</span>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1 font-mono text-[11px] max-h-48 pr-1">
          {swarmLogs.map((log, i) => (
            <div key={i} className="text-gray-300 flex items-start gap-1.5 leading-snug">
              <span className="text-cyan-500 shrink-0">›</span>
              <span className={log.includes("APEX") ? "text-cyan-300" : log.includes("ARGUS") ? "text-purple-300" : log.includes("FORGE") ? "text-emerald-300" : log.includes("SENTINEL") ? "text-amber-300" : "text-gray-400"}>
                {log}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AgentTeamView;
