import { useEffect, useRef, useState, useCallback } from "react";
import { ApprovalRequestData, ChatMessage, ToolCallData, ToolResultData } from "../types";

export function speakAgentVoice(text: string) {
  if (!text || typeof window === "undefined") return;
  // Strip code fences, json blocks, and technical symbols for clear speech
  const spoken = text
    .replace(/```[\s\S]*?```/g, "Code block executed.")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/[#*_~>]/g, "")
    .trim();
  if (!spoken) return;

  if ("speechSynthesis" in window) {
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(spoken);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(
        (v) =>
          v.lang.startsWith("en") &&
          (v.name.includes("Natural") ||
            v.name.includes("Google") ||
            v.name.includes("Microsoft") ||
            v.name.includes("David") ||
            v.name.includes("Zira"))
      );
      if (preferred) utterance.voice = preferred;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("Speech synthesis notice:", e);
    }
  }
}

export function useAgentSocket() {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalRequestData[]>([]);
  const [streamingThought, setStreamingThought] = useState("");
  const [voiceOutputEnabled, setVoiceOutputEnabled] = useState(true);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const hasGreetedRef = useRef(false);

  const triggerStartupGreeting = useCallback(() => {
    if (hasGreetedRef.current) return;
    hasGreetedRef.current = true;

    const hour = new Date().getHours();
    let timeGreeting = "Good morning";
    if (hour >= 12 && hour < 17) {
      timeGreeting = "Good afternoon";
    } else if (hour >= 17) {
      timeGreeting = "Good evening";
    }

    const greeting = `${timeGreeting}, Operator! OmniAgent OS Sovereign Swarm is online. All 6 autonomous agents are synchronized, desktop automation hooks are active, and Gemini multimodal reasoning is ready. How may I assist your desktop workflow today?`;

    setMessages((prev) => [
      ...prev,
      {
        id: `greeting_${Date.now()}`,
        role: "assistant",
        content: greeting,
        timestamp: Date.now(),
        provider: "gemini",
        model: "gemini-2.5-flash"
      }
    ]);

    // Proactively speak greeting aloud
    setTimeout(() => {
      speakAgentVoice(greeting);
    }, 600);
  }, []);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/agent`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log("Connected to Agent WebSocket");
      triggerStartupGreeting();
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      reconnectTimeoutRef.current = window.setTimeout(connect, 2000);
    };

    ws.onerror = (err) => {
      console.error("Agent WebSocket error", err);
      ws.close();
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const { type, data } = payload;

        switch (type) {
          case "connected":
            console.log("Agent session:", data.session_id);
            break;

          case "agent_start":
            setIsThinking(true);
            setStreamingThought("");
            setCurrentStep(1);
            break;

          case "agent_step":
            setCurrentStep(data.step);
            setStreamingThought("");
            break;

          case "agent_thought_delta":
            setStreamingThought((prev) => prev + data.delta);
            break;

          case "agent_thought":
            setIsThinking(false);
            setStreamingThought("");
            setMessages((prev) => [
              ...prev,
              {
                id: `turn_${Date.now()}_${Math.random()}`,
                role: "assistant",
                content: data.content,
                toolCalls: data.tool_calls,
                timestamp: Date.now(),
                provider: data.provider,
                model: data.model
              }
            ]);

            // Speak agent response aloud if voice output is enabled
            if (voiceOutputEnabled && data.content) {
              speakAgentVoice(data.content);
            }
            break;

          case "tool_call_start":
            break;

          case "tool_call_result":
            setMessages((prev) => {
              const res = data.result as ToolResultData;
              const last = prev[prev.length - 1];
              if (last && last.role === "assistant") {
                const results = last.toolResults ? [...last.toolResults, res] : [res];
                const updated = {
                  ...last,
                  toolResults: results,
                  screenshotUrl: res.screenshot_file ? `/screenshots/${res.screenshot_file}` : last.screenshotUrl
                };
                return [...prev.slice(0, -1), updated];
              } else {
                return [
                  ...prev,
                  {
                    id: `tool_${Date.now()}_${Math.random()}`,
                    role: "tool",
                    content: res.output,
                    toolResults: [res],
                    screenshotUrl: res.screenshot_file ? `/screenshots/${res.screenshot_file}` : undefined,
                    timestamp: Date.now()
                  }
                ];
              }
            });
            break;

          case "approval_required":
            setPendingApprovals((prev) => {
              const existing = prev.find((p) => p.id === data.id);
              if (existing) return prev;
              return [...prev, data as ApprovalRequestData];
            });
            break;

          case "goal_aborted":
            setIsThinking(false);
            setStreamingThought("");
            setMessages((prev) => [
              ...prev,
              {
                id: `aborted_${Date.now()}`,
                role: "system",
                content: "Current operation halted by operator or kill switch.",
                timestamp: Date.now()
              }
            ]);
            break;

          case "error":
            setIsThinking(false);
            setStreamingThought("");
            setMessages((prev) => [
              ...prev,
              {
                id: `err_${Date.now()}`,
                role: "system",
                content: `Error: ${data.error}`,
                timestamp: Date.now()
              }
            ]);
            break;
        }
      } catch (e) {
        console.error("Failed to parse agent message", e);
      }
    };
  }, [triggerStartupGreeting, voiceOutputEnabled]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  const sendGoal = (goal: string, imageB64?: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    
    setMessages((prev) => [
      ...prev,
      {
        id: `user_${Date.now()}`,
        role: "user",
        content: goal,
        screenshotUrl: imageB64 ? `data:image/jpeg;base64,${imageB64}` : undefined,
        timestamp: Date.now()
      }
    ]);
    setIsThinking(true);

    wsRef.current.send(
      JSON.stringify({
        type: "start_goal",
        data: { goal, image_b64: imageB64 }
      })
    );
  };

  const sendApproval = (id: string, approved: boolean, note: string = "") => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(
      JSON.stringify({
        type: "approval_decision",
        data: { id, approved, note }
      })
    );
    setPendingApprovals((prev) => prev.filter((p) => p.id !== id));
  };

  const abortGoal = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "abort_goal" }));
    setIsThinking(false);
  };

  return {
    connected,
    messages,
    isThinking,
    currentStep,
    streamingThought,
    pendingApprovals,
    voiceOutputEnabled,
    setVoiceOutputEnabled,
    sendGoal,
    sendApproval,
    abortGoal,
    setMessages
  };
}

export default useAgentSocket;
