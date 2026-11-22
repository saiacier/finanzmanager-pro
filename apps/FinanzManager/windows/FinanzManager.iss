; SPDX-License-Identifier: GPL-3.0-or-later
; Copyright (C) 2026 Samuele Timoteo Iacierno
; Windows installer of FinanzManager Pro (Inno Setup 6). Built by scripts/build.py on Windows:
; installs per user without administrator rights; uninstalling keeps the user's financial data.
#ifndef AppVersion
  #error AppVersion fehlt
#endif

[Setup]
AppId={{ECF7A1E9-330C-417E-86DC-16466BFF7A9A}
AppName=FinanzManager Pro
AppVersion={#AppVersion}
AppVerName=FinanzManager Pro {#AppVersion}
AppPublisher=Samuele Timoteo Iacierno · IT & SmartHome Service
AppPublisherURL=https://it-smarthome.net
AppSupportURL=https://it-smarthome.net/downloads
AppUpdatesURL=https://it-smarthome.net/downloads
AppCopyright=© 2026 Samuele Timoteo Iacierno · IT-Smarthome
VersionInfoVersion={#AppVersion}
PrivilegesRequired=lowest
DefaultDirName={autopf}\FinanzManager Pro
DisableProgramGroupPage=yes
DisableDirPage=auto
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes
InfoBeforeFile={#InfoFile}
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\FinanzManager Pro.exe
UninstallDisplayName=FinanzManager Pro
OutputDir={#OutputDir}
OutputBaseFilename=FinanzManager-Pro-{#AppVersion}-Windows-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; Updates replace the program files completely; the data folder is elsewhere and stays untouched.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\FinanzManager Pro"; Filename: "{app}\FinanzManager Pro.exe"
Name: "{autodesktop}\FinanzManager Pro"; Filename: "{app}\FinanzManager Pro.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FinanzManager Pro.exe"; Description: "{cm:LaunchProgram,FinanzManager Pro}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
    MsgBox('FinanzManager Pro wurde entfernt.' + #13#10#13#10 +
      'Deine Finanzdaten, Einstellungen und Sicherungen bleiben erhalten unter:' + #13#10 +
      ExpandConstant('{localappdata}\IT-Smarthome\FinanzManager') + #13#10#13#10 +
      'Bei einer erneuten Installation werden sie wieder verwendet. Wenn du sie nicht mehr brauchst, kannst du diesen Ordner selbst löschen.',
      mbInformation, MB_OK);
end;
