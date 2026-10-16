#ifndef AppVersion
#define AppVersion "0.3.0"
#endif
[Setup]
AppId={{C130450A-6680-47B6-9FCC-275DBCA2E3A1}
AppName=WriteWatch
AppVersion={#AppVersion}
AppPublisher=Joseph Luker
DefaultDirName={localappdata}\Programs\WriteWatch
DefaultGroupName=WriteWatch
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=WriteWatch-{#AppVersion}-Windows-Setup
SetupIconFile=..\build\assets\writewatch.ico
UninstallDisplayIcon={app}\WriteWatch.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
[Files]
Source: "..\dist\WriteWatch\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\WriteWatch"; Filename: "{app}\WriteWatch.exe"
Name: "{autodesktop}\WriteWatch"; Filename: "{app}\WriteWatch.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Run]
Filename: "{app}\WriteWatch.exe"; Description: "Open WriteWatch"; Flags: nowait postinstall skipifsilent

Filename: "{app}\WriteWatch.exe"; Flags: nowait; Check: IsUpdater

[Code]
function IsUpdater: Boolean;
begin
  Result := ExpandConstant('{param:WRITEWATCHUPDATE|0}') = '1';
end;
