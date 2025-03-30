#define NAME "uFocus"
#define VERSION GetEnv("VERSION")

[Setup]
AppId={{7590DFA6-239C-4C9E-AF4D-C218A0E48189}
AppName={#NAME}
AppVersion={#VERSION}
AppPublisher=Dimitrios Papaioannou
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DefaultDirName={autopf}\{#NAME}
DefaultGroupName={#NAME}
OutputDir=build
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=uFocus-setup-win64
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "build\main.dist\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#NAME}"; Filename: "{app}\{#NAME}-{#VERSION}.exe"
Name: "{group}\{cm:UninstallProgram,{#NAME}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#NAME}"; Filename: "{app}\{#NAME}-{#VERSION}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#NAME}-{#VERSION}.exe"; Description: "Launch {#NAME}"; Flags: nowait postinstall skipifsilent