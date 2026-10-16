import React, { useEffect, useRef } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { Terminal as TerminalIcon, RefreshCw, Trash2 } from "lucide-react";

export const TerminalView: React.FC = () => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const initTerminal = () => {
    if (!terminalRef.current) return;

    // Teardown previous if existing
    if (xtermRef.current) {
      xtermRef.current.dispose();
      xtermRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const term = new Terminal({
      cursorBlink: true,
      fontFamily: "JetBrains Mono, Fira Code, Consolas, monospace",
      fontSize: 13,
      lineHeight: 1.2,
      theme: {
        background: "#111217",
        foreground: "#cbd5e1",
        cursor: "#818cf8",
        selectionBackground: "#3730a3",
        black: "#1e293b",
        red: "#f87171",
        green: "#4ade80",
        yellow: "#facc15",
        blue: "#60a5fa",
        magenta: "#c084fc",
        cyan: "#38bdf8",
        white: "#f8fafc"
      }
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Connect to WebSocket /ws/terminal
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/terminal`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "output" && payload.data) {
          term.write(payload.data);
        }
      } catch {
        term.write(event.data);
      }
    };

    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "input", data }));
      }
    });

    term.writeln("\x1b[1;35m OmniAgent OS Interactive Terminal (PTY Session) \x1b[0m");
    term.writeln("\x1b[90m Connected to native workspace shell \x1b[0m\r\n");
  };

  useEffect(() => {
    initTerminal();

    const handleResize = () => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit();
      }
    };

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      if (wsRef.current) wsRef.current.close();
      if (xtermRef.current) xtermRef.current.dispose();
    };
  }, []);

  const clearTerminal = () => {
    if (xtermRef.current) {
      xtermRef.current.clear();
    }
  };

  return (
    <div className="flex-1 h-full bg-ide-bg flex flex-col">
      {/* Terminal Header */}
      <div className="h-9 bg-ide-sidebar border-b border-ide-border flex items-center justify-between px-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-gray-300 uppercase tracking-wider">
          <TerminalIcon className="w-4 h-4 text-emerald-400" />
          <span>Integrated Terminal Multiplexer</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={clearTerminal}
            className="p-1 rounded text-gray-400 hover:text-white hover:bg-ide-hover"
            title="Clear Console"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={initTerminal}
            className="p-1 rounded text-gray-400 hover:text-white hover:bg-ide-hover"
            title="Restart Session"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Terminal Viewport */}
      <div className="flex-1 p-2 bg-[#111217] overflow-hidden" ref={terminalRef} />
    </div>
  );
};
