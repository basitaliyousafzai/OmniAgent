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
  Activity
} from "lucide-react";
import { ApprovalRequestData, ChatMessage, RiskLevel } from "../types";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";

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
  }, [messages, streamingThought, isThinking]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isThinking) return;
    onSendGoal(inputText.trim());
    setInputText("");
  };

  const getRiskColor = (level: RiskLevel) => {
    switch (level) {
      case "CRITICAL":
        return "bg-red-500/20 text-red-400 border-red-500/50";
      case "HIGH":
        return "bg-orange-500/20 text-orange-400 border-orange-500/50";
      case "MEDIUM":
        return "bg-amber-500/20 text-amber-400 border-amber-500/50";
      default:
        return "bg-cyan-500/20 text-cyan-400 border-cyan-500/50";
    }
  };

  const quickPrompts = [
    { label: "📸 Screenshot Desktop", prompt: "Capture desktop screenshot and describe the active windows." },
    { label: "🛠️ Visual Studio Build", prompt: "Focus Visual Studio and press Ctrl+Shift+B to build the solution." },
    { label: "⚡ SSMS New Query", prompt: "Focus SQL Server Management Studio and open a new query window." },
    { label: "🔍 List Windows", prompt: "List all currently open desktop application windows." }
  ];

  return (
    <div className="w-[420px] h-full bg-[#0d0e14] border-l border-indigo-900/40 flex flex-col relative select-none cyber-scanline">
      {/* Cyber Hacker HUD Header */}
      <div className="p-3 border-b border-indigo-900/40 flex flex-col gap-2 bg-[#12141d]/80 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
            <span className="font-bold text-xs tracking-wider uppercase text-cyan-400 font-mono flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-cyan-400" />
              <span>AGENTIC HUD // SOVEREIGN OS</span>
            </span>
          </div>

          {/* Equalizer Frequency Pulse Visualizer */}
          <div className="flex items-end gap-1 h-4 px-2 py-0.5 rounded bg-black/40 border border-cyan-500/30">
            <div className={`w-1 bg-cyan-400 rounded-full ${isThinking || isRecording ? "eq-bar-1" : "h-1"}`} />
            <div className={`w-1 bg-indigo-400 rounded-full ${isThinking || isRecording ? "eq-bar-2" : "h-2"}`} />
            <div className={`w-1 bg-pink-400 rounded-full ${isThinking || isRecording ? "eq-bar-3" : "h-1"}`} />
            <div className={`w-1 bg-emerald-400 rounded-full ${isThinking || isRecording ? "eq-bar-4" : "h-2"}`} />
          </div>
        </div>

        {/* Telemetry Bar */}
        <div className="flex items-center justify-between text-[10px] text-gray-400 font-mono bg-black/30 px-2 py-1 rounded border border-indigo-950">
          <span className="flex items-center gap-1 text-emerald-400">
            <Radio className="w-2.5 h-2.5" />
            <span>SAFETY MATRIX: ARMED</span>
          </span>
          <span className="text-gray-500">HOOK: WIN32 / UIA</span>
          {isThinking && (
            <span className="text-cyan-300 animate-pulse font-bold">
              EXEC STEP #{currentStep}
            </span>
          )}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 cyber-grid">
        {messages.length === 0 && (
          <div className="py-8 flex flex-col items-center justify-center text-center space-y-4 text-gray-400">
            <div className="w-14 h-14 rounded-2xl bg-indigo-600/10 border border-indigo-500/30 flex items-center justify-center glow-indigo animate-radar">
              <Sparkles className="w-7 h-7 text-indigo-400" />
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-200">OmniAgent OS Ready</p>
              <p className="text-[11px] text-gray-500 mt-1 max-w-xs">
                Direct native OS automation active. Instruct me to control Visual Studio, SSMS, run scripts, or type below.
              </p>
            </div>

            {/* Quick Action Chips */}
            <div className="grid grid-cols-2 gap-2 w-full px-2 pt-2">
              {quickPrompts.map((qp, i) => (
                <button
                  key={i}
                  onClick={() => onSendGoal(qp.prompt)}
                  className="p-2 text-left bg-[#12141d] hover:bg-indigo-950/40 border border-indigo-900/40 hover:border-indigo-500 rounded-lg text-[10px] text-gray-300 hover:text-cyan-300 transition-all font-mono"
                >
                  {qp.label}
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
                <span className="text-[9px] bg-black/40 px-1.5 py-0.2 rounded text-gray-400 border border-indigo-950">
                  {msg.provider} / {msg.model}
                </span>
              )}
            </div>

            {/* Bubble Content */}
            <div
              className={`p-3 rounded-xl max-w-[95%] leading-relaxed ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-tr-none shadow-lg shadow-indigo-600/20"
                  : msg.role === "system"
                  ? "bg-amber-950/30 text-amber-300 border border-amber-500/30 font-mono"
                  : "bg-[#141622] text-gray-200 border border-indigo-900/40 rounded-tl-none glow-indigo"
              }`}
            >
              {msg.content && <div className="whitespace-pre-wrap select-text">{msg.content}</div>}

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
                    </div>
                  ))}
                </div>
              )}

              {/* Visual Screenshot Thumbnail */}
              {msg.screenshotUrl && (
                <div className="mt-2.5">
                  <div className="text-[10px] text-cyan-400 flex items-center gap-1 mb-1 font-mono font-medium">
                    <ImageIcon className="w-3 h-3" />
                    <span>OPTICAL SCREEN TELEMETRY:</span>
                  </div>
                  <a
                    href={msg.screenshotUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="block rounded-lg overflow-hidden border border-cyan-500/30 hover:border-cyan-400 transition-colors glow-cyan"
                  >
                    <img
                      src={msg.screenshotUrl}
                      alt="Desktop View"
                      className="w-full object-cover max-h-48"
                    />
                  </a>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Live Streaming Thought Delta */}
        {streamingThought && (
          <div className="flex flex-col items-start text-xs">
            <div className="text-[11px] text-cyan-400 font-mono font-medium mb-1 flex items-center gap-1.5">
              <Loader2 className="w-3 h-3 animate-spin text-cyan-400" />
              <span>COGNITIVE ENGINE STREAMING...</span>
            </div>
            <div className="bg-[#141622] p-3 rounded-xl rounded-tl-none border border-cyan-500/40 text-gray-300 max-w-[95%] whitespace-pre-wrap select-text font-mono text-[11px] glow-cyan">
              {streamingThought}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* HUMAN-IN-THE-LOOP ACTION CONFIRMATION MODAL / GATEWAY              */}
      {/* ------------------------------------------------------------------ */}
      {pendingApprovals.length > 0 && (
        <div className="absolute inset-0 bg-black/85 backdrop-blur-md z-30 flex flex-col justify-end p-3 animate-fade-in">
          {pendingApprovals.map((appr) => (
            <div
              key={appr.id}
              className="bg-[#12141e] border-2 border-amber-500 rounded-2xl p-4 shadow-2xl shadow-amber-500/20 flex flex-col gap-3 glow-red"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-amber-400 animate-bounce" />
                  <span className="font-bold text-xs uppercase tracking-wider text-amber-400 font-mono">
                    SECURITY INTERCEPT // HUMAN CONFIRMATION
                  </span>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase font-mono ${getRiskColor(
                    appr.risk_level
                  )}`}
                >
                  {appr.risk_level} RISK
                </span>
              </div>

              <p className="text-xs text-gray-200 font-medium leading-relaxed">
                {appr.action_description}
              </p>

              {/* Exact Destructive Command / SQL Box */}
              <div className="bg-[#0b0c10] border border-amber-500/40 rounded-lg p-2.5 font-mono text-xs text-amber-300 select-text overflow-x-auto max-h-32">
                <code>{appr.exact_command_or_query}</code>
              </div>

              {/* Guardrail Reasons */}
              {appr.reasons && appr.reasons.length > 0 && (
                <div className="text-[11px] text-gray-400 space-y-0.5 font-mono">
                  <span className="font-semibold text-gray-300">Flagged Risk Policies:</span>
                  {appr.reasons.map((r, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-amber-300/80">
                      <ChevronRight className="w-3 h-3 shrink-0" />
                      <span>{r}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Actions: ALLOW vs DENY */}
              <div className="flex items-center gap-2 pt-2 border-t border-indigo-900/40">
                <button
                  onClick={() => onSendApproval(appr.id, true)}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2 px-3 rounded-lg text-xs flex items-center justify-center gap-1.5 transition-colors shadow-lg shadow-emerald-600/30"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>ALLOW (Authorize)</span>
                </button>
                <button
                  onClick={() => onSendApproval(appr.id, false, "Denied by human operator")}
                  className="flex-1 bg-red-600 hover:bg-red-500 text-white font-semibold py-2 px-3 rounded-lg text-xs flex items-center justify-center gap-1.5 transition-colors shadow-lg shadow-red-600/30"
                >
                  <XCircle className="w-4 h-4" />
                  <span>DENY (Abort)</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Input Tray */}
      <div className="p-3 border-t border-indigo-900/40 bg-[#12141d]/90">
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
                  : "Command OmniAgent (e.g. 'Build Visual Studio and check for errors', or voice mic)..."
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
                    ? "bg-red-600 text-white animate-pulse"
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
                  className="p-1.5 rounded-lg bg-cyan-500 text-black font-bold hover:bg-cyan-400 disabled:opacity-40 disabled:hover:bg-cyan-500 transition-colors"
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
