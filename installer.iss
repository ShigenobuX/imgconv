; imgconv Windows installer (Inno Setup 7)
; Build with: ISCC.exe installer.iss

#define MyAppName "imgconv"
#define MyAppVersion "0.9.4"
#define MyAppPublisher "imgconv"
#define MyAppExeName "imgconv.exe"

[Setup]
AppId={{1B61584F-DBD6-4B5B-B4A6-A7B88BEBE271}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=InstallerOutput
OutputBaseFilename=imgconv-{#MyAppVersion}-setup
SetupIconFile=imgconv.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=lowest
SetupArchitecture=x64

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加のショートカット:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--register-menu"; Description: "右クリックメニューを登録する"; Flags: postinstall nowait skipifsilent unchecked
Filename: "{app}\{#MyAppExeName}"; Description: "imgconv を起動する"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--unregister-menu"; Flags: runhidden; RunOnceId: "RemoveImgconvContextMenu"
