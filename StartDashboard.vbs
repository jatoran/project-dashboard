' Launch Project Dashboard without a console window
' Double-click this file to start the dashboard in the system tray

Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Run uv in hidden mode (0 = hidden, False = don't wait)
WshShell.Run "cmd /c cd /d """ & strPath & """ && uv run --project backend python backend/tray.py", 0, False
