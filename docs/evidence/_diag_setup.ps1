param([string]$Setup, [string]$Language, [string]$Prefix)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class DiagWin {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc callback, IntPtr extra);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int max);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
function Capture([string]$path) {
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
}
$p = Start-Process -FilePath $Setup -ArgumentList "/CURRENTUSER", "/LANG=$Language" -PassThru
Start-Sleep -Seconds 5
Capture "$Prefix-1-welcome.png"

$script:found = @()
$cb = [DiagWin+EnumWindowsProc]{
    param($h, $l)
    if ([DiagWin]::IsWindowVisible($h)) {
        $sb = New-Object System.Text.StringBuilder 512
        [void][DiagWin]::GetWindowText($h, $sb, 512)
        $t = $sb.ToString()
        if ($t -like "*NextPDF*") {
            $r = New-Object DiagWin+RECT
            [void][DiagWin]::GetWindowRect($h, [ref]$r)
            $script:found += [pscustomobject]@{ Handle=$h; Title=$t; Rect="$($r.Left),$($r.Top),$($r.Right),$($r.Bottom)" }
        }
    }
    return $true
}
[void][DiagWin]::EnumWindows($cb, [IntPtr]::Zero)
$script:found | Format-List

[System.Windows.Forms.SendKeys]::SendWait("%n")
Start-Sleep -Seconds 2
Capture "$Prefix-2-after-next.png"

$script:found = @()
[void][DiagWin]::EnumWindows($cb, [IntPtr]::Zero)
$script:found | Format-List

if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
