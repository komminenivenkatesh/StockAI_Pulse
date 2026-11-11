$cloudflared = "$PSScriptRoot\cloudflared.exe"
if (-not (Test-Path $cloudflared)) {
    $cloudflared = "cloudflared"
}

Write-Host "`n=======================================================" -ForegroundColor Cyan
Write-Host "   Starting Public Cloudflare Tunnel..." -ForegroundColor Yellow
Write-Host "=======================================================`n" -ForegroundColor Cyan

# Start cloudflared in the background with metrics port
$port = 20241
$proc = Start-Process -FilePath $cloudflared -ArgumentList "tunnel", "--url", "http://127.0.0.1:5173", "--metrics", "127.0.0.1:$port" -PassThru -NoNewWindow

Write-Host "Connecting to Cloudflare edge network..." -ForegroundColor Gray

# Wait for hostname to be registered (poll metrics endpoint)
$hostname = $null
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:$port/quicktunnel" -ErrorAction SilentlyContinue -TimeoutSec 2
        if ($res.hostname) {
            $hostname = $res.hostname
            break
        }
    } catch {}
}

if ($hostname) {
    $publicUrl = "https://$hostname"
    Write-Host "`n==========================================================================" -ForegroundColor Green
    Write-Host "   PUBLIC URL READY:" -ForegroundColor White
    Write-Host "   $publicUrl" -ForegroundColor Cyan
    Write-Host "==========================================================================`n" -ForegroundColor Green
    
    try {
        Set-Clipboard $publicUrl
        Write-Host "(Copied to your clipboard!)" -ForegroundColor Green
    } catch {}
    
    Write-Host "Opening in browser..." -ForegroundColor Gray
    Start-Process $publicUrl
} else {
    Write-Host "Could not auto-detect URL, check the cloudflared output above." -ForegroundColor Yellow
}

Write-Host "`nKeep this window open to maintain your public tunnel." -ForegroundColor White
Write-Host "Press Ctrl+C to stop sharing.`n" -ForegroundColor Gray

$proc.WaitForExit()
