# Runs INSIDE Windows Sandbox for the exhibition test in
# test_autocontinue_game.py, started hidden by the agent's `helper` command.
# As each button autocontinue acts on shows (Continue; Return under the
# Halftime or Results label), it sets the pointer before autocontinue's next
# scan: it leaves the pointer on a quarter of them, lights half (a move onto
# it, then 1 px) and moves the pointer away from a quarter. It leaves only one
# the pointer is already on, unlit, as it opened under it, so the left share
# stays under a quarter when the game gives too few. Each one goes to
# out\helper.txt as
# "<button> <action> <ms> <on|off>": ms how long the button had been up at
# most, and whether the pointer is on the button after. After acting it waits
# for the button to go.
#
# -Screen FILE looks once at a saved screenshot of the primary screen, with
# the game window at -Left, -Top, and prints what it sees: a check of the
# matching outside the sandbox.

param([string]$Screen, [int]$Left, [int]$Top)

$desk = 'C:\Users\WDAGUtilityAccount\Desktop'
$out = Join-Path $desk 'out'
$images = Join-Path (Split-Path $PSCommandPath) 'images'

Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public class Needle {
    public double[] Centered;
    public double Norm;
    public int Width, Height;
}

public class Sighting {
    public string Name { get; set; }
    public int X { get; set; }  // the middle
    public int Y { get; set; }
    public int Width { get; set; }
    public int Height { get; set; }
}

public static class Seen {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] static extern bool GetCursorPos(out POINT point);

    [StructLayout(LayoutKind.Sequential)]
    struct POINT { public int X, Y; }

    // Whether the pointer is on the button whose middle is at x, y.
    public static bool PointerOn(int x, int y, int width, int height) {
        POINT p;
        if (!GetCursorPos(out p)) return false;
        return Math.Abs(p.X - x) * 2 < width && Math.Abs(p.Y - y) * 2 < height;
    }
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    static extern IntPtr FindWindow(string cls, string title);
    [DllImport("dwmapi.dll")]
    static extern int DwmGetWindowAttribute(IntPtr hwnd, int attribute, out RECT rect, int size);

    [StructLayout(LayoutKind.Sequential)]
    struct RECT { public int Left, Top, Right, Bottom; }

    // Wider than the game window, so a frame a few pixels off still holds it.
    public const int GrabWidth = 700, GrabHeight = 560;

    // The game window's top-left, as drawn (no invisible frame); false
    // while there is none.
    public static bool Window(string title, out int left, out int top) {
        left = top = 0;
        IntPtr hwnd = FindWindow(null, title);
        if (hwnd == IntPtr.Zero) return false;
        RECT rect;
        if (DwmGetWindowAttribute(hwnd, 9, out rect, Marshal.SizeOf(typeof(RECT))) != 0) return false;
        left = rect.Left;
        top = rect.Top;
        return true;
    }

    public static Bitmap Grab(int left, int top) {
        Bitmap shot = new Bitmap(GrabWidth, GrabHeight, PixelFormat.Format24bppRgb);
        using (Graphics g = Graphics.FromImage(shot)) {
            g.CopyFromScreen(left, top, 0, 0, shot.Size);
        }
        return shot;
    }

    // Gray as OpenCV makes it from RGB, so scores match autocontinue's.
    public static byte[] Gray(Bitmap bitmap) {
        Bitmap rgb = bitmap.Clone(new Rectangle(0, 0, bitmap.Width, bitmap.Height), PixelFormat.Format24bppRgb);
        BitmapData data = rgb.LockBits(new Rectangle(0, 0, rgb.Width, rgb.Height), ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
        byte[] raw = new byte[data.Stride * rgb.Height];
        Marshal.Copy(data.Scan0, raw, 0, raw.Length);
        rgb.UnlockBits(data);
        byte[] gray = new byte[rgb.Width * rgb.Height];
        for (int y = 0; y < rgb.Height; y++) {
            for (int x = 0; x < rgb.Width; x++) {
                int i = y * data.Stride + x * 3;  // B, G, R
                gray[y * rgb.Width + x] = (byte)((raw[i + 2] * 4899 + raw[i + 1] * 9617 + raw[i] * 1868 + 8192) >> 14);
            }
        }
        rgb.Dispose();
        return gray;
    }

    public static Needle Load(string path) {
        using (Bitmap bitmap = new Bitmap(path)) {
            byte[] gray = Gray(bitmap);
            Needle needle = new Needle();
            needle.Width = bitmap.Width;
            needle.Height = bitmap.Height;
            double mean = 0;
            foreach (byte b in gray) mean += b;
            mean /= gray.Length;
            needle.Centered = new double[gray.Length];
            for (int i = 0; i < gray.Length; i++) {
                needle.Centered[i] = gray[i] - mean;
                needle.Norm += needle.Centered[i] * needle.Centered[i];
            }
            return needle;
        }
    }

    // The best normalized correlation (OpenCV's TM_CCOEFF_NORMED) of the
    // needle with its top-left within `dx`, `dy` of (x, y) on the grab; the
    // middle of that spot in `mx`, `my`.
    public static double Best(byte[] screen, Needle needle, int x, int y, int dx, int dy, out int mx, out int my) {
        double best = -1;
        mx = my = 0;
        int n = needle.Width * needle.Height;
        for (int top = Math.Max(0, y - dy); top <= y + dy && top + needle.Height <= GrabHeight; top++) {
            for (int left = Math.Max(0, x - dx); left <= x + dx && left + needle.Width <= GrabWidth; left++) {
                double sum = 0, squares = 0, product = 0;
                for (int row = 0; row < needle.Height; row++) {
                    int at = (top + row) * GrabWidth + left;
                    int k = row * needle.Width;
                    for (int col = 0; col < needle.Width; col++) {
                        double v = screen[at + col];
                        sum += v;
                        squares += v * v;
                        product += v * needle.Centered[k + col];
                    }
                }
                double variance = squares - sum * sum / n;
                if (variance <= 0 || needle.Norm <= 0) continue;
                double score = product / Math.Sqrt(variance * needle.Norm);
                if (score > best) {
                    best = score;
                    mx = left + needle.Width / 2;
                    my = top + needle.Height / 2;
                }
            }
        }
        return best;
    }
}
'@

