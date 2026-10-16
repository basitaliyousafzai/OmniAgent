import React, { useState, useEffect } from "react";
import { Folder, FolderOpen, FileCode, RefreshCw, Search, FileText } from "lucide-react";
import { FileItem } from "../types";

interface FileExplorerProps {
  onSelectFile: (path: string) => void;
  selectedFile: string | null;
}

export const FileExplorer: React.FC<FileExplorerProps> = ({ onSelectFile, selectedFile }) => {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const loadFiles = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/files/tree?recursive=true");
      if (res.ok) {
        const data = await res.json();
        setFiles(data.items || []);
      }
    } catch (err) {
      console.error("Failed to load file tree:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFiles();
  }, []);

  const filtered = files.filter((f) =>
    f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="w-64 h-full bg-ide-sidebar border-r border-ide-border flex flex-col text-sm select-none">
      {/* Explorer Header */}
      <div className="p-3 border-b border-ide-border flex items-center justify-between">
        <span className="font-semibold text-xs tracking-wider uppercase text-gray-400">
          Workspace Files
        </span>
        <button
          onClick={loadFiles}
          disabled={loading}
          className="p-1 rounded hover:bg-ide-hover text-gray-400 hover:text-white transition-colors"
          title="Reload Files"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Filter Input */}
      <div className="p-2 border-b border-ide-border/50">
        <div className="relative flex items-center">
          <Search className="w-3.5 h-3.5 absolute left-2.5 text-gray-400" />
          <input
            type="text"
            placeholder="Search files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-ide-surface/60 border border-ide-border/60 rounded px-2.5 py-1 pl-8 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500/80 transition-colors"
          />
        </div>
      </div>

      {/* File Tree List */}
      <div className="flex-1 overflow-y-auto p-1 space-y-0.5">
        {filtered.map((item) => {
          const isSelected = selectedFile === item.path;
          return (
            <div
              key={item.path}
              onClick={() => {
                if (!item.is_dir) onSelectFile(item.path);
              }}
              className={`flex items-center gap-2 px-2.5 py-1.5 rounded cursor-pointer transition-colors text-xs ${
                isSelected
                  ? "bg-ide-accent/20 text-indigo-300 font-medium"
                  : "text-gray-300 hover:bg-ide-hover hover:text-white"
              } ${item.is_dir ? "text-gray-400 font-semibold mt-1" : ""}`}
            >
              {item.is_dir ? (
                <Folder className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              ) : (
                <FileCode className="w-3.5 h-3.5 text-blue-400 shrink-0" />
              )}
              <span className="truncate" title={item.path}>
                {item.name}
              </span>
            </div>
          );
        })}

        {filtered.length === 0 && !loading && (
          <div className="p-4 text-center text-xs text-gray-500">
            No files found matching criteria.
          </div>
        )}
      </div>
    </div>
  );
};
