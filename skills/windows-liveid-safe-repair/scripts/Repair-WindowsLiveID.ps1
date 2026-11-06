#requires -Version 5.1
<#
Read-only audit by default; optional current-user Live ID registration repair.
Never deletes credentials, tokens, logs, services, registry keys or user files.
#>
[CmdletBinding()]
param(
    [ValidateSet('Audit','Repair')][string]$Mode='Audit',
    [ValidateRange(1,60)][int]$Minutes=5
)
$ErrorActionPreference='Stop'
$runStart=Get-Date
$desktop=[Environment]::GetFolderPath('Desktop')
$reportRoot=Join-Path $desktop 'Windows-LiveID-Repair-Reports'
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
$reportFile=Join-Path $reportRoot ('LiveID-'+$runStart.ToString('yyyyMMdd-HHmmss')+'.txt')
$lines=New-Object 'System.Collections.Generic.List[string]'
function Write-Report([string]$s) {
    $script:lines.Add($s)
    Write-Host $s
}
function Get-LiveIdEvents([datetime]$from) {
    $items=@(Get-WinEvent -FilterHashtable @{
        LogName='Microsoft-Windows-LiveId/Operational'
        Id=2028,6113
        StartTime=$from
    } -ErrorAction SilentlyContinue)
    $groups=@()
    foreach($event in $items) {
        $pidNumber=0
        try {
            $xml=[xml]$event.ToXml()
            $pidNumber=[int]$xml.Event.System.Execution.ProcessID
        } catch {}
        $groups += [pscustomobject]@{EventId=$event.Id;ProcessId=$pidNumber}
    }
    $result=@($groups | Group-Object EventId,ProcessId |
      Sort-Object Count -Descending | Select-Object -First 8)
    return [pscustomobject]@{Count=$items.Count;Groups=$result}
}
Write-Report 'Windows Live ID Safe Repair - v1.0'
Write-Report ('Time (local): '+$runStart.ToString('s'))
Write-Report ('Mode: '+$Mode)
Write-Report 'Privacy: no email, username, passwords, tokens or raw messages collected.'
$baseline=Get-LiveIdEvents -from $runStart.AddMinutes(-$Minutes)
Write-Report ('Events 2028/6113 in previous '+$Minutes+' min: '+$baseline.Count)
foreach($g in $baseline.Groups) {
    $sample=$g.Group[0]
    $procName='unknown-or-exited'
    if($sample.ProcessId -gt 0) {
        try {
            $p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$sample.ProcessId) -ErrorAction SilentlyContinue
            if($p){$procName=$p.Name}
        } catch {}
    }
    Write-Report ('Event/PID/Process/Count: '+$sample.EventId+' / '+$sample.ProcessId+' / '+$procName+' / '+$g.Count)
}
foreach($serviceName in @('wlidsvc','TokenBroker','GamingServices','GamingServicesNet')) {
    $svc=Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if($svc){Write-Report ('Service '+$serviceName+': '+$svc.Status+' ('+$svc.StartType+')')}
    else {Write-Report ('Service '+$serviceName+': NOT INSTALLED')}
}
foreach($packageName in @('Microsoft.Windows.CloudExperienceHost','Microsoft.AccountsControl','Microsoft.XboxIdentityProvider','Microsoft.GamingServices')) {
    $pkg=Get-AppxPackage -Name $packageName -ErrorAction SilentlyContinue
    if($pkg){Write-Report ('Package '+$packageName+': '+$pkg.Status+' version '+$pkg.Version)}
    else{Write-Report ('Package '+$packageName+': NOT AVAILABLE')}
}
$account=Get-ItemProperty 'HKCU:\Software\Microsoft\OneDrive\Accounts\Personal' -ErrorAction SilentlyContinue
if($account) {
    $signIn='NOT RECORDED'
    if($null -ne $account.LastSignInResult){$signIn=('0x{0:X8}' -f [uint32]$account.LastSignInResult)}
    Write-Report ('OneDrive local sign-in result: '+$signIn)
}
if($Mode -eq 'Repair') {
    Write-Report 'Repair action: re-register personal Microsoft Live ID UI package for CURRENT USER.'
    $package=Get-AppxPackage -Name 'Microsoft.Windows.CloudExperienceHost' -ErrorAction SilentlyContinue
    $manifest=if($package){Join-Path $package.InstallLocation 'AppxManifest.xml'}else{
        Join-Path $env:windir 'SystemApps\Microsoft.Windows.CloudExperienceHost_cw5n1h2txyewy\AppxManifest.xml'
    }
    if(Test-Path -LiteralPath $manifest) {
        try {
            Add-AppxPackage -DisableDevelopmentMode -Register $manifest -ErrorAction Stop
            Write-Report 'Live ID UI package registration: COMMAND SUCCEEDED (not proof of login).'
        } catch {
            Write-Report ('Live ID UI package registration: FAILED HResult '+('0x{0:X8}' -f [uint32]$_.Exception.HResult))
        }
    } else {Write-Report 'Live ID UI package manifest: MISSING. No change performed.'}
    Write-Report 'Post-check: observing new events for 20 seconds.'
    $checkFrom=Get-Date
    Start-Sleep -Seconds 20
    $after=Get-LiveIdEvents -from $checkFrom
    Write-Report ('NEW Live ID 2028/6113 events after repair attempt: '+$after.Count)
    if($after.Count -eq 0){Write-Report 'NO EVENTS IN SHORT WINDOW. Sustained resolution: UNVERIFIED.'}
    else{Write-Report 'ISSUE STILL PRESENT. No credentials or service registry keys were deleted.'}
}
if(-not (Get-Service GamingServicesNet -ErrorAction SilentlyContinue)) {
    Write-Report 'GamingServicesNet missing. Refer to signed Xbox tool:'
    Write-Report 'https://support.xbox.com/help/games-apps/troubleshooting/gaming-services-repair-tool'
}
Write-Report 'History preserved; no gaming service was disabled, removed or reinstalled.'
$lines | Out-File -LiteralPath $reportFile -Encoding UTF8
Write-Host ('Report saved: '+$reportFile)