import React, { useState, useEffect } from "react";
import { ActivityBar, ActiveTab } from "./components/ActivityBar";
import { FileExplorer } from "./components/FileExplorer";
import { MonacoEditor } from "./components/MonacoEditor";
import { TerminalView } from "./components/TerminalView";
import { OSControlView } from "./components/OSControlView";
import { AuditView } from "./components/AuditView";
import { AgentChat } from "./components/AgentChat";
import { StatusBar } from "./components/StatusBar";
import { SettingsModal } from "./components/SettingsModal";
import { useAgentSocket } from "./hooks/useAgentSocket";
import { SystemStatus } from "./types";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>("explorer");
  const [selectedFile, setSelectedFile] = useState<string | null>("backend/config.py");
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  // Hook into Agent WebSocket Event Bus
  const {
    connected,
    messages,
    isThinking,
    currentStep,
    streamingThought,
    pendingApprovals,
    sendGoal,
    sendApproval,
    abortGoal
  } = useAgentSocket();

  const loadStatus = async () => {
    try {
      const res = await fetch("/api/status");
      if (res.ok) {
        const data = await res.json();
        setSystemStatus(data);
      }
    } catch (err) {
      console.error("Failed to fetch system status", err);
    }
  };

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 4000);
    return () => clearInterval(interval);
  }, []);

  const triggerKillSwitch = async () => {
    try {
      await fetch("/api/killswitch/trigger", { method: "POST" });
      loadStatus();
    } catch (err) {
      console.error("Kill switch trigger error", err);
    }
  };

  const resetKillSwitch = async () => {
    try {
      await fetch("/api/killswitch/reset", { method: "POST" });
      loadStatus();
    } catch (err) {
      console.error("Kill switch reset error", err);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-ide-bg text-gray-200">
      {/* Main Workspace Frame */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Leftmost Activity Bar */}
        <ActivityBar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          onOpenSettings={() => setIsSettingsOpen(true)}
          killSwitchEngaged={systemStatus?.kill_switch_engaged || false}
          onTriggerKillSwitch={triggerKillSwitch}
          onResetKillSwitch={resetKillSwitch}
          pendingApprovalsCount={pendingApprovals.length}
        />

        {/* Central Workspace Canvas */}
        <div className="flex flex-1 overflow-hidden">
          {activeTab === "explorer" && (
            <>
              <FileExplorer
                selectedFile={selectedFile}
                onSelectFile={(path) => setSelectedFile(path)}
              />
              <MonacoEditor
                filePath={selectedFile}
                onClose={() => setSelectedFile(null)}
              />
            </>
          )}

          {activeTab === "os_control" && <OSControlView />}

          {activeTab === "terminal" && <TerminalView />}

          {activeTab === "audit" && <AuditView />}
        </div>

        {/* Rightmost Conversational Agent HUD & Safety Gateway */}
        <AgentChat
          messages={messages}
          isThinking={isThinking}
          currentStep={currentStep}
          streamingThought={streamingThought}
          pendingApprovals={pendingApprovals}
          onSendGoal={sendGoal}
          onSendApproval={sendApproval}
          onAbortGoal={abortGoal}
        />
      </div>

      {/* Ambient Status Bar */}
      <StatusBar
        status={systemStatus}
        activeProvider="OpenRouter / Multi-Provider"
        activeModel="claude-3.5-sonnet / gpt-4o"
        isThinking={isThinking}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* Settings & Secrets Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSaved={loadStatus}
      />
    </div>
  );
};

export default App;
