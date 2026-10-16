import { useEffect, useRef, useState, useCallback } from "react";
import { ApprovalRequestData, ChatMessage, ToolCallData, ToolResultData } from "../types";

export function useAgentSocket() {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalRequestData[]>([]);
  const [streamingThought, setStreamingThought] = useState("");
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/agent`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log("Connected to Agent WebSocket");
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      // Auto-reconnect after 2 seconds
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
            break;

          case "tool_call_start":
            // Tool invocation started
            break;

          case "tool_call_result":
            setMessages((prev) => {
              const res = data.result as ToolResultData;
              // Check if we should attach to previous assistant message
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
                    id: `tool_${Date.now()}`,
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

          case "approval_request":
            setPendingApprovals((prev) => {
              const req = data as ApprovalRequestData;
              if (prev.some((p) => p.id === req.id)) return prev;
              return [...prev, req];
            });
            break;

          case "approval_resolved":
            setPendingApprovals((prev) => prev.filter((p) => p.id !== data.id));
            break;

          case "agent_done":
            setIsThinking(false);
            break;

          case "agent_cancelled":
            setIsThinking(false);
            setMessages((prev) => [
              ...prev,
              {
                id: `cancel_${Date.now()}`,
                role: "system",
                content: "Operation was aborted.",
                timestamp: Date.now()
              }
            ]);
            break;

          case "agent_error":
            setIsThinking(false);
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
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  const sendGoal = (goal: string, imageB64?: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    
    // Append user turn immediately
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
    sendGoal,
    sendApproval,
    abortGoal,
    setMessages
  };
}
