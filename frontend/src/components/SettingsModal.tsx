import React, { useState, useEffect } from "react";
import { X, Save, Key, Cpu, Mic, Volume2, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose, onSaved }) => {
  const [provider, setProvider] = useState("openrouter");
  const [model, setModel] = useState("anthropic/claude-3.5-sonnet");
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [keyStatus, setKeyStatus] = useState<Record<string, { configured: boolean; masked: string }>>({});
  const [ollamaUrl, setOllamaUrl] = useState("http://127.0.0.1:11434");
  const [ollamaModel, setOllamaModel] = useState("llama3.1");
  const [ollamaOnline, setOllamaOnline] = useState(false);
  const [availableOllamaModels, setAvailableOllamaModels] = useState<string[]>([]);
  const [tokenBudget, setTokenBudget] = useState(60000);
  const [whisperModel, setWhisperModel] = useState("base");
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const loadSettings = async () => {
    try {
      const res = await fetch("/api/settings");
      if (res.ok) {
        const data = await res.json();
        const s = data.settings || {};
        setProvider(s.provider || "openrouter");
        setModel(s.model || "anthropic/claude-3.5-sonnet");
        setOllamaUrl(s.ollama_base_url || "http://127.0.0.1:11434");
        setOllamaModel(s.ollama_model || "llama3.1");
        setTokenBudget(s.context_token_budget || 60000);
        setWhisperModel(s.whisper_model || "base");
        setKeyStatus(data.key_status || {});
      }

      // Check Ollama status
      const statRes = await fetch("/api/status");
      if (statRes.ok) {
        const statData = await statRes.json();
        if (statData.ollama) {
          setOllamaOnline(statData.ollama.online);
          setAvailableOllamaModels(statData.ollama.models || []);
        }
      }
    } catch (err) {
      console.error("Failed to load settings", err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadSettings();
      setSaveSuccess(false);
    }
  }, [isOpen]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        settings: {
          provider,
          model,
          ollama_base_url: ollamaUrl,
          ollama_model: ollamaModel,
          context_token_budget: tokenBudget,
          whisper_model: whisperModel
        },
        api_keys: apiKeys
      };

      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setSaveSuccess(true);
        setApiKeys({}); // reset input state
        loadSettings();
        if (onSaved) onSaved();
        setTimeout(() => setSaveSuccess(false), 2000);
      }
    } catch (err) {
      console.error("Failed to save settings", err);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-ide-surface border border-ide-border rounded-2xl w-full max-w-xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-fade-in select-none">
        {/* Header */}
        <div className="p-4 border-b border-ide-border flex items-center justify-between bg-ide-surface/50">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-indigo-400" />
            <h3 className="font-bold text-sm text-gray-200">
              OmniAgent Settings & Provider Configuration
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-ide-hover transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-4 overflow-y-auto space-y-5 text-xs text-gray-300">
          {/* Active Model Provider */}
          <div className="space-y-2">
            <label className="font-semibold text-gray-200 block">
              Active LLM Provider
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {[
                { id: "gemini", name: "Google Gemini", model: "gemini-1.5-flash" },
                { id: "openrouter", name: "OpenRouter", model: "anthropic/claude-3.5-sonnet" },
                { id: "anthropic", name: "Anthropic Native", model: "claude-3-5-sonnet-latest" },
                { id: "openai", name: "OpenAI Native", model: "gpt-4o" },
                { id: "xai", name: "xAI (Grok)", model: "grok-2-vision-1212" },
                { id: "ollama", name: "Ollama (Offline)", model: "llama3.1" },
                { id: "vllm", name: "vLLM / LM Studio", model: "default" }
              ].map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => {
                    setProvider(p.id);
                    setModel(p.model);
                  }}
                  className={`p-2.5 rounded-xl border text-left flex flex-col gap-1 transition-all ${
                    provider === p.id
                      ? "bg-indigo-600/20 border-indigo-500 text-indigo-300 font-semibold shadow-md shadow-indigo-500/10"
                      : "bg-[#111217] border-ide-border text-gray-400 hover:border-gray-600"
                  }`}
                >
                  <span className="font-medium text-gray-200">{p.name}</span>
                  <span className="text-[10px] text-gray-500 truncate">{p.model}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Model Name Input */}
          <div className="space-y-1">
            <label className="font-semibold text-gray-300 block">
              Model Identifier / Path
            </label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full bg-[#111217] border border-ide-border rounded-lg p-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* API Keys Vault */}
          <div className="space-y-3 pt-2 border-t border-ide-border/60">
            <div className="flex items-center gap-1.5 font-semibold text-gray-200">
              <Key className="w-4 h-4 text-amber-400" />
              <span>Local Secret Vault (.env.local)</span>
            </div>
            <p className="text-[11px] text-gray-400">
              API keys are stored exclusively on your local computer in ./.env.local. They are never sent to external telemetry.
            </p>

            <div className="space-y-2">
              {[
                { id: "gemini", label: "Google Gemini API Key (FREE from aistudio.google.com)" },
                { id: "openrouter", label: "OpenRouter API Key" },
                { id: "anthropic", label: "Anthropic Claude API Key" },
                { id: "openai", label: "OpenAI API Key" },
                { id: "xai", label: "xAI (Grok) API Key" }
              ].map((k) => (
                <div key={k.id} className="space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-gray-300">{k.label}</span>
                    {keyStatus[k.id]?.configured && (
                      <span className="text-emerald-400 text-[10px] font-mono">
                        Configured: {keyStatus[k.id]?.masked}
                      </span>
                    )}
                  </div>
                  <input
                    type="password"
                    placeholder={keyStatus[k.id]?.configured ? "Leave blank to keep existing key" : "Paste API key..."}
                    value={apiKeys[k.id] || ""}
                    onChange={(e) => setApiKeys({ ...apiKeys, [k.id]: e.target.value })}
                    className="w-full bg-[#111217] border border-ide-border rounded-lg p-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Offline Ollama Settings */}
          <div className="space-y-2 pt-2 border-t border-ide-border/60">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-200">Local Ollama Configuration</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full border ${
                  ollamaOnline
                    ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                    : "bg-red-500/20 text-red-400 border-red-500/30"
                }`}
              >
                {ollamaOnline ? "Online" : "Offline / Not Running"}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[11px] text-gray-400 block mb-1">Ollama Base URL</label>
                <input
                  type="text"
                  value={ollamaUrl}
                  onChange={(e) => setOllamaUrl(e.target.value)}
                  className="w-full bg-[#111217] border border-ide-border rounded-lg p-2 text-xs text-gray-200 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-[11px] text-gray-400 block mb-1">Local Model</label>
                <input
                  type="text"
                  value={ollamaModel}
                  onChange={(e) => setOllamaModel(e.target.value)}
                  className="w-full bg-[#111217] border border-ide-border rounded-lg p-2 text-xs text-gray-200 focus:outline-none"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-ide-border flex items-center justify-between bg-ide-surface/50">
          {saveSuccess ? (
            <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4" />
              <span>Settings and Keys Saved Locally!</span>
            </div>
          ) : (
            <span className="text-[11px] text-gray-500">
              Changes take effect immediately on next agent turn.
            </span>
          )}

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-ide-hover transition-colors text-xs"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg text-xs flex items-center gap-1.5 transition-colors shadow-lg shadow-indigo-600/20"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{saving ? "Saving..." : "Save Settings"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
