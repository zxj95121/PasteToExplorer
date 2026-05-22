#define MyAppName "Paste to Explorer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "PasteToExplorer"
#define MyAppExeName "PasteToExplorer.exe"
#define MyAppId "{{B8F7A3D2-1C4E-4F6A-9B0D-3E5A7C1F8E2D}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppMutex=PasteToExplorer
CloseApplications=yes
RestartApplications=no
OutputDir=.
OutputBaseFilename=PasteToExplorer_Setup_{#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequired=admin
LicenseFile=LICENSE.txt
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription=Screenshot->Ctrl+V in Explorer->Save as file
WizardStyle=modern
DisableWelcomePage=no
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\PasteToExplorer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\images\logo.png"; DestDir: "{app}\assets\images"; Flags: ignoreversion
Source: "assets\images\logo0.png"; DestDir: "{app}\assets\images"; Flags: ignoreversion
Source: "tray_icon.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Run at Windows startup"; GroupDescription: "Startup:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Run {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PasteToExplorer"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: startup

[Code]
function InitializeSetup: Boolean;
var V: TWindowsVersion;
begin
  Result := IsWin64;
  if not IsWin64 then MsgBox('64-bit Windows required. Setup will exit.', mbError, MB_OK)
  else begin
    GetWindowsVersionEx(V);
    if V.Major < 10 then begin
      MsgBox('Windows 10 or later required. Setup will exit.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;
