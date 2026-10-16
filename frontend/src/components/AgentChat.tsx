import React, { useState, useRef, useEffect } from "react";
import { 
  Send, 
  Mic, 
  MicOff, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  Square, 
  Image as ImageIcon, 
  Terminal, 
  Code, 
  ChevronRight,
  ShieldAlert,
  Clock,
  Sparkles,
  Radio,
  Cpu,
  Zap,
  Activity,
  Command,
  Flame
} from "lucide-react";
import { ApprovalRequestData, ChatMessage, RiskLevel } from "../types";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";
import { NeuralReactorCore } from "./NeuralReactorCore";
import { LiveAudioVisualizer } from "./LiveAudioVisualizer";

interface AgentChatProps {
  messages: ChatMessage[];
  isThinking: boolean;
  currentStep: number;
  streamingThought: string;
  pendingApprovals: ApprovalRequestData[];
  onSendGoal: (goal: string, imageB64?: string) => void;
  onSendApproval: (id: string, approved: boolean, note?: string) => void;
  onAbortGoal: () => void;
}

export const AgentChat: React.FC<AgentChatProps> = ({
  messages,
  isThinking,
  currentStep,
  streamingThought,
  pendingApprovals,
  onSendGoal,
  onSendApproval,
  onAbortGoal
}) => {
  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-fill input text from voice transcription
  const { isRecording, isTranscribing, startRecording, stopRecording } = useVoiceRecorder(
    (text) => setInputText((prev) => (prev ? `${prev} ${text}` : text))
  );

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingThought, isThinking, pendingApprovals]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isThinking) return;
    onSendGoal(inputText.trim());
    setInputText("");
  };

  const getRiskColor = (level: RiskLevel) => {
    switch (level) {
      case "CRITICAL":
        return "bg-red-500/20 text-red-400 border-red-500/60 shadow-[0_0_15px_rgba(239,68,68,0.25)]";
      case "HIGH":
        return "bg-orange-500/20 text-orange-400 border-orange-500/60 shadow-[0_0_12px_rgba(249,115,22,0.25)]";
      case "MEDIUM":
        return "bg-amber-500/20 text-amber-400 border-amber-500/60";
      default:
        return "bg-cyan-500/20 text-cyan-400 border-cyan-500/60";
    }
  };

  const quickPrompts = [
    { label: "📸 Screenshot Desktop", prompt: "Capture desktop screenshot and describe the active windows." },
    { label: "🛠️ Visual Studio Build", prompt: "Focus Visual Studio and press Ctrl+Shift+B to build the solution." },
    { label: "⚡ SSMS New Query", prompt: "Focus SQL Server Management Studio and open a new query window." },
    { label: "🔍 List Windows", prompt: "List all currently open desktop application windows." }
  ];

  const hasAlert = pendingApprovals.length > 0;

  return (
    <div className="w-[430px] h-full bg-[#0d0e15] border-l border-indigo-900/40 flex flex-col relative select-none cyber-scanline">
      {/* Animated Holographic Neural Reactor Core Header */}
      <NeuralReactorCore
        isThinking={isThinking}
        hasAlert={hasAlert}
        currentStep={currentStep}
        streamingThought={streamingThought}
      />

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 cyber-grid">
        {messages.length === 0 && (
          <div className="py-6 flex flex-col items-center justify-center text-center space-y-3 text-gray-400">
            <div className="w-12 h-12 rounded-2xl bg-cyan-600/10 border border-cyan-500/30 flex items-center justify-center glow-cyan animate-radar">
              <Sparkles className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <p className="text-xs font-bold text-gray-200 font-cyber tracking-wider">OMNIAGENT OS CORE ONLINE</p>
              <p className="text-[11px] text-gray-500 mt-1 max-w-xs font-mono">
                Multimodal autonomous desktop controller active. Instruct me to operate Visual Studio, SSMS, launch terminal scripts, or automate the desktop.
              </p>
            </div>

            {/* Quick Action Chips */}
            <div className="grid grid-cols-2 gap-2 w-full px-1 pt-2">
              {quickPrompts.map((qp, i) => (
                <button
                  key={i}
                  onClick={() => onSendGoal(qp.prompt)}
                  className="p-2 text-left bg-[#131520] hover:bg-cyan-950/40 border border-indigo-900/50 hover:border-cyan-500/70 rounded-lg text-[10px] text-gray-300 hover:text-cyan-300 transition-all font-mono group"
                >
                  <span className="group-hover:translate-x-0.5 inline-block transition-transform">{qp.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col text-xs ${
              msg.role === "user" ? "items-end" : "items-start"
            }`}
          >
            {/* Turn Header */}
            <div className="flex items-center gap-1.5 mb-1 text-[10px] text-gray-500 font-mono">
              <span className={msg.role === "user" ? "text-indigo-400 font-semibold" : "text-cyan-400 font-semibold"}>
                {msg.role === "user" ? "OPERATOR >" : "OMNI_CORE >"}
              </span>
              {msg.provider && (
                <span className="text-[9px] bg-black/50 px-1.5 py-0.2 rounded text-gray-400 border border-indigo-950 font-mono">
                  {msg.provider} / {msg.model}
                </span>
              )}
            </div>

            {/* Bubble Content with Cyber Clip */}
            <div
              className={`p-3 rounded-xl max-w-[95%] leading-relaxed ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-tr-none shadow-lg shadow-indigo-600/20"
                  : msg.role === "system"
                  ? "bg-amber-950/40 text-amber-300 border border-amber-500/40 font-mono"
                  : "bg-[#141624] text-gray-200 border-l-2 border-l-cyan-400 border border-indigo-900/40 rounded-tl-none glow-cyan"
              }`}
            >
              {msg.content && <div className="whitespace-pre-wrap select-text font-sans">{msg.content}</div>}

              {/* Tool Calls History */}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-indigo-900/40 space-y-1.5">
                  {msg.toolCalls.map((tc) => (
                    <div
                      key={tc.id}
                      className="bg-[#0b0c10] p-2 rounded-lg border border-cyan-500/20 font-mono text-[11px]"
                    >
                      <div className="flex items-center gap-1 text-cyan-400 font-semibold mb-1">
                        <Terminal className="w-3 h-3 text-cyan-400" />
                        <span>DISPATCH: {tc.name}</span>
                      </div>
                      <div className="text-gray-400 text-[10px] truncate max-h-20 overflow-y-auto select-text bg-black/40 p-1.5 rounded">
                        {JSON.stringify(tc.arguments, null, 2)}
                      </div>
                      {(() => {
                        const tr = msg.toolResults?.find((r) => r.tool_call_id === tc.id);
                        return tr ? (
                          <div className="mt-1 text-gray-300 text-[10px] max-h-24 overflow-y-auto select-text bg-black/60 p-1.5 rounded border border-indigo-950 font-mono">
                            <span className={tr.ok ? "text-emerald-400" : "text-red-400"}>[{tr.ok ? "OK" : "ERROR"}] </span>
                            {tr.output}
                          </div>
                        ) : null;
                      })()}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Live Streaming ReAct Thought Ticker */}
        {isThinking && (
          <div className="flex flex-col items-start text-xs space-y-1">
            <div className="flex items-center gap-1.5 text-[10px] text-pink-400 font-mono">
              <Loader2 className="w-3 h-3 animate-spin text-pink-400" />
              <span>REASONING IN PROGRESS [STEP #{currentStep}]...</span>
            </div>
            {streamingThought && (
              <div className="p-2.5 rounded-lg bg-pink-950/20 border border-pink-500/40 text-pink-200 text-xs font-mono max-w-[95%] italic animate-pulse">
                {streamingThought}
              </div>
            )}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Human-in-the-Loop Safety Gate Cards */}
      {pendingApprovals.length > 0 && (
        <div className="p-3 bg-red-950/40 border-t border-b border-red-500/60 space-y-2 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-red-400 flex items-center gap-1.5 font-hud tracking-wide">
              <ShieldAlert className="w-4 h-4 text-red-500 animate-bounce" />
              <span>SECURITY CONFIRMATION REQUIRED</span>
            </span>
            <span className="text-[10px] font-mono text-red-300">
              {pendingApprovals.length} PENDING
            </span>
          </div>

          {pendingApprovals.map((appr) => (
            <div
              key={appr.id}
              className={`p-3 rounded-lg border text-xs space-y-2 ${getRiskColor(appr.risk_level)}`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-white uppercase tracking-wider text-[11px] font-hud">
                  {appr.tool_name}
                </span>
                <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-red-900/60 border border-red-500 text-red-200">
                  {appr.risk_level}
                </span>
              </div>

              <div className="text-gray-200 text-xs">
                {appr.action_description || appr.reasons?.join(", ")}
              </div>

              {appr.exact_command_or_query && (
                <div className="bg-black/60 p-2 rounded text-[11px] font-mono text-cyan-300 truncate select-text border border-indigo-950">
                  {appr.exact_command_or_query}
                </div>
              )}

              {/* Action Decision Buttons */}
              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={() => onSendApproval(appr.id, true)}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2 px-3 rounded text-xs flex items-center justify-center gap-1.5 transition-colors shadow-lg shadow-emerald-600/30 font-hud"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>ALLOW (Authorize)</span>
                </button>
                <button
                  onClick={() => onSendApproval(appr.id, false, "Denied by human operator")}
                  className="flex-1 bg-red-600 hover:bg-red-500 text-white font-semibold py-2 px-3 rounded text-xs flex items-center justify-center gap-1.5 transition-colors shadow-lg shadow-red-600/30 font-hud"
                >
                  <XCircle className="w-4 h-4" />
                  <span>DENY (Abort)</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Live Audio Spectrum Equalizer */}
      <div className="px-3 pt-2 bg-[#10121a]/95">
        <LiveAudioVisualizer
          isActive={isThinking}
          isRecording={isRecording}
          isTranscribing={isTranscribing}
          label="SENSORY AUDIO SPECTRUM"
        />
      </div>

      {/* Input Tray */}
      <div className="p-3 border-t border-indigo-900/40 bg-[#10121a]/95">
        <form onSubmit={handleSubmit} className="flex flex-col gap-2">
          <div className="relative flex items-center">
            <textarea
              rows={2}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder={
                isThinking
                  ? "OmniAgent is actively operating desktop..."
                  : "Command OmniAgent (e.g. 'Build Visual Studio and check for errors', or click mic)..."
              }
              disabled={isThinking}
              className="w-full bg-[#0b0c10] border border-indigo-900/60 rounded-xl p-2.5 pr-20 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-colors resize-none font-mono"
            />

            <div className="absolute right-2 bottom-2.5 flex items-center gap-1">
              {/* Voice Input Button */}
              <button
                type="button"
                onClick={isRecording ? stopRecording : startRecording}
                className={`p-1.5 rounded-lg text-xs transition-colors ${
                  isRecording
                    ? "bg-red-600 text-white animate-pulse shadow-[0_0_12px_rgba(239,68,68,0.6)]"
                    : isTranscribing
                    ? "bg-amber-600 text-white"
                    : "text-gray-400 hover:text-white hover:bg-white/10"
                }`}
                title={isRecording ? "Stop Voice Recording" : "Voice Input (Offline Whisper STT)"}
              >
                {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>

              {/* Submit / Abort Button */}
              {isThinking ? (
                <button
                  type="button"
                  onClick={onAbortGoal}
                  className="p-1.5 rounded-lg bg-red-600/30 text-red-400 hover:bg-red-600 hover:text-white border border-red-500/50 transition-colors"
                  title="Abort Current Goal"
                >
                  <Square className="w-4 h-4" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!inputText.trim()}
                  className="p-1.5 rounded-lg bg-cyan-500 text-black font-bold hover:bg-cyan-400 disabled:opacity-40 disabled:hover:bg-cyan-500 transition-colors shadow-[0_0_10px_rgba(6,182,212,0.4)]"
                  title="Dispatch Goal"
                >
                  <Send className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AgentChat;
