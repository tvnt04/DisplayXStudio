#define MyAppName "Display X Studio"
#define MyAppVersion "1.3.9"
#define MyAppPublisher "TVNT04"
#define MyAppExeName "Display X Studio.exe"
#define MyAppId "{{D7A9F6E8-6D3B-4E5A-9B31-2A7C8F4D6E10}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Display X Studio
DefaultGroupName={#MyAppName}
OutputDir=..\..
OutputBaseFilename=Display-X-Studio-{#MyAppVersion}-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayName={#MyAppName}
Uninstallable=yes
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\..\dist\Display X Studio\*"; DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Display X Studio"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Display X Studio"; \
    Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; \
    GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch Display X Studio"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{localappdata}\Display X Studio"
