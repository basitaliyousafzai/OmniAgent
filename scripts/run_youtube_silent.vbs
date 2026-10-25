' ============================================================================
' OmniAgent YouTube Automator — Invisible Windows Boot Daemon
' Module 10.2: Invisible COM Daemon
' Runs start_youtube.bat with zero console window popups via Task Scheduler
' ============================================================================

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

ScriptDirectory = FSO.GetParentFolderName(WScript.ScriptFullName)
BatPath = ScriptDirectory & "\start_youtube.bat"

' Window Style 0 = Hidden, False = Do not wait for script completion
WshShell.Run """" & BatPath & """", 0, False
