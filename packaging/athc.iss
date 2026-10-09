; Inno Setup script for the athc installer.
;
; Compiled by packaging\release-build.ps1, which passes AppVersion, StagingDir,
; ConfigDir, DocsDir, ChangelogFile, LicenseFile, OutputDir and OutputBaseName
; with /D. athc-admin's build compiles this same script for the admin setup.exe
; and also passes AdminDocsDir. Running ISCC on this file directly fails on the
; #error checks below.

#ifndef AppVersion
  #error AppVersion must be passed with /DAppVersion=...
#endif
#ifndef StagingDir
  #error StagingDir must be passed with /DStagingDir=...
#endif
#ifndef ConfigDir
  #error ConfigDir must be passed with /DConfigDir=...
#endif
#ifndef DocsDir
  #error DocsDir must be passed with /DDocsDir=...
#endif
#ifndef ChangelogFile
  #error ChangelogFile must be passed with /DChangelogFile=...
#endif
#ifndef LicenseFile
  #error LicenseFile must be passed with /DLicenseFile=...
#endif
#ifndef OutputDir
  #error OutputDir must be passed with /DOutputDir=...
#endif
#ifndef OutputBaseName
  #error OutputBaseName must be passed with /DOutputBaseName=...
#endif

[Setup]
; One identity for the public and the admin setup.exe, so the admin one
; installs over the public one in place (the reverse is refused, see [Code]).
AppId={{A60A37FC-32E8-41F5-BF9E-C78F8A2C53C2}
AppName=Assistant to the Head Coach
AppVersion={#AppVersion}
AppVerName=Assistant to the Head Coach {#AppVersion}
AppPublisher=Brian Jacobs
DefaultDirName={autopf}\Assistant to the Head Coach
DisableProgramGroupPage=yes
DisableDirPage=yes
; Per-user install: no admin rights needed.
PrivilegesRequired=lowest
; The bundled Python is 64-bit; refuse 32-bit Windows instead of installing an
; athc.exe that cannot start.
ArchitecturesAllowed=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseName}
Compression=lzma2
SolidCompression=yes
; The installer edits the user's PATH.
ChangesEnvironment=yes
WizardStyle=modern
UninstallDisplayName=Assistant to the Head Coach {#AppVersion}

[InstallDelete]
; Setup replaces files but never removes ones an older bundle had, and
; PyInstaller renames internals between builds - wipe the old bundle first.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
; The PyInstaller onedir bundle: athc.exe plus its interpreter and libraries.
Source: "{#StagingDir}\*"; DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion
; Release docs are program files: refreshed on every install.
Source: "{#DocsDir}\*.txt"; DestDir: "{app}"; Flags: ignoreversion
; Renamed to .txt so double-clicking opens Notepad instead of prompting for an
; app.
Source: "{#ChangelogFile}"; DestDir: "{app}"; DestName: "CHANGELOG.txt"; \
    Flags: ignoreversion
Source: "{#LicenseFile}"; DestDir: "{app}"; DestName: "LICENSE.txt"; \
    Flags: ignoreversion
#ifdef AdminDocsDir
Source: "{#AdminDocsDir}\README.txt"; DestDir: "{app}"; \
    DestName: "README-admin.txt"; Flags: ignoreversion
Source: "{#AdminDocsDir}\COMMANDS.txt"; DestDir: "{app}"; \
    DestName: "COMMANDS-admin.txt"; Flags: ignoreversion
#endif
; User-owned config, in the folder athc reads it from: each file seeded only if
; it is missing, so edits survive an upgrade and a file new in a release is
; still added.
Source: "{#ConfigDir}\athc.ini"; DestDir: "{localappdata}\athc"; \
    Flags: onlyifdoesntexist
Source: "{#ConfigDir}\leagues\*"; DestDir: "{localappdata}\athc\leagues"; \
    Flags: recursesubdirs createallsubdirs onlyifdoesntexist

[Icons]
Name: "{autoprograms}\Assistant to the Head Coach README"; \
    Filename: "{app}\README.txt"

[UninstallDelete]
; The whole config folder, user edits and added files included.
Type: filesandordirs; Name: "{localappdata}\athc"

[Registry]
; Put athc.exe on PATH for this user.
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))
#ifdef AdminDocsDir
; Marks an admin install, so the public setup.exe refuses to install over it.
Root: HKCU; Subkey: "Software\Assistant to the Head Coach"; ValueType: string; \
    ValueName: "Edition"; ValueData: "admin"; Flags: uninsdeletekey
#endif

[Run]
Filename: "{app}\README.txt"; Description: "Open the README"; \
    Flags: postinstall shellexec skipifsilent nowait

[Code]
#ifndef AdminDocsDir
{ The public setup.exe would drop the admin commands and leave their docs
  behind, so it stops when the admin edition is installed. }
function InitializeSetup(): Boolean;
var
  Edition: string;
begin
  Result := True;
  if RegQueryStringValue(HKCU, 'Software\Assistant to the Head Coach', 'Edition', Edition)
     and (Edition = 'admin') then
  begin
    SuppressibleMsgBox('The admin edition of Assistant to the Head Coach is installed. ' +
      'Run the admin setup instead, or uninstall the admin edition first.',
      mbError, MB_OK, IDOK);
    Result := False;
  end;
end;
#endif

{ True when Dir is not already one of the entries in the user's PATH. }
function NeedsAddPath(Dir: string): Boolean;
var
  Existing: string;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', Existing) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Uppercase(Dir) + ';', ';' + Uppercase(Existing) + ';') = 0;
end;

{ Drop the install dir from PATH on uninstall, leaving other entries intact. }
procedure RemoveFromPath(Dir: string);
var
  Existing: string;
  Cleaned: string;
  Part: string;
  P: Integer;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', Existing) then
    exit;
  Cleaned := '';
  Existing := Existing + ';';
  repeat
    P := Pos(';', Existing);
    Part := Trim(Copy(Existing, 1, P - 1));
    Existing := Copy(Existing, P + 1, Length(Existing));
    if (Part <> '') and (Uppercase(Part) <> Uppercase(Dir)) then
    begin
      if Cleaned <> '' then
        Cleaned := Cleaned + ';';
      Cleaned := Cleaned + Part;
    end;
  until Existing = '';
  RegWriteExpandStringValue(HKCU, 'Environment', 'Path', Cleaned);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RemoveFromPath(ExpandConstant('{app}'));
end;
