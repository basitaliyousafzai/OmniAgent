import React from "react";
import { 
  Cpu, 
  ShieldCheck, 
  HardDrive, 
  Wifi, 
  Terminal, 
  Monitor,
  Activity,
  Layers
} from "lucide-react";

interface TelemetryDeckProps {
  isThinking: boolean;
  activeWindow?: string;
  tokenVelocity?: string;
  contextUsagePercent?: number;
  latencyMs?: number;
}

export const TelemetryDeck: React.FC<TelemetryDeckProps> = ({
  isThinking,
  activeWindow = "Windows Desktop OS",
  tokenVelocity = "92.4",
  contextUsagePercent = 28,
  latencyMs = 16
}) => {
  return (
    <div className="w-full bg-[#10121a]/95 border-b border-indigo-900/40 px-3 py-1.5 flex items-center justify-between text-xs font-mono select-none backdrop-blur-md z-10">
      {/* Active Target Window Pill */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/40 text-cyan-300 font-hud text-[11px] font-semibold">
          <Monitor className="w-3 h-3 text-cyan-400" />
          <span className="text-gray-400">TARGET:</span>
          <span className="truncate max-w-[140px] text-white" title={activeWindow}>
            {activeWindow}
          </span>
        </div>

        {/* Live System Mode */}
        <div className="hidden sm:flex items-center gap-1 text-[10px] text-indigo-300 px-2 py-0.5 rounded bg-indigo-950/50 border border-indigo-800/30 font-mono">
          <Terminal className="w-2.5 h-2.5 text-indigo-400" />
          <span>SOVEREIGN OS</span>
        </div>
      </div>

      {/* Center Animated Telemetry Beacon */}
      <div className="hidden md:flex items-center gap-4 text-[10px] text-gray-400">
        <div className="flex items-center gap-1.5">
          <Activity className={`w-3 h-3 ${isThinking ? "text-pink-400 animate-pulse" : "text-emerald-400"}`} />
          <span className="text-gray-400">VELOCITY:</span>
          <span className="text-white font-bold">{isThinking ? `${tokenVelocity} t/s` : "IDLE"}</span>
        </div>

        <div className="flex items-center gap-1.5">
          <Layers className="w-3 h-3 text-purple-400" />
          <span className="text-gray-400">CONTEXT:</span>
          <div className="w-12 h-1.5 bg-gray-800 rounded-full overflow-hidden flex items-center">
            <div 
              className="h-full bg-gradient-to-r from-cyan-400 to-indigo-500 rounded-full transition-all duration-500"
              style={{ width: `${contextUsagePercent}%` }}
            />
          </div>
          <span className="text-purple-300 font-bold">{contextUsagePercent}%</span>
        </div>

        <div className="flex items-center gap-1.5">
          <Wifi className="w-3 h-3 text-cyan-400" />
          <span className="text-gray-400">PING:</span>
          <span className="text-cyan-300">{latencyMs}ms</span>
        </div>
      </div>

      {/* Right Safety Fabric Badge */}
      <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/40 text-emerald-300 text-[10px] font-semibold">
        <ShieldCheck className="w-3 h-3 text-emerald-400" />
        <span className="hidden sm:inline">SAFETY GATE:</span>
        <span className="text-white">ARMED</span>
      </div>
    </div>
  );
};

export default TelemetryDeck;
