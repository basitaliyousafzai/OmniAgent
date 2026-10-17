import React from "react";
import { 
  FolderTree, 
  Monitor, 
  Terminal, 
  ShieldAlert, 
  Settings, 
  OctagonAlert, 
  Sparkles, 
  RefreshCw,
  Zap,
  Users
} from "lucide-react";

export type ActiveTab = "explorer" | "os_control" | "team" | "terminal" | "audit";

interface ActivityBarProps {
  activeTab: ActiveTab;
  onSelectTab: (tab: ActiveTab) => void;
  onOpenSettings: () => void;
  killSwitchEngaged: boolean;
  onTriggerKillSwitch: () => void;
  onResetKillSwitch: () => void;
  pendingApprovalsCount: number;
}

export const ActivityBar: React.FC<ActivityBarProps> = ({
  activeTab,
  onSelectTab,
  onOpenSettings,
  killSwitchEngaged,
  onTriggerKillSwitch,
  onResetKillSwitch,
  pendingApprovalsCount
}) => {
  return (
    <div className="w-14 bg-[#08090d] border-r border-indigo-900/40 flex flex-col items-center justify-between py-3 select-none z-20 shadow-2xl relative">
      {/* Background Micro Scanline */}
      <div className="absolute inset-0 cyber-grid-dense opacity-20 pointer-events-none" />

      {/* Top Section: OmniAgent Cyber Logo & Main Views */}
      <div className="flex flex-col items-center gap-3.5 w-full z-10">
        <div 
          className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-indigo-600 to-pink-500 flex items-center justify-center shadow-lg shadow-cyan-500/30 mb-2 cursor-pointer transition-transform hover:scale-110 glow-cyan relative"
          title="OmniAgent OS — Sovereign Desktop Agent"
        >
          <Sparkles className="w-5 h-5 text-white animate-pulse" />
          <div className="absolute -bottom-1 w-2 h-0.5 bg-cyan-300 rounded-full" />
        </div>

        {/* Workspace Explorer */}
        <button
          onClick={() => onSelectTab("explorer")}
          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all relative ${
            activeTab === "explorer"
              ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/60 glow-cyan"
              : "text-gray-400 hover:text-cyan-300 hover:bg-white/5"
          }`}
          title="Workspace Explorer (Files & Code)"
        >
          <FolderTree className="w-5 h-5" />
          {activeTab === "explorer" && (
            <span className="absolute -left-1 w-1 h-5 bg-cyan-400 rounded-r-full" />
          )}
        </button>

        {/* Full OS & Window Control Plane */}
        <button
          onClick={() => onSelectTab("os_control")}
          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all relative ${
            activeTab === "os_control"
              ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/60 glow-cyan"
              : "text-gray-400 hover:text-cyan-300 hover:bg-white/5"
          }`}
          title="OS Control Plane (Visual Studio, SSMS, Screen)"
        >
          <Monitor className="w-5 h-5" />
          {activeTab === "os_control" && (
            <span className="absolute -left-1 w-1 h-5 bg-cyan-400 rounded-r-full" />
          )}
        </button>

        {/* Multi-Agent Swarm & Team Organization */}
        <button
          onClick={() => onSelectTab("team")}
          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all relative ${
            activeTab === "team"
              ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/60 glow-cyan"
              : "text-gray-400 hover:text-cyan-300 hover:bg-white/5"
          }`}
          title="Multi-Agent Swarm Organization (6 Specialized Cores)"
        >
          <Users className="w-5 h-5" />
          {activeTab === "team" && (
            <span className="absolute -left-1 w-1 h-5 bg-cyan-400 rounded-r-full" />
          )}
        </button>

        {/* Integrated Terminal */}
        <button
          onClick={() => onSelectTab("terminal")}
          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all relative ${
            activeTab === "terminal"
              ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/50 glow-indigo"
              : "text-gray-400 hover:text-indigo-300 hover:bg-white/5"
          }`}
          title="Terminal (PowerShell / PTY Multiplexer)"
        >
          <Terminal className="w-5 h-5" />
          {activeTab === "terminal" && (
            <span className="absolute -left-1 w-1 h-5 bg-indigo-400 rounded-r-full" />
          )}
        </button>

        {/* Audit Log / Safety Fabric */}
        <button
          onClick={() => onSelectTab("audit")}
          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all relative ${
            activeTab === "audit"
              ? "bg-purple-500/20 text-purple-300 border border-purple-500/50 glow-magenta"
              : "text-gray-400 hover:text-purple-300 hover:bg-white/5"
          }`}
          title="Safety & Audit Fabric (Logs & Interceptions)"
        >
          <ShieldAlert className="w-5 h-5" />
          {activeTab === "audit" && (
            <span className="absolute -left-1 w-1 h-5 bg-purple-400 rounded-r-full" />
          )}
          {pendingApprovalsCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 text-black text-[10px] font-bold rounded-full flex items-center justify-center animate-bounce shadow-[0_0_8px_#f59e0b]">
              {pendingApprovalsCount}
            </span>
          )}
        </button>
      </div>

      {/* Bottom Section: Kill Switch & Settings */}
      <div className="flex flex-col items-center gap-3 w-full z-10">
        {/* Emergency Kill Switch */}
        {killSwitchEngaged ? (
          <button
            onClick={onResetKillSwitch}
            className="w-10 h-10 rounded-lg bg-red-600/30 text-red-400 border border-red-500 flex items-center justify-center hover:bg-red-600 hover:text-white transition-all animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.5)]"
            title="Emergency Kill Switch Engaged! Click to Reset."
          >
            <RefreshCw className="w-5 h-5 animate-spin" />
          </button>
        ) : (
          <button
            onClick={onTriggerKillSwitch}
            className="w-10 h-10 rounded-lg bg-red-950/40 text-red-400 hover:bg-red-600 hover:text-white border border-red-900/60 transition-all flex items-center justify-center group hover:shadow-[0_0_15px_rgba(239,68,68,0.4)]"
            title="EMERGENCY STOP (Ctrl+Esc) - Aborts all automation instantly"
          >
            <OctagonAlert className="w-5 h-5 group-hover:scale-110 transition-transform" />
          </button>
        )}

        {/* Settings Modal */}
        <button
          onClick={onOpenSettings}
          className="w-10 h-10 rounded-lg flex items-center justify-center text-gray-400 hover:text-cyan-300 hover:bg-white/5 transition-colors"
          title="Settings (Models, API Keys, Voice)"
        >
          <Settings className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default ActivityBar;
