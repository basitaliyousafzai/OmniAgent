import React, { useState, useEffect } from "react";
import {
  Play,
  CheckCircle2,
  Clock,
  Film,
  Sparkles,
  Settings,
  RefreshCw,
  AlertCircle,
  ExternalLink,
  Layers,
  Radio,
  Sliders,
  ChevronRight,
  Database,
  BarChart3,
  Video,
  Eye
} from "lucide-react";

interface UploadRecord {
  id: number;
  upload_date: string;
  title: string;
  production_mode: string;
  youtube_id?: string;
  duration_sec?: number;
  file_size_bytes?: number;
  status: string;
  created_at: string;
}

interface ActiveJob {
  is_running: boolean;
  current_stage: string;
  percent: number;
  detail: string;
  last_result?: any;
}

export const YouTubeDashboard: React.FC = () => {
  const [statusData, setStatusData] = useState<any>(null);
  const [activeJob, setActiveJob] = useState<ActiveJob>({
    is_running: false,
    current_stage: "IDLE",
    percent: 0,
    detail: "Ready",
  });
  const [history, setHistory] = useState<UploadRecord[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [recommendedNiches, setRecommendedNiches] = useState<any[]>([]);
  const [isLoadingNiches, setIsLoadingNiches] = useState(false);

  // Form State
  const [niche, setNiche] = useState("AI Innovations & Breakthroughs");
  const [productionMode, setProductionMode] = useState("solo");
  const [llmProvider, setLlmProvider] = useState("gemini");
  const [customTopic, setCustomTopic] = useState("");
  const [forceRun, setForceRun] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");

  // Preview Modal / Player
  const [selectedVideoUrl, setSelectedVideoUrl] = useState<string | null>(null);

  // Fetch status & history
  const fetchStatus = async () => {
    try {
      const res = await fetch("/api/youtube/status");
      if (res.ok) {
        const data = await res.json();
        setStatusData(data);
        if (data.active_job) {
          setActiveJob(data.active_job);
        }
        if (data.config_summary) {
          if (data.config_summary.niche) setNiche(data.config_summary.niche);
          if (data.config_summary.production_mode) setProductionMode(data.config_summary.production_mode);
          if (data.config_summary.llm_provider) setLlmProvider(data.config_summary.llm_provider);
        }
      }
    } catch (err) {
      console.error("Failed to fetch YouTube status:", err);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch("/api/youtube/history");
      if (res.ok) {
        const data = await res.json();
        setHistory(data.uploads || []);
      }
    } catch (err) {
      console.error("Failed to fetch YouTube history:", err);
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch("/api/youtube/logs?limit=40");
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch (err) {
      console.error("Failed to fetch YouTube logs:", err);
    }
  };

  const fetchNiches = async () => {
    setIsLoadingNiches(true);
    try {
      const res = await fetch("/api/youtube/niches");
      if (res.ok) {
        const data = await res.json();
        setRecommendedNiches(data.niches || []);
      }
    } catch (err) {
      console.error("Failed to fetch niches:", err);
    } finally {
      setIsLoadingNiches(false);
    }
  };

  // Setup EventSource for SSE live streaming
  useEffect(() => {
    fetchStatus();
    fetchHistory();
    fetchLogs();

    const eventSource = new EventSource("/api/youtube/stream");
    eventSource.onmessage = (event) => {
      try {
        const job: ActiveJob = JSON.parse(event.data);
        setActiveJob(job);
        if (!job.is_running && job.percent === 100) {
          fetchStatus();
          fetchHistory();
          fetchLogs();
        }
      } catch (e) {
        console.error("SSE parse error", e);
      }
    };

    const interval = setInterval(() => {
      fetchStatus();
      fetchLogs();
    }, 5000);

    return () => {
      eventSource.close();
      clearInterval(interval);
    };
  }, []);

  const handleSaveConfig = async () => {
    setIsSavingConfig(true);
    setSaveMessage("");
    try {
      const res = await fetch("/api/youtube/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          niche,
          production_mode: productionMode,
          llm_provider: llmProvider,
        }),
      });
      if (res.ok) {
        setSaveMessage("Settings saved successfully.");
        fetchStatus();
      } else {
        setSaveMessage("Failed to save settings.");
      }
    } catch (err) {
      setSaveMessage("Network error saving settings.");
    } finally {
      setIsSavingConfig(false);
      setTimeout(() => setSaveMessage(""), 4000);
    }
  };

  const handleTriggerPipeline = async () => {
    try {
      const res = await fetch("/api/youtube/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          force: forceRun,
          dry_run: dryRun,
          custom_topic: customTopic.trim() || null,
        }),
      });
      if (res.ok) {
        fetchStatus();
      }
    } catch (err) {
      console.error("Error triggering pipeline:", err);
    }
  };

  return (
    <div className="flex flex-1 flex-col h-full bg-[#090a10] text-gray-200 overflow-y-auto p-6 font-sans select-text">
      {/* Top Header Banner */}
      <div className="flex items-center justify-between pb-5 border-b border-indigo-950/60 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-red-600 via-pink-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-red-500/20">
            <Film className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-wider text-white">
                Autonomous YouTube Production Subsystem
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono tracking-widest bg-red-950/60 text-red-400 border border-red-800/60">
                100% CPU / ZERO VRAM
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              Daily Autonomous YouTube Shorts & Podcast Generator (EBU R128 • Ken Burns • Resumable OAuth2)
            </p>
          </div>
        </div>

        {/* Global Pipeline Trigger CTA */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              fetchStatus();
              fetchHistory();
              fetchLogs();
            }}
            className="p-2.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/10 transition-colors"
            title="Refresh Ledger"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={handleTriggerPipeline}
            disabled={activeJob.is_running}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm transition-all shadow-lg ${
              activeJob.is_running
                ? "bg-amber-600/30 text-amber-300 border border-amber-500/40 cursor-not-allowed animate-pulse"
                : "bg-gradient-to-r from-red-600 via-pink-600 to-purple-600 hover:brightness-110 text-white shadow-red-600/30 glow-red"
            }`}
          >
            {activeJob.is_running ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Running ({activeJob.percent}%)</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>Trigger Pipeline Now</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Real-time Progress Bar Card (Visible when active) */}
      <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-900/60 border border-indigo-900/50 backdrop-blur-md shadow-xl">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Radio className={`w-4 h-4 ${activeJob.is_running ? "text-red-400 animate-pulse" : "text-gray-400"}`} />
            <span className="text-xs font-mono uppercase tracking-wider text-gray-300">
              Live Stage: <span className="text-cyan-400 font-bold">{activeJob.current_stage}</span>
            </span>
          </div>
          <span className="text-xs font-mono text-cyan-400 font-semibold">{activeJob.percent}%</span>
        </div>
        
        {/* Progress Track */}
        <div className="w-full h-2.5 bg-gray-900/80 rounded-full overflow-hidden border border-indigo-950">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 via-indigo-500 to-pink-500 transition-all duration-500 rounded-full relative"
            style={{ width: `${Math.max(activeJob.percent, 3)}%` }}
          >
            {activeJob.is_running && (
              <div className="absolute inset-0 bg-white/20 animate-pulse" />
            )}
          </div>
        </div>
        <p className="text-[11px] font-mono text-gray-400 mt-2 truncate">
          {activeJob.detail || "Subsystem standby — awaiting trigger or scheduled boot cycle."}
        </p>
      </div>

      {/* Grid: 3 Main Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Card 1: Today's Status & Idempotency Ledger */}
        <div className="p-5 rounded-2xl bg-[#0e1017] border border-indigo-950/80 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-mono tracking-wider uppercase text-gray-400 flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                Today's Idempotency Gate
              </span>
              {statusData?.today_completed ? (
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/80 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3 h-3" /> Uploaded
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-amber-950/60 text-amber-400 border border-amber-800/80 flex items-center gap-1.5">
                  <Clock className="w-3 h-3" /> Pending Today
                </span>
              )}
            </div>

            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-black/40 border border-white/5">
                <span className="text-[10px] uppercase font-mono text-gray-500">Scheduled Date</span>
                <p className="text-sm font-semibold text-white mt-0.5">{statusData?.today_date || "—"}</p>
              </div>

              {statusData?.today_record ? (
                <div className="p-3 rounded-xl bg-black/40 border border-white/5">
                  <span className="text-[10px] uppercase font-mono text-gray-500">Today's Title</span>
                  <p className="text-xs font-medium text-cyan-300 mt-0.5 line-clamp-2">
                    {statusData.today_record.title}
                  </p>
                  {statusData.today_record.youtube_id && (
                    <a
                      href={`https://www.youtube.com/shorts/${statusData.today_record.youtube_id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-pink-400 hover:text-pink-300 mt-2 font-mono"
                    >
                      <ExternalLink className="w-3 h-3" /> View YouTube Short
                    </a>
                  )}
                </div>
              ) : (
                <div className="p-3 rounded-xl bg-black/40 border border-white/5 text-gray-400 text-xs italic">
                  No video generated for today yet. System will run automatically on startup or via trigger button.
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-[11px] text-gray-400">
            <span>OAuth Token:</span>
            <span className={statusData?.config_summary?.has_oauth_token ? "text-emerald-400" : "text-amber-400"}>
              {statusData?.config_summary?.has_oauth_token ? "● Authorized" : "○ Offline / Dry-Run"}
            </span>
          </div>
        </div>

        {/* Card 2: Production Parameters & AI Niche Control */}
        <div className="p-5 rounded-2xl bg-[#0e1017] border border-indigo-950/80 shadow-xl flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-mono tracking-wider uppercase text-gray-400 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-pink-400" />
              Niche & Format Matrix
            </span>
            <button
              onClick={fetchNiches}
              disabled={isLoadingNiches}
              className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-mono"
            >
              <Sparkles className="w-3 h-3" />
              {isLoadingNiches ? "Consulting..." : "AI Consult"}
            </button>
          </div>

          <div className="space-y-3 flex-1">
            {/* Target Niche */}
            <div>
              <label className="text-[10px] uppercase font-mono text-gray-400">Target Niche</label>
              <input
                type="text"
                value={niche}
                onChange={(e) => setNiche(e.target.value)}
                className="w-full mt-1 px-3 py-2 rounded-lg bg-black/50 border border-indigo-950 text-xs text-white focus:outline-none focus:border-cyan-500"
                placeholder="e.g. AI Innovations & Breakthroughs"
              />
            </div>

            {/* Production Mode */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] uppercase font-mono text-gray-400">Production Mode</label>
                <select
                  value={productionMode}
                  onChange={(e) => setProductionMode(e.target.value)}
                  className="w-full mt-1 px-2.5 py-2 rounded-lg bg-black/50 border border-indigo-950 text-xs text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="solo">solo (1 Narrator)</option>
                  <option value="podcast">podcast (2 Hosts)</option>
                  <option value="alternating">alternating (Daily)</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] uppercase font-mono text-gray-400">LLM Provider</label>
                <select
                  value={llmProvider}
                  onChange={(e) => setLlmProvider(e.target.value)}
                  className="w-full mt-1 px-2.5 py-2 rounded-lg bg-black/50 border border-indigo-950 text-xs text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="gemini">Gemini (Free 15 RPM)</option>
                  <option value="openrouter">OpenRouter Free</option>
                  <option value="ollama">Ollama (CPU Local)</option>
                </select>
              </div>
            </div>

            {/* AI Niches Carousel / Pills */}
            {recommendedNiches.length > 0 && (
              <div className="p-2 rounded-lg bg-black/30 border border-white/5 space-y-1">
                <span className="text-[9px] uppercase font-mono text-gray-400">AI Suggested High-CPM Niches:</span>
                <div className="flex flex-wrap gap-1">
                  {recommendedNiches.map((n, i) => (
                    <button
                      key={i}
                      onClick={() => setNiche(n.name)}
                      className="px-2 py-0.5 rounded text-[10px] bg-indigo-950/70 hover:bg-cyan-950 text-cyan-300 border border-indigo-800/40 transition-colors"
                      title={n.why}
                    >
                      {n.name} ({n.cpm_estimate})
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between">
            <span className="text-[11px] text-emerald-400">{saveMessage}</span>
            <button
              onClick={handleSaveConfig}
              disabled={isSavingConfig}
              className="px-3 py-1.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-200 border border-indigo-500/40 text-xs font-medium transition-colors"
            >
              {isSavingConfig ? "Saving..." : "Save Settings"}
            </button>
          </div>
        </div>

        {/* Card 3: Execution Overrides & Dry-Run Panel */}
        <div className="p-5 rounded-2xl bg-[#0e1017] border border-indigo-950/80 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-mono tracking-wider uppercase text-gray-400 flex items-center gap-2">
                <Layers className="w-4 h-4 text-purple-400" />
                Pipeline Overrides
              </span>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-[10px] uppercase font-mono text-gray-400">
                  Custom Topic Prompt (Optional)
                </label>
                <input
                  type="text"
                  value={customTopic}
                  onChange={(e) => setCustomTopic(e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-lg bg-black/50 border border-indigo-950 text-xs text-white focus:outline-none focus:border-cyan-500"
                  placeholder="Leave empty for AI autonomous topic selection"
                />
              </div>

              <div className="p-3 rounded-xl bg-black/40 border border-white/5 space-y-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-300">
                  <input
                    type="checkbox"
                    checked={forceRun}
                    onChange={(e) => setForceRun(e.target.checked)}
                    className="rounded bg-black border-gray-700 text-cyan-500 focus:ring-0"
                  />
                  <span>Bypass Idempotency (Force upload even if done today)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-300">
                  <input
                    type="checkbox"
                    checked={dryRun}
                    onChange={(e) => setDryRun(e.target.checked)}
                    className="rounded bg-black border-gray-700 text-cyan-500 focus:ring-0"
                  />
                  <span>Dry-Run Mode (Render video without uploading)</span>
                </label>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-white/5 text-[11px] text-gray-400 font-mono">
            Silent Task Scheduler: <span className="text-gray-300">scripts/run_youtube_silent.vbs</span>
          </div>
        </div>
      </div>

      {/* Bottom Split: Recent Uploads Ledger & Live Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-[340px]">
        {/* Uploads History Table */}
        <div className="p-5 rounded-2xl bg-[#0e1017] border border-indigo-950/80 shadow-xl flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-mono tracking-wider uppercase text-gray-400 flex items-center gap-2">
              <Database className="w-4 h-4 text-cyan-400" />
              Upload Ledger (SQLite WAL)
            </span>
            <span className="text-[11px] font-mono text-gray-500">{history.length} records</span>
          </div>

          <div className="flex-1 overflow-y-auto pr-1 space-y-2">
            {history.length === 0 ? (
              <div className="text-center py-12 text-gray-500 text-xs italic">
                No uploads recorded in ledger yet.
              </div>
            ) : (
              history.map((item) => (
                <div
                  key={item.id}
                  className="p-3 rounded-xl bg-black/40 border border-white/5 hover:border-cyan-500/30 transition-colors flex items-center justify-between gap-3"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-gray-400">{item.upload_date}</span>
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-mono uppercase bg-indigo-950 text-indigo-300 border border-indigo-800/40">
                        {item.production_mode}
                      </span>
                      <span
                        className={`text-[9px] font-mono uppercase px-1.5 py-0.2 rounded ${
                          item.status === "COMPLETED"
                            ? "bg-emerald-950 text-emerald-400"
                            : "bg-red-950 text-red-400"
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>
                    <p className="text-xs font-medium text-white truncate mt-1">{item.title}</p>
                    <div className="text-[10px] text-gray-500 flex items-center gap-3 mt-0.5">
                      {item.duration_sec && <span>Duration: {item.duration_sec.toFixed(1)}s</span>}
                      {item.file_size_bytes && (
                        <span>Size: {(item.file_size_bytes / (1024 * 1024)).toFixed(1)} MB</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {item.youtube_id && (
                      <a
                        href={`https://www.youtube.com/shorts/${item.youtube_id}`}
                        target="_blank"
                        rel="noreferrer"
                        className="p-2 rounded-lg bg-red-950/40 hover:bg-red-900/60 text-red-400 hover:text-white border border-red-900/50 transition-colors"
                        title="Watch on YouTube"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Live Structured Execution Telemetry */}
        <div className="p-5 rounded-2xl bg-[#0e1017] border border-indigo-950/80 shadow-xl flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-mono tracking-wider uppercase text-gray-400 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-purple-400" />
              Pipeline Execution Telemetry
            </span>
            <span className="text-[10px] font-mono text-gray-500">Live Structured Logs</span>
          </div>

          <div className="flex-1 overflow-y-auto pr-1 space-y-1.5 font-mono text-[11px] bg-black/60 p-3 rounded-xl border border-indigo-950/60">
            {logs.length === 0 ? (
              <div className="text-gray-500 italic text-center py-10">No execution logs yet.</div>
            ) : (
              logs.map((logItem, idx) => (
                <div key={idx} className="flex items-start gap-2 py-0.5 border-b border-white/5 last:border-none">
                  <span className="text-gray-600 shrink-0 text-[10px]">{logItem.created_at?.slice(11, 19)}</span>
                  <span
                    className={`font-semibold shrink-0 text-[10px] ${
                      logItem.status === "SUCCESS"
                        ? "text-emerald-400"
                        : logItem.status === "RUNNING"
                        ? "text-cyan-400"
                        : "text-red-400"
                    }`}
                  >
                    [{logItem.stage}]
                  </span>
                  <span className="text-gray-300 break-words">{logItem.details}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default YouTubeDashboard;
