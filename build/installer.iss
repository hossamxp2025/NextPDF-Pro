; Inno Setup script for NextPDF Pro 1.1.0
; Build with: build\build_exe.py --installer  (defines ReleaseDir)

#define MyAppName "NextPDF Pro"
#include "version.iss"
#define MyAppPublisher "NextPDF"
#define MyAppURL "https://nextpdf.example.com"
#define MyAppExeName "NextPDF-Pro.exe"

#ifndef ReleaseDir
  #define ReleaseDir "..\dist\release-" + MyAppVersion
#endif

[Setup]
AppId={{8F4A1B2C-3D4E-5F6A-7B8C-9D0E1F2A3B4C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir={#ReleaseDir}
OutputBaseFilename=NextPDF-Pro-Setup-{#MyAppVersion}
SetupIconFile=..\resources\icons\NextPDF-Pro.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#ReleaseDir}\NextPDF-Pro.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseDir}\README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseDir}\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseDir}\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseDir}\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ReleaseDir}\LICENSES.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseDir}\VERSION.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseDir}\SHA256SUMS.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
