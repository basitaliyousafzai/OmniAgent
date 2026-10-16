import React from "react";
import { 
  FolderTree, 
  Monitor, 
  Terminal, 
  ShieldAlert, 
  Settings, 
  OctagonAlert, 
  Sparkles,
  RefreshCw
} from "lucide-react";

export type ActiveTab = "explorer" | "os_control" | "terminal" | "audit";

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
    <div className="w-14 bg-[#090a0f] border-r border-indigo-950 flex flex-col items-center justify-between py-3 select-none z-20 shadow-2xl">
      {/* Top Section: OmniAgent Cyber Logo & Main Views */}
      <div className="flex flex-col items-center gap-4 w-full">
        <div 
          className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-indigo-600 to-pink-500 flex items-center justify-center shadow-lg shadow-cyan-500/30 mb-2 cursor-pointer transition-transform hover:scale-110 glow-cyan"
          title="OmniAgent OS — Sovereign Desktop Agent"
        >
          <Sparkles className="w-5 h-5 text-white animate-pulse" />
        </div>

        {/* Workspace Explorer */}
        <button
          onClick={() => onSelectTab("explorer")}
          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all relative ${
            activeTab === "explorer"
              ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/50 glow-cyan"
              : "text-gray-400 hover:text-white hover:bg-white/5"
          }`}
          title="Workspace Explorer (Files & Code)"
        >
          <FolderTree className="w-5 h-5" />
        </button>

        {/* Full OS & Window Control Plane */}
        <button
          onClick={() => onSelectTab("os_control")}
          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all relative ${
            activeTab === "os_control"
              ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/50 glow-cyan"
              : "text-gray-400 hover:text-white hover:bg-white/5"
          }`}
          title="OS Control Plane (Visual Studio, SSMS, Screen)"
        >
          <Monitor className="w-5 h-5" />
        </button>

        {/* Integrated Terminal */}
        <button
          onClick={() => onSelectTab("terminal")}
          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors relative ${
            activeTab === "terminal"
              ? "bg-ide-accent/20 text-indigo-400 border border-indigo-500/30"
              : "text-gray-400 hover:text-white hover:bg-ide-hover"
          }`}
          title="Terminal (PowerShell / PTY Multiplexer)"
        >
          <Terminal className="w-5 h-5" />
        </button>

        {/* Audit Log / Safety Fabric */}
        <button
          onClick={() => onSelectTab("audit")}
          className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors relative ${
            activeTab === "audit"
              ? "bg-ide-accent/20 text-indigo-400 border border-indigo-500/30"
              : "text-gray-400 hover:text-white hover:bg-ide-hover"
          }`}
          title="Safety & Audit Fabric (Logs & Interceptions)"
        >
          <ShieldAlert className="w-5 h-5" />
          {pendingApprovalsCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 text-black text-[10px] font-bold rounded-full flex items-center justify-center animate-bounce">
              {pendingApprovalsCount}
            </span>
          )}
        </button>
      </div>

      {/* Bottom Section: Kill Switch & Settings */}
      <div className="flex flex-col items-center gap-3 w-full">
        {/* Emergency Kill Switch */}
        {killSwitchEngaged ? (
          <button
            onClick={onResetKillSwitch}
            className="w-10 h-10 rounded-lg bg-red-600/30 text-red-400 border border-red-500 flex items-center justify-center hover:bg-red-600 hover:text-white transition-all animate-pulse"
            title="Emergency Kill Switch Engaged! Click to Reset."
          >
            <RefreshCw className="w-5 h-5 animate-spin" />
          </button>
        ) : (
          <button
            onClick={onTriggerKillSwitch}
            className="w-10 h-10 rounded-lg bg-red-950/40 text-red-400 hover:bg-red-600 hover:text-white border border-red-900/60 transition-all flex items-center justify-center group"
            title="EMERGENCY STOP (Ctrl+Esc) - Aborts all automation instantly"
          >
            <OctagonAlert className="w-5 h-5 group-hover:scale-110 transition-transform" />
          </button>
        )}

        {/* Settings Modal */}
        <button
          onClick={onOpenSettings}
          className="w-10 h-10 rounded-lg flex items-center justify-center text-gray-400 hover:text-white hover:bg-ide-hover transition-colors"
          title="Settings (Models, API Keys, Voice)"
        >
          <Settings className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};
