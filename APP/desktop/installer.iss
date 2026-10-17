; Draft branding. Final name/logo must be approved before GitHub publication.
#define AppName "Paddy"
#define AppVersion "0.1.0"
#define AppExeName "Paddy.exe"

[Setup]
AppId={{A4C79094-C8C6-4AAF-98AC-56D949EEFC17}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=R Ritwik and Joshith G
DefaultDirName={autopf}\{#AppName}
DisableDirPage=no
UsePreviousAppDir=yes
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir=releases
OutputBaseFilename=Paddy-Setup-{#AppVersion}
SetupIconFile=branding\paddy.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
MinVersion=10.0.17763
AppMutex=PaddyDesktop
CloseApplications=yes
RestartApplications=no
Uninstallable=yes
SetupLogging=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\..\OTHER\paddy_build_0_1_0\dist\Paddy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; AppUserModelID: "Paddy.Desktop.1"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon; AppUserModelID: "Paddy.Desktop.1"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Open {#AppName}"; Flags: nowait postinstall skipifsilent runasoriginaluser
