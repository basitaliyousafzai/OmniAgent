import React, { useState, useEffect, useRef } from "react";
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
  AlertCircle,
  Crosshair,
  Zap,
  Target,
  Maximize2
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

  // Interactive reticle hover tracking (0-1000)
  const [hoverCoord, setHoverCoord] = useState<{ x: number; y: number } | null>(null);
  const imageContainerRef = useRef<HTMLDivElement>(null);

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
        setTimeout(captureScreen, 600);
      }
    } catch (err) {
      console.error("Focus failed", err);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!imageContainerRef.current) return;
    const rect = imageContainerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(1000, Math.round(((e.clientX - rect.left) / rect.width) * 1000)));
    const y = Math.max(0, Math.min(1000, Math.round(((e.clientY - rect.top) / rect.height) * 1000)));
    setHoverCoord({ x, y });
  };

  const handleMouseLeave = () => {
    setHoverCoord(null);
  };

  const handleImageClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!imageContainerRef.current) return;
    const rect = imageContainerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(1000, Math.round(((e.clientX - rect.left) / rect.width) * 1000)));
    const y = Math.max(0, Math.min(1000, Math.round(((e.clientY - rect.top) / rect.height) * 1000)));
    setManualNormX(x.toString());
    setManualNormY(y.toString());
    setStatusMessage(`Reticle calibrated to: X:${x}, Y:${y}`);
    setTimeout(() => setStatusMessage(null), 2500);
  };

  return (
    <div className="flex-1 h-full bg-[#0b0c12] flex flex-col overflow-y-auto p-4 space-y-4 cyber-scanline">
      {/* View Header with Cyber HUD */}
      <div className="flex items-center justify-between pb-3 border-b border-indigo-900/40">
        <div>
          <h2 className="text-sm font-bold text-gray-200 flex items-center gap-2 font-hud tracking-wide">
            <Monitor className="w-4 h-4 text-cyan-400" />
            <span className="uppercase text-cyan-300">OS Automation & Coordinate Reticle Plane</span>
          </h2>
          <p className="text-xs text-gray-400 font-mono">
            Direct visual coordinate inspection (0-1000 matrix), window targeting, and external software hook
          </p>
        </div>

        {statusMessage && (
          <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 rounded text-xs font-mono animate-pulse">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{statusMessage}</span>
          </div>
        )}
      </div>

      {/* Target Application Preset Quickbar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <button
          onClick={() => handleFocus("devenv")}
          className="p-2.5 rounded-lg bg-[#12141f] hover:bg-purple-950/40 border border-purple-900/50 hover:border-purple-500/80 text-left transition-all flex items-center gap-2.5 group"
        >
          <div className="p-2 rounded bg-purple-600/20 text-purple-400 group-hover:scale-110 transition-transform">
            <Hammer className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-semibold text-gray-200 group-hover:text-purple-300 font-hud">Visual Studio</div>
            <div className="text-[10px] text-gray-500 font-mono">devenv.exe</div>
          </div>
        </button>

        <button
          onClick={() => handleFocus("ssms")}
          className="p-2.5 rounded-lg bg-[#12141f] hover:bg-yellow-950/40 border border-yellow-900/50 hover:border-yellow-500/80 text-left transition-all flex items-center gap-2.5 group"
        >
          <div className="p-2 rounded bg-yellow-600/20 text-yellow-400 group-hover:scale-110 transition-transform">
            <Database className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-semibold text-gray-200 group-hover:text-yellow-300 font-hud">SQL Server SSMS</div>
            <div className="text-[10px] text-gray-500 font-mono">Ssms.exe</div>
          </div>
        </button>

        <button
          onClick={() => handleFocus("chrome")}
          className="p-2.5 rounded-lg bg-[#12141f] hover:bg-cyan-950/40 border border-cyan-900/50 hover:border-cyan-500/80 text-left transition-all flex items-center gap-2.5 group"
        >
          <div className="p-2 rounded bg-cyan-600/20 text-cyan-400 group-hover:scale-110 transition-transform">
            <Globe className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-semibold text-gray-200 group-hover:text-cyan-300 font-hud">Browser Target</div>
            <div className="text-[10px] text-gray-500 font-mono">Chrome / Edge</div>
          </div>
        </button>

        <button
          onClick={() => captureScreen(showGrid)}
          className="p-2.5 rounded-lg bg-[#12141f] hover:bg-emerald-950/40 border border-emerald-900/50 hover:border-emerald-500/80 text-left transition-all flex items-center gap-2.5 group"
        >
          <div className="p-2 rounded bg-emerald-600/20 text-emerald-400 group-hover:scale-110 transition-transform">
            <Camera className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-semibold text-gray-200 group-hover:text-emerald-300 font-hud">Capture Buffer</div>
            <div className="text-[10px] text-gray-500 font-mono">Interactive Desktop</div>
          </div>
        </button>
      </div>

      {/* Main Grid: Left Window Directory & Right Holographic Reticle Screen */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1">
        {/* Left Column: Top-Level Desktop Windows */}
        <div className="bg-[#10121c]/90 border border-indigo-900/40 rounded-xl p-3 flex flex-col space-y-3">
          <div className="flex items-center justify-between pb-1 border-b border-indigo-950">
            <span className="text-xs font-semibold uppercase tracking-wider text-cyan-300 flex items-center gap-1.5 font-hud">
              <Monitor className="w-3.5 h-3.5 text-cyan-400" />
              <span>Discovered OS Windows ({windows.length})</span>
            </span>

            <button
              onClick={loadWindows}
              disabled={loadingWindows}
              className="p-1 text-gray-400 hover:text-cyan-300 transition-colors"
              title="Refresh Windows"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingWindows ? "animate-spin" : ""}`} />
            </button>
          </div>

          <div className="space-y-1.5 max-h-96 overflow-y-auto pr-1">
            {windows.map((win) => (
              <div
                key={win.hwnd}
                className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition-colors ${
                  win.foreground
                    ? "bg-cyan-950/40 border-cyan-500/60 text-cyan-100 shadow-[0_0_12px_rgba(6,182,212,0.15)]"
                    : "bg-[#0d0e15] border-indigo-950 text-gray-300 hover:border-indigo-800"
                }`}
              >
                <div className="flex-1 truncate mr-2">
                  <div className="font-medium truncate flex items-center gap-1.5">
                    {win.foreground && <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping shrink-0" />}
                    <span className="truncate">{win.title}</span>
                  </div>
                  <div className="text-[10px] text-gray-500 font-mono flex items-center gap-2 mt-0.5">
                    <span>PID: {win.pid}</span>
                    <span>Proc: {win.process_name}</span>
                    {win.foreground && <span className="text-cyan-400 font-bold uppercase tracking-wider">[ACTIVE FOREGROUND]</span>}
                  </div>
                </div>

                <button
                  onClick={() => handleFocus(win.title)}
                  className="px-2.5 py-1 bg-indigo-950/80 hover:bg-cyan-600 hover:text-black border border-cyan-800/40 rounded text-[10px] font-mono font-bold transition-colors"
                >
                  FOCUS
                </button>
              </div>
            ))}

            {windows.length === 0 && !loadingWindows && (
              <div className="p-4 text-center text-xs text-gray-500 font-mono">
                No visible top-level windows detected.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Live Screen Capture & Coordinate Reticle */}
        <div className="bg-[#10121c]/90 border border-indigo-900/40 rounded-xl p-3 flex flex-col space-y-3">
          <div className="flex items-center justify-between pb-1 border-b border-indigo-950">
            <span className="text-xs font-semibold uppercase tracking-wider text-cyan-300 flex items-center gap-1.5 font-hud">
              <Crosshair className="w-3.5 h-3.5 text-cyan-400" />
              <span>Interactive Reticle Viewport</span>
            </span>

            <div className="flex items-center gap-2">
              {hoverCoord && (
                <div className="text-[10px] font-mono text-cyan-300 bg-black/60 px-2 py-0.5 rounded border border-cyan-500/40 animate-pulse">
                  X:{hoverCoord.x} Y:{hoverCoord.y}
                </div>
              )}

              <button
                onClick={() => {
                  const next = !showGrid;
                  setShowGrid(next);
                  captureScreen(next);
                }}
                className={`px-2 py-1 rounded text-xs flex items-center gap-1 border transition-colors font-mono ${
                  showGrid
                    ? "bg-cyan-500 text-black font-bold border-cyan-400"
                    : "bg-[#0d0e15] text-gray-400 border-indigo-900/60 hover:text-white"
                }`}
                title="Toggle 0-1000 Coordinate Grid"
              >
                <Grid className="w-3.5 h-3.5" />
                <span>GRID</span>
              </button>

              <button
                onClick={() => captureScreen(showGrid)}
                disabled={loadingScreen}
                className="px-2 py-1 bg-indigo-950/80 hover:bg-indigo-900 text-cyan-300 border border-indigo-800/40 rounded text-xs flex items-center gap-1 transition-colors font-mono"
                title="Capture Fresh Frame"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingScreen ? "animate-spin" : ""}`} />
                <span>SNAP</span>
              </button>
            </div>
          </div>

          {/* Interactive Screen Display with Reticle Crosshairs */}
          <div
            ref={imageContainerRef}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            onClick={handleImageClick}
            className="flex-1 bg-black/80 rounded-lg overflow-hidden border border-indigo-900/40 relative flex items-center justify-center min-h-[260px] cursor-crosshair group select-none"
          >
            {screenshotUrl ? (
              <>
                <img
                  src={screenshotUrl}
                  alt="Desktop Viewport"
                  className="w-full h-full object-contain pointer-events-none"
                />

                {/* Interactive Dynamic Reticle Crosshair */}
                {hoverCoord && (
                  <div
                    className="absolute pointer-events-none transform -translate-x-1/2 -translate-y-1/2 z-20"
                    style={{
                      left: `${hoverCoord.x / 10}%`,
                      top: `${hoverCoord.y / 10}%`
                    }}
                  >
                    <div className="w-8 h-8 rounded-full border border-cyan-400/80 flex items-center justify-center animate-spin-slow">
                      <div className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]" />
                    </div>
                    {/* Reticle Lines */}
                    <div className="absolute top-1/2 left-0 right-0 h-[1px] bg-cyan-400/50 w-12 -translate-x-2" />
                    <div className="absolute left-1/2 top-0 bottom-0 w-[1px] bg-cyan-400/50 h-12 -translate-y-2" />
                  </div>
                )}
              </>
            ) : (
              <div className="text-gray-500 text-xs font-mono flex flex-col items-center gap-2">
                <Camera className="w-8 h-8 text-gray-600 animate-pulse" />
                <span>No frame captured yet. Click SNAP to refresh buffer.</span>
              </div>
            )}
          </div>

          <div className="text-[10px] text-gray-400 font-mono flex items-center justify-between">
            <span>💡 Click anywhere on the viewport to pick normalized coordinates</span>
            <span className="text-cyan-400 font-semibold">COORDS: X:{manualNormX} Y:{manualNormY}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OSControlView;
