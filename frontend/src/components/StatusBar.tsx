import React from "react";
import { Cpu, ShieldCheck, ShieldAlert, Mic, HardDrive, Wifi, WifiOff } from "lucide-react";
import { SystemStatus } from "../types";

interface StatusBarProps {
  status: SystemStatus | null;
  activeProvider: string;
  activeModel: string;
  isThinking: boolean;
  onOpenSettings: () => void;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  status,
  activeProvider,
  activeModel,
  isThinking,
  onOpenSettings
}) => {
  return (
    <div className="h-6 bg-[#08090e] border-t border-indigo-950 flex items-center justify-between px-3 text-[10px] font-mono text-gray-400 select-none z-10">
      {/* Left Status: Provider & Model */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenSettings}
          className="flex items-center gap-1.5 hover:text-cyan-300 transition-colors cursor-pointer text-cyan-400"
          title="Click to configure provider & model"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          <span className="font-bold text-gray-300">CORE:</span>
          <span className="text-cyan-300 truncate max-w-48 uppercase">GEMINI 1.5 FLASH</span>
        </button>

        {/* Neural Gateway Status */}
        <div className="flex items-center gap-1 text-emerald-400" title="API Status">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
          <span className="text-[10px]">GATEWAY: ARMED</span>
        </div>

        {/* Whisper STT Status */}
        <div className="flex items-center gap-1 text-indigo-400" title="Speech-to-Text Whisper Status">
          <Mic className="w-2.5 h-2.5 text-indigo-400" />
          <span className="text-gray-400 text-[10px]">VOICE STT: OFFLINE</span>
        </div>
      </div>

      {/* Right Status: Safety & Host Environment */}
      <div className="flex items-center gap-4">
        {/* Kill Switch Indicator */}
        <div className="flex items-center gap-1">
          {status?.kill_switch_engaged ? (
            <span className="flex items-center gap-1 text-red-400 font-semibold animate-pulse">
              <ShieldAlert className="w-3 h-3 text-red-400" />
              <span>KILL SWITCH ENGAGED</span>
            </span>
          ) : (
            <span className="flex items-center gap-1 text-emerald-400/90" title="Ctrl+Esc armed">
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
              <span>Safety Gate Armed (Ctrl+Esc)</span>
            </span>
          )}
        </div>

        {/* Operating System */}
        {status?.os && (
          <div className="flex items-center gap-1 text-gray-500">
            <HardDrive className="w-3 h-3" />
            <span>{status.os}</span>
          </div>
        )}
      </div>
    </div>
  );
};
