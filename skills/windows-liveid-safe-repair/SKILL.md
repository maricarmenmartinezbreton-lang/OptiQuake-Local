---
name: windows-liveid-safe-repair
description: Diagnoses Windows Live ID events 2028 and 6113, error 0x80048888, Xbox Gaming Services and personal OneDrive sign-in failures on Windows 10/11. Performs a read-only audit by default and provides an explicitly requested conservative current-user registration repair. Never wipes credentials or event logs.
license: AGPL-3.0-only
compatibility: Windows 10/11; Windows PowerShell 5.1; interactive user session; user-scope registration repair.
---

# Windows Live ID Safe Repair

## Scope
Investigate repeated Microsoft-Windows-LiveId/Operational events 2028 and 6113, error 0x80048888, and related Xbox/Gaming Services or OneDrive login issues. These events are symptoms; a failed browser login, local-account reset, and an Xbox service issue have different causes.

## Safety constraints
1. Run a **READ-ONLY** audit before any repair.
2. Do not clear Security, LiveId or other event logs; old events remain evidence.
3. Never delete or reset credential vaults, OneAuth, IdentityCache, TokenBroker, DPAPI, Windows Hello, local users, Windows sessions, passwords or games.
4. Never disable, uninstall or re-register the GamingServices package automatically: package registration can fail and affect Windows services. Do not invent service registry keys or repair from guessed paths.
5. Never close Steam, OneDrive, JARVIS-OS, Docker or unrelated applications.
6. Do not change Windows sign-in accounts or restart Windows without distinct, explicit authorization.
7. Produce redacted reports only; do not publish machine names, user IDs, emails, tokens, raw account identifiers or event messages.
8. Preserve prior status, perform a bounded intervention, inspect error rates before/after, and state UNRESOLVED if errors persist.

## Safe runbook
- Identify Windows version, current session, OneDrive sign-in result (hex only), and services wlidsvc, TokenBroker, GamingServices, GamingServicesNet.
- Read Microsoft-Windows-LiveId/Operational IDs 2028 and 6113 with a bounded time window.
- Parse System.Execution.ProcessID, then resolve currently active process names. PIDs may be recycled; do not presume historical process identity from the current process list alone.
- If gamingservices.exe is source of event 2028 and wlidsvc of 6113, report process attribution but do not claim that deleting GamingServices or any credential is the root-cause fix.
- Run safe audit from skill root with Windows PowerShell:
  powershell.exe -NoProfile -File scripts/Repair-WindowsLiveID.ps1 -Mode Audit
- If the user authorizes a minimal live-ID component repair:
  powershell.exe -NoProfile -File scripts/Repair-WindowsLiveID.ps1 -Mode Repair
  It re-registers only Microsoft.Windows.CloudExperienceHost under the current user and samples new errors. No gaming services or credential stores are deleted.
- For local one-click launch after downloading/extracting, double-click Ejecutar-reparacion-segura.cmd. It uses process-scoped ExecutionPolicy Bypass. It never changes machine-wide PowerShell policy.
- If GamingServicesNet is missing, refer the user to the official Microsoft Xbox Gaming Services Repair Tool. Check Microsoft Authenticode signature before launching it and verify both services afterward. The official tool can require interaction or an approved reboot.
- If still failing, report UNRESOLVED and suggest guided investigation; do not automatically escalate to destructive steps.

## Validation and honesty
- PowerShell syntax parse: zero ParseError objects.
- Audit: no system mutation and redacted report is produced.
- Registration succeeded is not proof of successful Microsoft account authentication.
- A 20-second window without errors does not prove permanent resolution. Use continued monitoring and confirm real application sign-in separately.
- Local reports are written to the Desktop/Windows-LiveID-Repair-Reports folder and must not be committed to a public repo.

## References
- Microsoft Live ID and WAM repair: https://learn.microsoft.com/troubleshoot/microsoft-365/authentication/automatic-authentication-fails
- Microsoft Xbox Gaming Services Repair Tool: https://support.xbox.com/help/games-apps/troubleshooting/gaming-services-repair-tool
- Agent Skills specification: https://agentskills.io/specification