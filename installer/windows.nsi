; Seal Desktop – NSIS Installer Script
; Generates a professional Windows installer (.exe)
; Requires NSIS 3.x and EnVar plugin

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; ─── Metadata ──────────────────────────────────────────────────────────────
!define APP_NAME        "Seal Desktop"
!define APP_VERSION     "1.0.0"
!define APP_PUBLISHER   "Seal Desktop Team"
!define APP_URL         "https://github.com/your-username/seal-desktop"
!define APP_EXE         "SealDesktop.exe"
!define INSTALL_DIR     "$PROGRAMFILES64\${APP_NAME}"
!define UNINSTALL_KEY   "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
!define MUI_ICON        "assets\icon.ico"
!define MUI_UNICON      "assets\icon.ico"

; ─── Output ────────────────────────────────────────────────────────────────
Name            "${APP_NAME} ${APP_VERSION}"
OutFile         "dist\SealDesktop-${APP_VERSION}-Setup.exe"
InstallDir      "${INSTALL_DIR}"
InstallDirRegKey HKLM "${UNINSTALL_KEY}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor   /SOLID lzma

; ─── MUI Pages ─────────────────────────────────────────────────────────────
!define MUI_WELCOMEPAGE_TITLE    "Welcome to ${APP_NAME} Setup"
!define MUI_WELCOMEPAGE_TEXT     "This wizard will guide you through the installation of ${APP_NAME} ${APP_VERSION}.$\n$\nA powerful video & audio downloader powered by yt-dlp.$\n$\nClick Next to continue."
!define MUI_FINISHPAGE_RUN       "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT  "Launch ${APP_NAME}"
!define MUI_FINISHPAGE_SHOWREADME       ""
!define MUI_FINISHPAGE_SHOWREADME_TEXT  "Create desktop shortcut"
!define MUI_FINISHPAGE_SHOWREADME_FUNCTION CreateDesktopShortcut

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE    "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ─── Install Section ────────────────────────────────────────────────────────
Section "MainSection" SecMain
    SetOutPath "$INSTDIR"
    
    ; Copy all built files
    File /r "dist\SealDesktop\*.*"
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Registry: Add/Remove Programs
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayName"          "${APP_NAME}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayVersion"       "${APP_VERSION}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "Publisher"            "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "URLInfoAbout"         "${APP_URL}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "InstallLocation"      "$INSTDIR"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "UninstallString"      "$INSTDIR\Uninstall.exe"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayIcon"          "$INSTDIR\${APP_EXE}"
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify"             1
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair"             1
    
    ; Estimate installed size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "EstimatedSize" "$0"
    
    ; Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
    CreateShortCut  "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"   "$INSTDIR\Uninstall.exe"
SectionEnd

; ─── Finish page callback ───────────────────────────────────────────────────
Function CreateDesktopShortcut
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
FunctionEnd

; ─── Uninstall Section ─────────────────────────────────────────────────────
Section "Uninstall"
    ; Remove files
    RMDir /r "$INSTDIR"
    
    ; Remove Start Menu
    RMDir /r "$SMPROGRAMS\${APP_NAME}"
    
    ; Remove Desktop shortcut
    Delete "$DESKTOP\${APP_NAME}.lnk"
    
    ; Remove registry keys
    DeleteRegKey HKLM "${UNINSTALL_KEY}"
SectionEnd