[Seen]::SetProcessDPIAware() | Out-Null

function Needle([string]$name) { [Seen]::Load((Join-Path $images "$name.png")) }
$continue = Needle 'continue_button'
$labels = @{ 'Halftime' = (Needle 'halftime_label'); 'Results' = (Needle 'results_label') }
$returns = (Needle 'return_button'), (Needle 'return_highlight_button')

# Where each shows, as the top-left of its image in the game window, as
# autocontinue's test screenshots crop it, give or take a frame of a few
# pixels: Continue's box moves up and down with its text (its middle seen
# from 134 to 194); the labels and Return stay put. Matched as autocontinue
# does: 0.8, and Return, under the game's pointer, 0.6.
$continueAt = @{ X = 327; Y = 153; DY = 45 }
$labelAt = @{ 'Halftime' = @{ X = 521; Y = 26 }; 'Results' = @{ X = 513; Y = 27 } }
$returnAt = @{ X = 532; Y = 436 }
$margin = 15

# What shows on one grab of the game window: a Sighting, or $null.
function Look([byte[]]$gray) {
    $mx = 0; $my = 0
    foreach ($name in 'Results', 'Halftime') {
        $at = $labelAt[$name]
        if ([Seen]::Best($gray, $labels[$name], $at.X, $at.Y, $margin, $margin, [ref]$mx, [ref]$my) -ge 0.8) {
            foreach ($needle in $returns) {
                if ([Seen]::Best($gray, $needle, $returnAt.X, $returnAt.Y, $margin, $margin, [ref]$mx, [ref]$my) -ge 0.6) {
                    return [Sighting]@{ Name = 'Return'; X = $mx; Y = $my; Width = $needle.Width; Height = $needle.Height }
                }
            }
            return $null
        }
    }
    if ([Seen]::Best($gray, $continue, $continueAt.X, $continueAt.Y, $margin, $continueAt.DY, [ref]$mx, [ref]$my) -ge 0.8) {
        return [Sighting]@{ Name = 'Continue'; X = $mx; Y = $my; Width = $continue.Width; Height = $continue.Height }
    }
    return $null
}

if ($Screen) {
    $bitmap = New-Object System.Drawing.Bitmap $Screen
    $grab = $bitmap.Clone((New-Object System.Drawing.Rectangle $Left, $Top, ([Seen]::GrabWidth), ([Seen]::GrabHeight)), $bitmap.PixelFormat)
    $seen = Look ([Seen]::Gray($grab))
    if ($seen) { "$($seen.Name) $($seen.X) $($seen.Y)" } else { 'nothing' }
    return
}

$title = "Front Page Sports Football Pro '98"
$log = Join-Path $out 'helper.txt'
# What it has done so far, to keep the shares at a half, a quarter and a
# quarter.
$done = @{ 'light' = 0; 'away' = 0; 'leave' = 0 }
$acted = $null
# The last grab with no button to act on: a button is at most this old when
# the helper acts on it.
$clear = [DateTime]::UtcNow
while ($true) {
    Start-Sleep -Milliseconds 100
    $left = 0; $top = 0
    if (-not [Seen]::Window($title, [ref]$left, [ref]$top)) { continue }
    $grab = [Seen]::Grab($left, $top)
    $seen = Look ([Seen]::Gray($grab))
    $grab.Dispose()
    if ($acted) {
        # Still up: wait for it to go before the next one.
        if ($seen -and $seen.Name -eq $acted) { continue }
        $acted = $null
    }
    if (-not $seen) {
        $clear = [DateTime]::UtcNow
        continue
    }
    $x = $left + $seen.X; $y = $top + $seen.Y
    $count = $done['light'] + $done['away'] + $done['leave'] + 1
    if ([Seen]::PointerOn($x, $y, $seen.Width, $seen.Height) -and $done['leave'] -lt $count / 4) {
        # Already under the pointer, unlit: leave it.
        $action = 'leave'
    } elseif ($done['light'] -lt 2 * ($done['away'] + 1)) {
        $action = 'light'
    } else {
        $action = 'away'
    }
    $done[$action]++
    switch ($action) {
        'light' {
            [Seen]::SetCursorPos($x, $y) | Out-Null
            Start-Sleep -Milliseconds 50
            [Seen]::SetCursorPos($x + 1, $y) | Out-Null
        }
        # A blank spot at the window's top left, clear of every button.
        'away' { [Seen]::SetCursorPos($left + 20, $top + 60) | Out-Null }
    }
    $late = [int]([DateTime]::UtcNow - $clear).TotalMilliseconds
    $on = if ([Seen]::PointerOn($x, $y, $seen.Width, $seen.Height)) { 'on' } else { 'off' }
    [IO.File]::AppendAllText($log, "$($seen.Name) $action $late $on`r`n")
    $acted = $seen.Name
}
