import React, { useState, useEffect } from "react";
import Editor from "@monaco-editor/react";
import { Save, Check, FileCode, X } from "lucide-react";

interface MonacoEditorProps {
  filePath: string | null;
  onClose?: () => void;
}

export const MonacoEditor: React.FC<MonacoEditorProps> = ({ filePath, onClose }) => {
  const [content, setContent] = useState<string>("");
  const [originalContent, setOriginalContent] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  // Detect language by extension
  const getLanguage = (path: string | null) => {
    if (!path) return "plaintext";
    const ext = path.split(".").pop()?.toLowerCase();
    switch (ext) {
      case "ts":
      case "tsx":
        return "typescript";
      case "js":
      case "jsx":
        return "javascript";
      case "py":
        return "python";
      case "sql":
        return "sql";
      case "json":
        return "json";
      case "html":
        return "html";
      case "css":
        return "css";
      case "md":
        return "markdown";
      case "cs":
        return "csharp";
      case "bat":
      case "cmd":
        return "bat";
      case "ps1":
        return "powershell";
      case "sh":
        return "shell";
      default:
        return "plaintext";
    }
  };

  const loadFile = async (path: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/files/read?path=${encodeURIComponent(path)}`);
      if (res.ok) {
        const data = await res.json();
        setContent(data.content || "");
        setOriginalContent(data.content || "");
      }
    } catch (err) {
      console.error("Failed to read file", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (filePath) {
      loadFile(filePath);
    } else {
      setContent("");
      setOriginalContent("");
    }
  }, [filePath]);

  const handleSave = async () => {
    if (!filePath || saving) return;
    setSaving(true);
    try {
      const res = await fetch("/api/files/write", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: filePath, content })
      });
      if (res.ok) {
        setOriginalContent(content);
        setSavedSuccess(true);
        setTimeout(() => setSavedSuccess(false), 2000);
      }
    } catch (err) {
      console.error("Failed to save file", err);
    } finally {
      setSaving(false);
    }
  };

  // Keyboard shortcut Ctrl+S
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [content, filePath]);

  const isDirty = content !== originalContent;

  if (!filePath) {
    return (
      <div className="flex-1 h-full bg-ide-bg flex flex-col items-center justify-center text-gray-500 select-none">
        <FileCode className="w-12 h-12 text-gray-600 mb-3" />
        <p className="text-sm">Select a file from the Explorer to edit code</p>
      </div>
    );
  }

  return (
    <div className="flex-1 h-full flex flex-col bg-ide-bg">
      {/* Editor Tab Bar */}
      <div className="h-9 bg-ide-sidebar border-b border-ide-border flex items-center justify-between px-3">
        <div className="flex items-center gap-2 text-xs font-medium text-gray-200">
          <FileCode className="w-4 h-4 text-indigo-400" />
          <span className="truncate">{filePath}</span>
          {isDirty && <span className="w-2 h-2 rounded-full bg-amber-400" title="Unsaved changes" />}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            disabled={saving || !isDirty}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs transition-colors ${
              isDirty
                ? "bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
                : "bg-ide-surface/60 text-gray-400 hover:text-white"
            }`}
            title="Save File (Ctrl+S)"
          >
            {savedSuccess ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400">Saved</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                <span>Save</span>
              </>
            )}
          </button>

          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded text-gray-400 hover:text-white hover:bg-ide-hover"
              title="Close Tab"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Editor Main Surface */}
      <div className="flex-1 relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-ide-bg/80 z-10 text-gray-400 text-xs">
            Loading file content...
          </div>
        ) : (
          <Editor
            height="100%"
            language={getLanguage(filePath)}
            theme="vs-dark"
            value={content}
            onChange={(val) => setContent(val || "")}
            options={{
              fontSize: 13,
              fontFamily: "JetBrains Mono, Consolas, monospace",
              minimap: { enabled: true },
              automaticLayout: true,
              scrollBeyondLastLine: false,
              wordWrap: "on",
              padding: { top: 12, bottom: 12 }
            }}
          />
        )}
      </div>
    </div>
  );
};
