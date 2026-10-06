; Inno Setup Script for NICETECH_biometric
; Compiles NICETECH_biometric.exe into an installer wizard (Setup_NICETECH_biometric.exe)

#define MyAppName "NICETECH_biometric"
#define MyAppVersion "2.0"
#define MyAppPublisher "NICETECH"
#define MyAppExeName "NICETECH_biometric.exe"

[Setup]
AppId={{E89F4312-7809-4B02-861C-4B9F75201B78}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\NICETECH_biometric
DefaultGroupName={#MyAppName}
OutputDir=Ready_To_Distribute
OutputBaseFilename=Setup_NICETECH_biometric
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "Ready_To_Distribute\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
