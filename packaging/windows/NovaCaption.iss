#ifndef SourceDir
  #error SourceDir must be passed with /DSourceDir=...
#endif
#ifndef OutputDir
  #error OutputDir must be passed with /DOutputDir=...
#endif
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "NovaCaption"
#define AppExeName "NovaCaption.exe"

[Setup]
AppId={{91A552E7-24B0-4F69-889B-27AEEB341670}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=NovaCaption Contributors
AppPublisherURL=https://github.com/yu-hou/VideoCaptioner-customize
AppSupportURL=https://github.com/yu-hou/VideoCaptioner-customize/issues
AppUpdatesURL=https://github.com/yu-hou/VideoCaptioner-customize/releases
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=VideoCaptioner-Setup-x64
SetupIconFile={#SourceDir}\_internal\resource\assets\novacaption.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标："; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "启动 {#AppName}"; Flags: nowait postinstall skipifsilent
