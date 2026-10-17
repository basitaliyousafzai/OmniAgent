"""
Sub-Module: Master Tool Registry & Schemas.

Defines the function schemas registered with the LLMs (compatible with
OpenAI, Ollama, Anthropic, OpenRouter, and Grok).
"""
from __future__ import annotations

from typing import Any

MASTER_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "launch_or_focus_app",
            "description": "Launch an external desktop application (e.g., Visual Studio, SSMS, Chrome) or bring its window to the foreground if already running.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name_or_title": {
                        "type": "string",
                        "description": "Name of the executable or title of the window (e.g., 'devenv', 'Ssms', 'Visual Studio', 'SQL Server Management Studio', 'chrome', 'cmd')."
                    }
                },
                "required": ["app_name_or_title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_hotkey",
            "description": "Send keyboard shortcuts to the currently active desktop window (e.g., ['ctrl', 'shift', 'b'] for VS build, ['f5'] for execute query/run, ['ctrl', 's'] for save).",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of keys pressed together in sequence."
                    }
                },
                "required": ["keys"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_mouse_action",
            "description": "Perform mouse clicks or movement on desktop using normalized coordinates (0-1000).",
            "parameters": {
                "type": "object",
                "properties": {
                    "norm_x": {"type": "number", "description": "Normalized X coordinate (0-1000)."},
                    "norm_y": {"type": "number", "description": "Normalized Y coordinate (0-1000)."},
                    "click_type": {
                        "type": "string",
                        "enum": ["left", "right", "double"],
                        "description": "Type of mouse click."
                    }
                },
                "required": ["norm_x", "norm_y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_type_string",
            "description": "Type text into the currently active desktop window (useful for entering SQL queries, code, or search queries).",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The exact string to type."},
                    "press_enter": {"type": "boolean", "description": "Whether to press Enter after typing."}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gui_scroll",
            "description": "Scroll the active window or webpage. Use negative clicks to scroll down (e.g. -5 to scroll down a page), positive clicks to scroll up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "clicks": {
                        "type": "integer",
                        "description": "Number of scroll clicks. Negative for scrolling down (e.g. -5, -8 to view content below), positive for scrolling up."
                    },
                    "norm_x": {
                        "type": "number",
                        "description": "Optional normalized X coordinate (0-1000) to position the mouse before scrolling."
                    },
                    "norm_y": {
                        "type": "number",
                        "description": "Optional normalized Y coordinate (0-1000) to position the mouse before scrolling."
                    }
                },
                "required": ["clicks"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capture_desktop_view",
            "description": "Capture screenshot of current display to inspect the visual state of active desktop applications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "grid": {
                        "type": "boolean",
                        "description": "Whether to overlay a 0-1000 coordinate grid onto the screenshot."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_user_confirmation",
            "description": "Mandatory safety gate. Requests explicit user confirmation before executing any dangerous command or SQL statement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_description": {
                        "type": "string",
                        "description": "Clear explanation of what dangerous action is about to happen."
                    },
                    "exact_command_or_query": {
                        "type": "string",
                        "description": "The exact shell command or SQL query requiring approval."
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": ["MEDIUM", "HIGH", "CRITICAL"],
                        "description": "Risk assessment level."
                    }
                },
                "required": ["action_description", "exact_command_or_query", "risk_level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_shell",
            "description": "Execute a terminal command inside the project directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The exact shell command line."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file within the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Path relative to project root."},
                    "content": {"type": "string", "description": "Full file content."}
                },
                "required": ["relative_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read content from a workspace file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Path relative to project root."}
                },
                "required": ["relative_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories in a workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Path relative to project root (default is '.')."},
                    "recursive": {"type": "boolean", "description": "Whether to list recursively."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a substring or symbol across the workspace files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search for."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "apply_patch",
            "description": "Perform targeted string replacement in a file without overwriting the entire file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Path relative to project root."},
                    "target": {"type": "string", "description": "Exact text chunk to be replaced."},
                    "replacement": {"type": "string", "description": "New replacement text."}
                },
                "required": ["relative_path", "target", "replacement"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "app_action",
            "description": "High-level automation recipe for known applications (Visual Studio, SSMS, Browsers).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_app": {
                        "type": "string",
                        "description": "Target software (e.g. 'visual studio', 'ssms', 'chrome')."
                    },
                    "action": {
                        "type": "string",
                        "description": "Action recipe (e.g. VS: 'build', 'debug', 'errors'; SSMS: 'connect', 'new_query', 'run_query'; Browser: 'open', 'reload')."
                    },
                    "argument": {
                        "type": "string",
                        "description": "Optional payload (e.g. SQL query for SSMS, URL for browser)."
                    }
                },
                "required": ["target_app", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_ui_tree",
            "description": "Inspect the UI accessibility elements (buttons, textboxes, tabs) of the active desktop window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name_or_title": {
                        "type": "string",
                        "description": "Optional title or executable name. If omitted, uses the currently active foreground window."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_ui_element",
            "description": "Click an accessibility element by its visual Name / Title or AutomationId in the target window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "element_name": {"type": "string", "description": "Visual title or name of the button/item (e.g. 'Execute', 'Start', 'OK')."},
                    "control_type": {"type": "string", "description": "Optional control type (e.g. 'Button', 'MenuItem', 'TabItem')."}
                },
                "required": ["element_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_navigate",
            "description": "Navigate to a specific URL in web browser (Chrome, Edge, Firefox). Focuses or launches the browser, creates a new tab, enters the URL, and loads the webpage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The full URL or web address to navigate to (e.g., 'https://github.com/basitaliyousafzai/OmniAgent')."},
                    "browser": {"type": "string", "description": "Browser name (default: 'chrome'). Options: 'chrome', 'msedge', 'firefox'."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ssms_run_query",
            "description": "Execute a SQL query inside SQL Server Management Studio (SSMS). Connects to default server if connect dialog is open, opens query tab, pastes query, and executes with F5. CRITICAL: After execution, you MUST visually inspect the Results grid on screen using capture_desktop_view to extract and report the returned data rows to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The exact SQL statement to execute (e.g. 'USE [soukwears]; SELECT TOP 1 * FROM sales ORDER BY NetTotal DESC;')."},
                    "database": {"type": "string", "description": "Optional target database context (e.g. 'soukwears')."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_learned_skill",
            "description": "Save a newly discovered desktop workflow, successful UI recipe, or operating pattern into the agent's persistent self-learning memory bank.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_intent": {"type": "string", "description": "Clear description of the goal achieved (e.g. 'Navigate to GitHub repo in Chrome')."},
                    "action_sequence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ordered sequence of steps taken."
                    },
                    "key_insights": {"type": "string", "description": "Key takeaways, UI elements, or shortcuts used."}
                },
                "required": ["task_intent", "action_sequence", "key_insights"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_system_volume",
            "description": "Set the master Windows system audio volume to a specific percentage (0 to 100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "percent": {
                        "type": "integer",
                        "description": "Target volume level percentage from 0 (silent/mute) to 100 (max volume)."
                    }
                },
                "required": ["percent"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dismiss_overlay_or_ad",
            "description": "Dynamically detect and dismiss advertisements, cookie consent banners, modal dialogs, or skip buttons on any web page or desktop application using UI Automation and visual detection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_app_or_browser": {
                        "type": "string",
                        "description": "Target application name or browser (default 'chrome')."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "skip_ads",
            "description": "Dynamically detect and dismiss video advertisements, popups, or overlays on web media players.",
            "parameters": {
                "type": "object",
                "properties": {
                    "browser": {
                        "type": "string",
                        "description": "Browser name (default 'chrome')."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wait_and_observe",
            "description": "Wait a specified number of seconds for an asynchronous task, AI generation (Gemini/ChatGPT image or text), webpage rendering, or job to finish, then automatically takes a fresh screenshot to observe the final result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "integer",
                        "description": "Number of seconds to wait (e.g. 5, 8, 10). Default is 6."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for waiting (e.g. 'Waiting for Gemini image generation to complete')."
                    }
                }
            }
        }
    }
]
