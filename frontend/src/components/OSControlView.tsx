import React, { useState, useEffect } from "react";
import { 
  Monitor, 
  ExternalLink, 
  RefreshCw, 
  Play, 
  Hammer, 
  Database, 
  Globe, 
  Camera, 
  Grid, 
  MousePointer, 
  Keyboard, 
  CheckCircle2, 
  AlertCircle 
} from "lucide-react";
import { WindowItem } from "../types";

export const OSControlView: React.FC = () => {
  const [windows, setWindows] = useState<WindowItem[]>([]);
  const [loadingWindows, setLoadingWindows] = useState(false);
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [loadingScreen, setLoadingScreen] = useState(false);
  const [showGrid, setShowGrid] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Manual input testing states
  const [manualText, setManualText] = useState("");
  const [manualNormX, setManualNormX] = useState("500");
  const [manualNormY, setManualNormY] = useState("500");

  const loadWindows = async () => {
    setLoadingWindows(true);
    try {
      const res = await fetch("/api/windows");
      if (res.ok) {
        const data = await res.json();
        setWindows(data);
      }
    } catch (err) {
      console.error("Failed to load windows", err);
    } finally {
      setLoadingWindows(false);
    }
  };

  const captureScreen = async (grid: boolean = showGrid) => {
    setLoadingScreen(true);
    try {
      const res = await fetch(`/api/screenshot?grid=${grid}`);
      if (res.ok) {
        const data = await res.json();
        setScreenshotUrl(data.url);
      }
    } catch (err) {
      console.error("Failed to capture screenshot", err);
    } finally {
      setLoadingScreen(false);
    }
  };

  useEffect(() => {
    loadWindows();
    captureScreen();
  }, []);

  const handleFocus = async (target: string) => {
    try {
      const res = await fetch("/api/windows/focus", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target })
      });
      if (res.ok) {
        setStatusMessage(`Focused: ${target}`);
        setTimeout(() => setStatusMessage(null), 3000);
        loadWindows();
        setTimeout(captureScreen, 500);
      }
    } catch (err) {
      console.error("Focus failed", err);
    }
  };

  return (
    <div className="flex-1 h-full bg-ide-bg flex flex-col overflow-y-auto p-4 space-y-4">
      {/* View Header */}
      <div className="flex items-center justify-between pb-3 border-b border-ide-border">
        <div>
          <h2 className="text-sm font-bold text-gray-200 flex items-center gap-2">
            <Monitor className="w-4 h-4 text-indigo-400" />
            <span>Active External Window Control Monitor</span>
          </h2>
          <p className="text-xs text-gray-400">
            Inspect, focus, and automate Visual Studio, SSMS, Browsers, and desktop software
          </p>
        </div>

        {statusMessage && (
          <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{statusMessage}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Column: Running Desktop Applications */}
        <div className="bg-ide-surface/60 border border-ide-border rounded-xl p-3 flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-300">
              Running Desktop Windows
            </span>
            <button
              onClick={loadWindows}
              disabled={loadingWindows}
              className="p-1 rounded text-gray-400 hover:text-white hover:bg-ide-hover"
              title="Refresh Windows"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingWindows ? "animate-spin" : ""}`} />
            </button>
          </div>

          <div className="space-y-1.5 max-h-80 overflow-y-auto">
            {windows.map((win) => (
              <div
                key={win.hwnd}
                className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition-colors ${
                  win.foreground
                    ? "bg-indigo-950/40 border-indigo-500/50 text-indigo-200"
                    : "bg-[#111217] border-ide-border text-gray-300 hover:border-gray-600"
                }`}
              >
                <div className="flex-1 truncate mr-2">
                  <div className="font-medium truncate flex items-center gap-1.5">
                    {win.foreground && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />}
                    <span className="truncate">{win.title}</span>
                  </div>
                  <div className="text-[10px] text-gray-500 flex items-center gap-2 mt-0.5">
                    <span>Process: {win.process_name}</span>
                    <span>PID: {win.pid}</span>
                  </div>
                </div>

                <button
                  onClick={() => handleFocus(win.title)}
                  className="px-2.5 py-1 bg-ide-surface hover:bg-indigo-600 hover:text-white border border-ide-border rounded text-[11px] font-medium transition-colors"
                >
                  Focus
                </button>
              </div>
            ))}

            {windows.length === 0 && !loadingWindows && (
              <div className="p-4 text-center text-xs text-gray-500">
                No visible top-level windows detected.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Live Screen Capture & Coordinate Mapper */}
        <div className="bg-ide-surface/60 border border-ide-border rounded-xl p-3 flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
              <Camera className="w-3.5 h-3.5 text-indigo-400" />
              <span>Live Display View</span>
            </span>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  const next = !showGrid;
                  setShowGrid(next);
                  captureScreen(next);
                }}
                className={`px-2 py-1 rounded text-xs flex items-center gap-1 border transition-colors ${
                  showGrid
                    ? "bg-indigo-600 text-white border-indigo-500"
                    : "bg-[#111217] text-gray-400 border-ide-border hover:text-white"
                }`}
                title="Toggle 0-1000 Coordinate Grid"
              >
                <Grid className="w-3.5 h-3.5" />
                <span>Grid</span>
              </button>

              <button
                onClick={() => captureScreen(showGrid)}
                disabled={loadingScreen}
                className="px-2 py-1 bg-ide-surface hover:bg-ide-hover border border-ide-border rounded text-xs text-gray-300 flex items-center gap-1"
                title="Capture Fresh Screenshot"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingScreen ? "animate-spin" : ""}`} />
                <span>Refresh</span>
              </button>
            </div>
          </div>

          <div className="bg-[#111217] rounded-lg border border-ide-border overflow-hidden relative flex items-center justify-center min-h-64">
            {screenshotUrl ? (
              <img
                src={screenshotUrl}
                alt="Live Display"
                className="w-full h-auto object-contain max-h-96"
              />
            ) : (
              <div className="text-xs text-gray-500 flex flex-col items-center gap-2">
                <Camera className="w-8 h-8 text-gray-600" />
                <span>No screenshot available</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
