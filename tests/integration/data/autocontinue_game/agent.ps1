# Runs INSIDE Windows Sandbox for test_autocontinue_game.py, started hidden by
# the sandbox LogonCommand. Starts athc autocontinue and the game the host
# built, then takes screenshots and clicks for the host: the host writes
# out\cmd.txt (a request id, then one command per line), the agent runs it,
# writes out\done.txt (the id) and deletes cmd.txt.
#
#   shot NAME   the primary screen to out\NAME.png
#   click X Y   a left click at X, Y
#   move X Y    the mouse to X, Y, no click
#   wait MS     a pause, so the game redraws
#   helper      starts pointer-helper.ps1, hidden, for the rest of the run

$ErrorActionPreference = 'Continue'
$desk  = 'C:\Users\WDAGUtilityAccount\Desktop'
$out   = Join-Path $desk 'out'
Start-Transcript -Path (Join-Path $out 'agent.log') | Out-Null

Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Native {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
}
'@
[Native]::SetProcessDPIAware() | Out-Null

# The game the host built, mapped writable to Desktop\SIERRA, at the path its
# settings name (E:\SIERRA\FbPro98).
subst E: $desk
# The game needs a CD drive, not its own disc: an empty disc image gives it one.
Mount-DiskImage -ImagePath (Join-Path $desk 'SIERRA\FbPro98\CD\empty.iso') | Out-Null

$setup = Get-ChildItem (Join-Path $desk 'dist\athc-*-setup.exe') | Select-Object -First 1
Start-Process $setup.FullName -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=$out\install.log" -Wait

# autocontinue in a minimized console, its lines to out; then the game.
Start-Process cmd.exe -ArgumentList '/c', (Join-Path $desk 'assets\run-autocontinue.cmd') -WindowStyle Minimized
Start-Sleep -Seconds 3
Start-Process 'E:\SIERRA\FbPro98\Hike.exe' -WorkingDirectory 'E:\SIERRA\FbPro98'
Set-Content (Join-Path $out 'ready.txt') 'ready'

function Shot([string]$name) {
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    $bmp.Save((Join-Path $out "$name.png"), [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
}

function Click([int]$x, [int]$y) {
    [Native]::SetCursorPos($x, $y) | Out-Null
    Start-Sleep -Milliseconds 150
    [Native]::mouse_event(0x2, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [Native]::mouse_event(0x4, 0, 0, 0, [UIntPtr]::Zero)
}

# done.txt through a temporary file, retried: the host reads it while it waits,
# and a write that meets its read fails.
function Done([string]$id) {
    $staged = Join-Path $out 'done.tmp'
    for ($try = 0; $try -lt 50; $try++) {
        try {
            Set-Content $staged $id -ErrorAction Stop
            Move-Item $staged (Join-Path $out 'done.txt') -Force -ErrorAction Stop
            return
        } catch {
            Start-Sleep -Milliseconds 100
        }
    }
}

$cmdFile = Join-Path $out 'cmd.txt'
while ($true) {
    if (Test-Path $cmdFile) {
        Start-Sleep -Milliseconds 200   # let the host finish writing
        $lines = Get-Content $cmdFile
        Remove-Item $cmdFile -Force
        foreach ($line in $lines | Select-Object -Skip 1) {
            $verb, $x, $y = $line -split ' '
            switch ($verb) {
                'shot'  { Shot $x }
                'click' { Click ([int]$x) ([int]$y) }
                'move'  { [Native]::SetCursorPos([int]$x, [int]$y) | Out-Null }
                'wait'  { Start-Sleep -Milliseconds ([int]$x) }
                'helper' {
                    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $desk 'assets\pointer-helper.ps1')
                }
            }
        }
        Done $lines[0]
    }
    Start-Sleep -Milliseconds 250
}
