export type RiskLevel = "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface ToolCallData {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface ToolResultData {
  tool_call_id: string;
  name: string;
  ok: boolean;
  output: string;
  image_b64?: string;
  image_mime?: string;
  screenshot_file?: string;
  extra?: Record<string, any>;
}

export interface ApprovalRequestData {
  id: string;
  session_id: string;
  tool_name: string;
  action_description: string;
  exact_command_or_query: string;
  risk_level: RiskLevel;
  reasons: string[];
  created_at: number;
  timeout_seconds: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  toolCalls?: ToolCallData[];
  toolResults?: ToolResultData[];
  screenshotUrl?: string;
  timestamp: number;
  provider?: string;
  model?: string;
}

export interface WindowItem {
  hwnd: number;
  title: string;
  pid: number;
  process_name: string;
  exe: string;
  left: number;
  top: number;
  width: number;
  height: number;
  minimized: boolean;
  foreground: boolean;
}

export interface FileItem {
  name: string;
  is_dir: boolean;
  size: number;
  path: string;
}

export interface AuditEntry {
  ts: number;
  iso: string;
  event: string;
  session_id: string;
  data: Record<string, any>;
}

export interface SystemStatus {
  status: string;
  os: string;
  is_windows: boolean;
  workspace_root: string;
  kill_switch_engaged: boolean;
  kill_switch_hotkey_active: boolean;
  providers: Record<string, { label: string; configured: boolean; default_model: string }>;
  ollama: { online: boolean; models: string[]; base_url: string };
  stt: { loaded: boolean; model: string; loading: boolean };
  tts: { available: boolean; error: string };
}
