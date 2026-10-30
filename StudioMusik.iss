; Konfigurasi installer Inno Setup untuk Studio Musik Otomatis
#define MyAppName "Studio Musik Otomatis"
#define MyAppVersion "1.0.1"
#define MyAppExeName "StudioMusikOtomatis.exe"

[Setup]
AppId={{D8E2B5B9-1A7C-4D6F-9B3A-21E3C0A7B411}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Studio Musik Otomatis
DefaultDirName={autopf}\Studio Musik Otomatis
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=Setup_Studio_Musik_Otomatis_Windows11
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "indonesian"; MessagesFile: "compiler:Languages\Indonesian.isl"

[Tasks]
Name: "desktopicon"; Description: "Buat pintasan di Desktop"; GroupDescription: "Pintasan tambahan:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Jalankan {#MyAppName}"; Flags: postinstall nowait skipifsilent
