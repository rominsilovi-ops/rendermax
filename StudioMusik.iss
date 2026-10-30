# Inno Setup installer definition
#define MyAppName "Studio Musik Otomatis"
#define MyAppVersion "1.0.0"
#define MyAppExeName "StudioMusikOtomatis.exe"

[Setup]
AppId={{D8E2B5B9-1A7C-4D6F-9B3A-21E3C0A7B411}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\Studio Musik Otomatis
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=Setup_Studio_Musik_Otomatis_Windows11
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Buat pintasan di Desktop"; GroupDescription: "Pintasan tambahan:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Jalankan Studio Musik Otomatis"; Flags: postinstall nowait skipifsilent
