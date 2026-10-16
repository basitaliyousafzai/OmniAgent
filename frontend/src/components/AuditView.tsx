import React, { useState, useEffect } from "react";
import { ShieldCheck, RefreshCw, Filter, Clock, AlertTriangle, FileCode } from "lucide-react";
import { AuditEntry } from "../types";

export const AuditView: React.FC = () => {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterEvent, setFilterEvent] = useState<string>("ALL");

  const loadAudit = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/audit?limit=150");
      if (res.ok) {
        const data = await res.json();
        setEntries(data.reverse()); // most recent first
      }
    } catch (err) {
      console.error("Failed to load audit logs", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAudit();
  }, []);

  const filtered = entries.filter((e) => {
    if (filterEvent === "ALL") return true;
    return e.event.toLowerCase().includes(filterEvent.toLowerCase());
  });

  const getEventBadge = (event: string) => {
    if (event.includes("approval")) {
      return "bg-amber-500/20 text-amber-300 border-amber-500/30";
    }
    if (event.includes("kill_switch")) {
      return "bg-red-500/20 text-red-300 border-red-500/30";
    }
    if (event.includes("failover")) {
      return "bg-purple-500/20 text-purple-300 border-purple-500/30";
    }
    if (event.includes("tool")) {
      return "bg-blue-500/20 text-blue-300 border-blue-500/30";
    }
    return "bg-gray-500/20 text-gray-300 border-gray-500/30";
  };

  return (
    <div className="flex-1 h-full bg-ide-bg flex flex-col p-4 space-y-4 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-ide-border">
        <div>
          <h2 className="text-sm font-bold text-gray-200 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Safety, Sandbox & Audit Fabric</span>
          </h2>
          <p className="text-xs text-gray-400">
            Chronological audit journal recording every tool execution, risk verdict, and human confirmation
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Event Filter */}
          <select
            value={filterEvent}
            onChange={(e) => setFilterEvent(e.target.value)}
            className="bg-ide-surface border border-ide-border rounded-lg px-2.5 py-1 text-xs text-gray-300 focus:outline-none"
          >
            <option value="ALL">All Events</option>
            <option value="approval">Approvals</option>
            <option value="tool">Tool Executions</option>
            <option value="shell">Shell Commands</option>
            <option value="kill_switch">Kill Switch</option>
            <option value="failover">Provider Failovers</option>
          </select>

          <button
            onClick={loadAudit}
            disabled={loading}
            className="p-1.5 rounded-lg bg-ide-surface hover:bg-ide-hover border border-ide-border text-gray-300 text-xs flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Audit Log Table / Cards */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {filtered.map((entry, index) => (
          <div
            key={index}
            className="bg-ide-surface/60 border border-ide-border/80 rounded-xl p-3 flex flex-col gap-1.5 text-xs hover:border-gray-600 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border uppercase ${getEventBadge(entry.event)}`}>
                  {entry.event}
                </span>
                {entry.session_id && (
                  <span className="text-[10px] text-gray-500 font-mono">
                    Session: {entry.session_id}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1 text-[11px] text-gray-500">
                <Clock className="w-3 h-3" />
                <span>{entry.iso}</span>
              </div>
            </div>

            {/* Audit Payload Data */}
            <div className="bg-[#111217] rounded-lg p-2 font-mono text-[11px] text-gray-300 overflow-x-auto select-text border border-ide-border/40">
              <pre>{JSON.stringify(entry.data, null, 2)}</pre>
            </div>
          </div>
        ))}

        {filtered.length === 0 && !loading && (
          <div className="p-8 text-center text-xs text-gray-500">
            No audit log entries matching the selected filter.
          </div>
        )}
      </div>
    </div>
  );
};
