"""
Sub-Module 6.1: Destructive Command & Query Interceptor.

Every tool call produced by the reasoning engine is inspected here BEFORE it is
executed. The interceptor classifies shell commands, SQL statements, typed GUI
text, file writes and application launches into risk levels. Anything rated
MEDIUM or above is routed to the human approval gate; anything flagged as
`blocked` is refused outright (e.g. file access outside the workspace sandbox).
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from config import WORKSPACE_ROOT, PROJECT_ROOT
from schemas import GuardrailMatch, RiskAssessment, RiskLevel

_FLAGS = re.IGNORECASE | re.MULTILINE


@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: str
    level: RiskLevel
    pattern: re.Pattern[str]
    description: str


def _r(rule_id: str, category: str, level: RiskLevel, pattern: str, description: str) -> Rule:
    return Rule(rule_id, category, level, re.compile(pattern, _FLAGS), description)


C, H, M, L = RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW

# --------------------------------------------------------------------------- #
# Shell / OS command rules
# --------------------------------------------------------------------------- #
SHELL_RULES: tuple[Rule, ...] = (
    # Recursive / forced deletion
    _r("sh.rm_rf", "filesystem", C, r"\brm\s+(?:-[a-z]*r[a-z]*f[a-z]*|-[a-z]*f[a-z]*r[a-z]*|(?:-[a-z]*r[a-z]*\s+-[a-z]*f)|(?:-[a-z]*f[a-z]*\s+-[a-z]*r)|--recursive\s+--force|--force\s+--recursive)\b",
       "Recursive forced deletion (rm -rf)"),
    _r("sh.rm_recursive", "filesystem", H, r"\brm\s+(?:-[a-z]*r[a-z]*|--recursive)\b", "Recursive deletion (rm -r)"),
    _r("sh.rm", "filesystem", M, r"(?:^|[;&|]\s*|\b)rm\s+(?!-)\S", "File deletion (rm)"),
    _r("sh.del_sq", "filesystem", H, r"\b(?:del|erase)\b[^\n]*\s/[sqf]\b", "Forced/recursive deletion (del /s /q /f)"),
    _r("sh.del", "filesystem", M, r"(?:^|[;&|]\s*)(?:del|erase)\s+\S", "File deletion (del)"),
    _r("sh.rmdir_s", "filesystem", H, r"\b(?:rmdir|rd)\b[^\n]*\s/s\b", "Recursive directory removal (rmdir /s)"),
    _r("sh.remove_item_recurse", "filesystem", H, r"\bRemove-Item\b[^\n]*-(?:Recurse|r)\b", "Recursive deletion (Remove-Item -Recurse)"),
    _r("sh.remove_item", "filesystem", M, r"\bRemove-Item\b", "File deletion (Remove-Item)"),
    _r("sh.drive_root_wipe", "filesystem", C, r"(?:\brm\b|\bdel\b|\bRemove-Item\b|\brd\b|\brmdir\b)[^\n]*(?:\s|[\"'])(?:[a-z]:\\\*?|[a-z]:/\*?|/\*?|~/?\*?)(?:[\"']|\s|$)",
       "Deletion targeting a drive root, filesystem root or home directory"),
    _r("sh.shred", "filesystem", C, r"\b(?:shred|sdelete|sdelete64)\b|\bcipher(?:\.exe)?\s+/w\b", "Secure wipe of data (shred/sdelete/cipher /w)"),
    _r("sh.git_clean", "filesystem", M, r"\bgit\s+clean\s+-[a-z]*f", "git clean -f permanently deletes untracked files"),
    _r("sh.git_reset_hard", "filesystem", M, r"\bgit\s+reset\s+--hard\b", "git reset --hard discards local changes"),
    _r("sh.git_force_push", "filesystem", M, r"\bgit\s+push\b[^\n]*(?:--force\b|\s-f\b|--force-with-lease)", "git force push rewrites remote history"),
    # Disk / partition
    _r("sh.format", "disk", C, r"\bformat(?:\.com)?\s+[a-z]:", "Disk format command"),
    _r("sh.diskpart", "disk", C, r"\bdiskpart\b", "Disk partition tool (diskpart)"),
    _r("sh.ps_disk", "disk", C, r"\b(?:Format-Volume|Clear-Disk|Initialize-Disk|Remove-Partition|New-Partition|Resize-Partition|Set-Disk)\b",
       "PowerShell disk/partition cmdlet"),
    _r("sh.mkfs", "disk", C, r"\b(?:mkfs(?:\.\w+)?|fdisk|parted|gdisk|wipefs)\b", "Filesystem/partition tool"),
    _r("sh.dd", "disk", C, r"\bdd\s+[^\n]*\bof=", "Raw block device write (dd of=)"),
    _r("sh.dev_write", "disk", C, r">\s*/dev/(?:sd[a-z]|nvme|hd[a-z]|disk)", "Redirect output onto a raw disk device"),
    _r("sh.shadow_delete", "disk", C, r"\bvssadmin\b[^\n]*\bdelete\b|\bwmic\b[^\n]*shadowcopy[^\n]*delete|\bwbadmin\b[^\n]*\bdelete\b",
       "Deletion of shadow copies / backups"),
    # Registry
    _r("sh.reg_cmd", "registry", H, r"\breg(?:\.exe)?\s+(?:add|delete|import|restore|load|unload|copy)\b", "Registry modification (reg add/delete/import)"),
    _r("sh.regedit_silent", "registry", H, r"\bregedit(?:\.exe)?\s+/s\b", "Silent registry import (regedit /s)"),
    _r("sh.ps_registry", "registry", H, r"\b(?:Set-ItemProperty|New-ItemProperty|Remove-ItemProperty|Rename-ItemProperty|New-Item|Remove-Item|Set-Item)\b[^\n]*\b(?:HKLM|HKCU|HKCR|HKU|HKCC|Registry::)",
       "PowerShell registry modification"),
    # System / boot / drivers
    _r("sh.hosts_write", "system", H, r"(?:drivers[\\/]etc[\\/]hosts|/etc/hosts)[^\n]*|(?:>|Add-Content|Set-Content|Out-File|tee)[^\n]*(?:drivers[\\/]etc[\\/]hosts|/etc/hosts)",
       "Access to the system hosts file"),
    _r("sh.boot", "system", C, r"\b(?:bcdedit|bootrec|bcdboot)\b", "Boot configuration modification"),
    _r("sh.drivers", "system", H, r"\bpnputil\b|\bsc(?:\.exe)?\s+(?:create|delete|config)\b|\\System32\\drivers\\", "Driver / service modification"),
    _r("sh.system_dir_write", "system", H,
       r"(?:\b(?:del|erase|rm|Remove-Item|Move-Item|Copy-Item|Set-Content|Add-Content|Out-File|ren|move|copy|xcopy|robocopy)\b|>)[^\n]*(?:[a-z]:\\Windows\b|\\System32\b|[a-z]:\\Program Files)",
       "Write/delete inside Windows system directories"),
    _r("sh.shutdown", "system", H, r"\bshutdown(?:\.exe)?\b|\b(?:Restart|Stop)-Computer\b|\breboot\b|\bpoweroff\b|\bhalt\b", "System shutdown / restart"),
    _r("sh.exec_policy", "security", M, r"\bSet-ExecutionPolicy\b", "PowerShell execution policy change"),
    _r("sh.fork_bomb", "system", C, r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "Fork bomb"),
    # Processes
    _r("sh.kill_critical", "process", C,
       r"\b(?:taskkill|Stop-Process|kill|pkill|killall|wmic\s+process)\b[^\n]*\b(?:csrss|lsass|winlogon|wininit|smss|services|svchost|explorer|system|init|systemd|launchd)\b",
       "Termination of a critical system process"),
    _r("sh.kill", "process", M, r"\b(?:taskkill|Stop-Process|pkill|killall)\b|(?:^|[;&|]\s*)kill\s+-?\d", "Process termination"),
    # Network / security
    _r("sh.firewall", "network", H, r"\bnetsh\s+(?:adv)?firewall\b|\b(?:New|Set|Remove|Disable|Enable)-NetFirewall\w*\b|\b(?:iptables|ip6tables|ufw|firewall-cmd|nft)\b",
       "Firewall rule modification"),
    _r("sh.defender", "security", H, r"\b(?:Set|Add|Remove)-MpPreference\b", "Windows Defender configuration change"),
    _r("sh.download_exec_pipe", "network", C,
       r"(?:\b(?:iwr|irm|Invoke-WebRequest|Invoke-RestMethod|curl|wget)\b[^\n]*\|\s*(?:iex|Invoke-Expression|sh|bash|zsh|python\d?|powershell|pwsh))|\biex\s*\(?[^\n]*(?:DownloadString|DownloadFile|iwr|Invoke-WebRequest)",
       "Download-and-execute of remote code"),
    _r("sh.download_binary", "network", H,
       r"\b(?:iwr|Invoke-WebRequest|curl|wget|Start-BitsTransfer|certutil(?:\.exe)?\s+-urlcache|bitsadmin)\b[^\n]*\.(?:exe|msi|scr|bat|cmd|ps1|vbs|dll|com|jar)\b",
       "Download of an executable file"),
    _r("sh.users", "security", H,
       r"\bnet\s+(?:user|localgroup)\b[^\n]*(?:/add|/delete|administrators)|\b(?:New|Remove|Set)-LocalUser\b|\bAdd-LocalGroupMember\b|\buseradd\b|\buserdel\b|\bpasswd\b",
       "User account / group modification"),
    _r("sh.permissions", "security", H, r"\bicacls\b[^\n]*/(?:grant|reset|setowner)|\btakeown\b|\bchmod\s+-R\s+0?777\b|\bchown\s+-R\b", "Bulk permission / ownership change"),
)

# --------------------------------------------------------------------------- #
# SQL rules (applied to normalized, upper-cased statements)
# --------------------------------------------------------------------------- #
SQL_RULES: tuple[Rule, ...] = (
    _r("sql.drop_database", "sql", C, r"\bDROP\s+DATABASE\b", "DROP DATABASE"),
    _r("sql.drop_table", "sql", H, r"\bDROP\s+TABLE\b", "DROP TABLE"),
    _r("sql.drop_schema", "sql", H, r"\bDROP\s+SCHEMA\b", "DROP SCHEMA"),
    _r("sql.drop_security", "sql", H, r"\bDROP\s+(?:LOGIN|USER|ROLE|CERTIFICATE|ASYMMETRIC\s+KEY|MASTER\s+KEY)\b", "DROP of a security principal / key"),
    _r("sql.drop_object", "sql", M, r"\bDROP\s+(?:VIEW|PROCEDURE|PROC|FUNCTION|TRIGGER|INDEX|SEQUENCE|TYPE|SYNONYM|STATISTICS|PARTITION)\b", "DROP of a database object"),
    _r("sql.truncate", "sql", H, r"\bTRUNCATE\s+TABLE\b|\bTRUNCATE\s+(?!TABLE)[\w\[\]\".`]+", "TRUNCATE TABLE"),
    _r("sql.alter_drop", "sql", H, r"\bALTER\s+TABLE\b[^;]*\bDROP\b", "ALTER TABLE ... DROP"),
    _r("sql.alter_database", "sql", H, r"\bALTER\s+DATABASE\b[^;]*\b(?:SET\s+(?:OFFLINE|SINGLE_USER|EMERGENCY|READ_ONLY)|REMOVE\s+FILE|MODIFY\s+NAME|COLLATE)\b",
       "ALTER DATABASE state/structure change"),
    _r("sql.restore", "sql", H, r"\bRESTORE\s+(?:DATABASE|LOG)\b", "RESTORE DATABASE overwrites data"),
    _r("sql.detach", "sql", H, r"\bSP_DETACH_DB\b", "Database detach"),
    _r("sql.shutdown", "sql", C, r"(?:^|;)\s*SHUTDOWN\b", "SQL Server SHUTDOWN"),
    _r("sql.xp_cmdshell", "sql", C, r"\bXP_CMDSHELL\b", "xp_cmdshell executes OS commands"),
    _r("sql.sp_configure", "sql", H, r"\bSP_CONFIGURE\b|\bRECONFIGURE\b", "Server configuration change"),
    _r("sql.dbcc", "sql", H, r"\bDBCC\s+(?:SHRINK\w*|CHECKDB[^;]*REPAIR\w*|DROPCLEANBUFFERS|FREEPROCCACHE)\b", "Destructive/disruptive DBCC command"),
    _r("sql.kill", "sql", M, r"(?:^|;)\s*KILL\s+\d+", "KILL session"),
    _r("sql.permissions", "sql", M, r"(?:^|;)\s*(?:GRANT|REVOKE|DENY)\b", "Permission change (GRANT/REVOKE/DENY)"),
    _r("sql.delete", "sql", M, r"(?<!ON )\bDELETE\b(?:\s+TOP\s*\(\s*\d+\s*\)(?:\s+PERCENT)?)?\s+(?:FROM\s+[\w\[\]\".`#@]|[\w\[\]\".`#@]+\s*(?:;|$|\bWHERE\b|\bOUTPUT\b|\bFROM\b))",
       "DELETE statement"),
)

_SQL_DELETE_RE = re.compile(
    r"(?<!ON )\bDELETE\b(?:\s+TOP\s*\(\s*\d+\s*\)(?:\s+PERCENT)?)?\s+(?:FROM\s+[\w\[\]\".`#@]|[\w\[\]\".`#@]+\s*(?:;|$|\bWHERE\b|\bOUTPUT\b|\bFROM\b))",
    re.IGNORECASE,
)
_SQL_CLIENT_RE = re.compile(
    r"\b(?:sqlcmd|osql|bcp|psql|mysql|mariadb|sqlite3|duckdb|Invoke-Sqlcmd|clickhouse-client|mongosh|mongo)\b"
    r"|\bDROP\s+(?:TABLE|DATABASE|SCHEMA)\b|\bTRUNCATE\s+TABLE\b|\bDELETE\s+FROM\b|\bALTER\s+TABLE\b",
    re.IGNORECASE,
)
_SQL_UPDATE_RE = re.compile(r"(?:^|\s)UPDATE\s+(?:TOP\s*\(\s*\d+\s*\)\s+)?[\w\[\]\".`#@]+\s+SET\b", re.IGNORECASE)
_SQL_WHERE_RE = re.compile(r"\bWHERE\b|\bCURRENT\s+OF\b", re.IGNORECASE)
_SQL_DYNAMIC_RE = re.compile(r"\bEXEC(?:UTE)?\b|\bSP_EXECUTESQL\b|\bSP_MSFOREACH\w+\b", re.IGNORECASE)
_SQL_HINT_RE = re.compile(r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|EXEC|MERGE|GRANT|REVOKE)\b", re.IGNORECASE)

_SENSITIVE_APPS = {
    "regedit": (H, "Registry Editor"),
    "diskpart": (C, "Disk partition tool"),
    "diskmgmt": (H, "Disk Management console"),
    "gpedit": (H, "Group Policy Editor"),
    "secpol": (H, "Local Security Policy"),
    "bcdedit": (C, "Boot configuration editor"),
    "format": (C, "Disk format utility"),
    "compmgmt": (M, "Computer Management console"),
    "services.msc": (M, "Services console"),
    "wf.msc": (H, "Windows Firewall console"),
}

_SCRIPT_EXTENSIONS = {".bat", ".cmd", ".ps1", ".sh", ".sql", ".psm1"}
_PROTECTED_RELATIVE = (
    "backend/safety/",
    ".env.local",
    "UNINSTALL_AND_CLEANUP.bat",
    "run_setup.bat",
    "run_setup.sh",
    "STOP_OMNIAGENT.bat",
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _snippet(text: str, match: re.Match[str], width: int = 80) -> str:
    start = max(0, match.start() - 20)
    end = min(len(text), match.end() + 40)
    snip = text[start:end].replace("\n", " ").strip()
    return snip[:width] + ("..." if len(snip) > width else "")


def _apply_rules(text: str, rules: Iterable[Rule]) -> list[GuardrailMatch]:
    found: list[GuardrailMatch] = []
    for rule in rules:
        m = rule.pattern.search(text)
        if m:
            found.append(
                GuardrailMatch(
                    rule_id=rule.rule_id,
                    category=rule.category,  # type: ignore[arg-type]
                    level=rule.level,
                    description=rule.description,
                    snippet=_snippet(text, m),
                )
            )
    return found


def _dedupe(matches: list[GuardrailMatch]) -> list[GuardrailMatch]:
    """Remove weaker duplicates of the same family (e.g. sh.rm when sh.rm_rf matched)."""
    by_family: dict[str, GuardrailMatch] = {}
    order: list[str] = []
    for m in matches:
        family = m.rule_id.split("_")[0] if m.rule_id.startswith(("sh.rm", "sh.del", "sh.remove_item", "sh.kill")) else m.rule_id
        current = by_family.get(family)
        if current is None:
            by_family[family] = m
            order.append(family)
        elif m.level.rank > current.level.rank:
            by_family[family] = m
    return [by_family[f] for f in order]


def strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def strip_sql_literals(sql: str) -> str:
    return re.sub(r"N?'(?:[^']|'')*'", "''", sql)


def split_sql_statements(sql: str) -> list[str]:
    """Split on semicolons and T-SQL batch separators (GO on its own line)."""
    batches = re.split(r"^\s*GO\s*(?:\d+)?\s*$", sql, flags=re.IGNORECASE | re.MULTILINE)
    statements: list[str] = []
    for batch in batches:
        for stmt in batch.split(";"):
            stmt = " ".join(stmt.split())
            if stmt:
                statements.append(stmt)
    return statements


def _split_by_keyword(statement: str) -> list[str]:
    """
    T-SQL allows statements without semicolons. Further split a statement at the
    start of every DML/DDL keyword so 'DELETE FROM a SELECT * FROM b WHERE x=1'
    does not hide an unconditional DELETE behind a later WHERE.
    """
    parts = re.split(r"(?=(?<!ON )\b(?:DELETE|UPDATE|INSERT|SELECT|DROP|TRUNCATE|ALTER|CREATE|MERGE|EXEC|EXECUTE)\b)", statement, flags=re.IGNORECASE)
    merged: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Keep sub-selects attached to their parent DELETE/UPDATE (e.g. WHERE id IN (SELECT ...)).
        if merged and re.match(r"SELECT\b", part, re.IGNORECASE) and merged[-1].rstrip().endswith("("):
            merged[-1] += " " + part
        elif merged and re.match(r"SELECT\b", part, re.IGNORECASE) and re.search(r"\b(?:IN|EXISTS)\s*\($", merged[-1], re.IGNORECASE):
            merged[-1] += " " + part
        else:
            merged.append(part)
    return merged


def assess_sql(text: str, strip_literals: bool = True) -> list[GuardrailMatch]:
    if not text or not _SQL_HINT_RE.search(text):
        return []
    clean = strip_sql_comments(text)
    has_dynamic = bool(_SQL_DYNAMIC_RE.search(clean))
    scanned = strip_sql_literals(clean) if strip_literals else clean
    sources = [scanned]
    if strip_literals and has_dynamic:
        # Dynamic SQL hides statements inside string literals - inspect them too.
        sources.append(clean.replace("''", "'"))

    matches: list[GuardrailMatch] = []
    for source in sources:
        normalized = " ".join(source.split()).upper()
        matches.extend(_apply_rules(normalized, SQL_RULES))
        for stmt in split_sql_statements(source):
            for sub in _split_by_keyword(stmt):
                upper = sub.upper()
                if _SQL_DELETE_RE.match(upper) and not _SQL_WHERE_RE.search(upper):
                    matches.append(GuardrailMatch(rule_id="sql.delete_no_where", category="sql", level=H,
                                                  description="DELETE without WHERE clause (deletes every row)", snippet=sub[:80]))
                if _SQL_UPDATE_RE.search(" " + upper) and not _SQL_WHERE_RE.search(upper) and upper.startswith("UPDATE"):
                    matches.append(GuardrailMatch(rule_id="sql.update_no_where", category="sql", level=H,
                                                  description="UPDATE without WHERE clause (modifies every row)", snippet=sub[:80]))
    unique: dict[str, GuardrailMatch] = {}
    for m in matches:
        if m.rule_id not in unique or m.level.rank > unique[m.rule_id].level.rank:
            unique[m.rule_id] = m
    return list(unique.values())


def assess_shell(command: str) -> list[GuardrailMatch]:
    if not command or not command.strip():
        return []
    matches = _dedupe(_apply_rules(command, SHELL_RULES))
    # Avoid flagging plain reads of the hosts file as writes when no write verb exists
    filtered: list[GuardrailMatch] = []
    for m in matches:
        if m.rule_id == "sh.hosts_write" and not re.search(r">|Add-Content|Set-Content|Out-File|\btee\b|\becho\b|notepad|\bcopy\b|\bmove\b|\bsed\s+-i", command, re.IGNORECASE):
            m = m.model_copy(update={"level": L, "description": "Read access to the hosts file"})
        filtered.append(m)
    # SQL passed on the command line (sqlcmd -Q "DROP TABLE ...", psql -c ...)
    if _SQL_CLIENT_RE.search(command):
        filtered.extend(assess_sql(command, strip_literals=False))
    return filtered


def _resolve_inside(base: Path, candidate: str) -> Optional[Path]:
    try:
        p = Path(candidate)
        full = (p if p.is_absolute() else (base / p)).resolve()
        full.relative_to(base.resolve())
        return full
    except (ValueError, OSError, RuntimeError):
        return None


def referenced_scripts(command: str) -> list[Path]:
    """Find workspace script files that a shell command would execute."""
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError:
        tokens = command.split()
    scripts: list[Path] = []
    for tok in tokens:
        tok = tok.strip("\"'&;|()")
        if Path(tok).suffix.lower() in _SCRIPT_EXTENSIONS:
            resolved = _resolve_inside(WORKSPACE_ROOT, tok) or _resolve_inside(PROJECT_ROOT, tok)
            if resolved and resolved.is_file():
                scripts.append(resolved)
    return scripts


def is_inside_workspace(path_str: str) -> bool:
    return _resolve_inside(WORKSPACE_ROOT, path_str) is not None


def _build(matches: list[GuardrailMatch], blocked: bool = False, reason: str = "") -> RiskAssessment:
    level = RiskLevel.max(*(m.level for m in matches)) if matches else RiskLevel.NONE
    return RiskAssessment(level=level, matches=matches, blocked=blocked, block_reason=reason)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
class Guardrails:
    """Evaluates tool calls and raw text for destructive intent."""

    def assess_command(self, command: str) -> RiskAssessment:
        matches = assess_shell(command)
        for script in referenced_scripts(command):
            try:
                content = script.read_text(encoding="utf-8", errors="replace")[:200_000]
            except OSError:
                continue
            inner = assess_sql(content) if script.suffix.lower() == ".sql" else assess_shell(content)
            for m in inner:
                matches.append(m.model_copy(update={"description": f"{m.description} (inside {script.name})"}))
        return _build(matches)

    def assess_sql_text(self, sql: str) -> RiskAssessment:
        return _build(assess_sql(sql))

    def assess_typed_text(self, text: str) -> RiskAssessment:
        """Text typed into an arbitrary desktop window may be SQL (SSMS) or a shell command."""
        return _build(assess_sql(text) + assess_shell(text))

    def assess_file_write(self, relative_path: str, content: str = "") -> RiskAssessment:
        target = _resolve_inside(WORKSPACE_ROOT, relative_path)
        if target is None:
            return _build(
                [GuardrailMatch(rule_id="path.outside_workspace", category="path", level=C,
                                description="Write outside the sandboxed workspace", snippet=relative_path)],
                blocked=True, reason=f"Path '{relative_path}' resolves outside the workspace root {WORKSPACE_ROOT}.",
            )
        matches: list[GuardrailMatch] = []
        try:
            rel = target.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            rel = target.as_posix()
        for protected in _PROTECTED_RELATIVE:
            if rel == protected.rstrip("/") or rel.startswith(protected):
                matches.append(GuardrailMatch(rule_id="path.protected", category="security", level=H,
                                              description=f"Modification of protected safety/launcher file '{rel}'", snippet=rel))
        return _build(matches)

    def assess_file_read(self, relative_path: str) -> RiskAssessment:
        if _resolve_inside(WORKSPACE_ROOT, relative_path) is None:
            return _build(
                [GuardrailMatch(rule_id="path.outside_workspace", category="path", level=C,
                                description="Read outside the sandboxed workspace", snippet=relative_path)],
                blocked=True, reason=f"Path '{relative_path}' resolves outside the workspace root {WORKSPACE_ROOT}.",
            )
        return _build([])

    def assess_app_launch(self, app: str) -> RiskAssessment:
        lowered = app.lower().strip()
        matches: list[GuardrailMatch] = []
        for key, (level, desc) in _SENSITIVE_APPS.items():
            if re.search(rf"(?:^|[\\/\s]){re.escape(key)}(?:\.exe|\.msc)?(?:$|\s)", lowered):
                matches.append(GuardrailMatch(rule_id=f"app.{key}", category="system", level=level,
                                              description=f"Launching sensitive system tool: {desc}", snippet=app))
        matches.extend(assess_shell(app))
        return _build(matches)

    def assess_tool_call(self, name: str, args: dict[str, Any], typed_buffer: str = "") -> RiskAssessment:
        if name == "execute_shell":
            return self.assess_command(str(args.get("command", "")))
        if name == "gui_type_string":
            text = str(args.get("text", ""))
            combined = (typed_buffer + text)[-8000:]
            return self.assess_typed_text(combined)
        if name == "write_file":
            return self.assess_file_write(str(args.get("relative_path", "")), str(args.get("content", "")))
        if name == "apply_patch":
            return self.assess_file_write(str(args.get("relative_path", "")), str(args.get("replace", "")))
        if name in ("read_file", "list_directory"):
            return self.assess_file_read(str(args.get("relative_path", ".") or "."))
        if name == "launch_or_focus_app":
            return self.assess_app_launch(str(args.get("app_name_or_title", "")))
        if name == "app_action":
            payload = str(args.get("argument", "") or "")
            action = str(args.get("action", ""))
            if action in ("run_query", "paste_and_run"):
                return self.assess_typed_text(payload)
            if action == "open_path":
                return _build([])
            return self.assess_typed_text(payload) if payload else _build([])
        if name == "ui_set_text":
            combined = (typed_buffer + str(args.get("text", "")))[-8000:]
            return self.assess_typed_text(combined)
        return _build([])


guardrails = Guardrails()
