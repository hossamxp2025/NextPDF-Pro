# Launch the built installer, advance from the welcome page to the license page
# and save the wizard window itself with PrintWindow (works even when another
# window is in front). Nothing is installed; the wizard is closed afterwards.
param(
    [string]$Setup,
    [string]$Language,
    [string]$Path
)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class SetupCapture {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int command);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, IntPtr processId);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint attach, uint attachTo, bool join);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

function Stop-SetupProcesses {
    Get-Process | Where-Object { $_.ProcessName -like "NextPDF-Pro-Setup*" } |
        ForEach-Object { try { Stop-Process -Id $_.Id -Force -ErrorAction Stop } catch { } }
}

function Find-Wizard {
    $candidates = Get-Process | Where-Object {
        $_.ProcessName -like "NextPDF-Pro-Setup*" -and $_.MainWindowHandle -ne 0
    }
    $best = [IntPtr]::Zero
    $area = 0
    foreach ($candidate in $candidates) {
        $rect = New-Object SetupCapture+RECT
        [void][SetupCapture]::GetWindowRect($candidate.MainWindowHandle, [ref]$rect)
        $size = ($rect.Right - $rect.Left) * ($rect.Bottom - $rect.Top)
        if ($size -gt $area) { $area = $size; $best = $candidate.MainWindowHandle }
    }
    return $best
}

function Force-Foreground([IntPtr]$handle) {
    [void][SetupCapture]::ShowWindow($handle, 9)
    [void][SetupCapture]::BringWindowToTop($handle)
    $foreground = [SetupCapture]::GetForegroundWindow()
    $foregroundThread = [SetupCapture]::GetWindowThreadProcessId($foreground, [IntPtr]::Zero)
    $targetThread = [SetupCapture]::GetWindowThreadProcessId($handle, [IntPtr]::Zero)
    $joined = $false
    if ($foregroundThread -ne $targetThread) {
        $joined = [SetupCapture]::AttachThreadInput($foregroundThread, $targetThread, $true)
    }
    [void][SetupCapture]::SetForegroundWindow($handle)
    Start-Sleep -Milliseconds 300
    if ($joined) {
        [void][SetupCapture]::AttachThreadInput($foregroundThread, $targetThread, $false)
    }
}

Stop-SetupProcesses
Start-Sleep -Milliseconds 500

Start-Process -FilePath $Setup -ArgumentList "/CURRENTUSER", "/LANG=$Language" | Out-Null
Start-Sleep -Seconds 5

$handle = Find-Wizard
if ($handle -eq [IntPtr]::Zero) {
    Write-Output "wizard window not found"
    Stop-SetupProcesses
    exit 1
}

Force-Foreground $handle
$rect = New-Object SetupCapture+RECT
[void][SetupCapture]::GetWindowRect($handle, [ref]$rect)
# Click the wizard's default Next button, which advances welcome -> license.
[void][SetupCapture]::SetCursorPos($rect.Right - 95, $rect.Bottom - 30)
Start-Sleep -Milliseconds 250
[SetupCapture]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
[SetupCapture]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Seconds 2

$rect = New-Object SetupCapture+RECT
[void][SetupCapture]::GetWindowRect($handle, [ref]$rect)
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$hdc = $graphics.GetHdc()
[void][SetupCapture]::PrintWindow($handle, $hdc, 2)
$graphics.ReleaseHdc($hdc)
$bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()

[void][SetupCapture]::PostMessage($handle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
Start-Sleep -Seconds 1
Stop-SetupProcesses
Write-Output "saved $Path ($width x $height)"
