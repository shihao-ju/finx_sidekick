# Test admin endpoint directly
# Usage: .\test_admin_endpoint.ps1

Write-Host "=== Testing /admin Endpoint ===" -ForegroundColor Cyan
Write-Host ""

$url = "https://finx.ai-builders.space/admin"

try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -MaximumRedirection 0 -ErrorAction SilentlyContinue
    
    Write-Host "✅ Direct Request:" -ForegroundColor Green
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor White
    Write-Host "   Content Length: $($response.Content.Length) bytes" -ForegroundColor White
    
    if ($response.Content -match "Scheduler Admin") {
        Write-Host "   ✅ Admin page content found!" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Admin page content NOT found" -ForegroundColor Red
    }
    
    # Check for redirects
    $location = $response.Headers.Location
    if ($location) {
        Write-Host "   ⚠️  Redirect detected: $location" -ForegroundColor Yellow
    }
    
} catch {
    if ($_.Exception.Response.StatusCode -eq 302 -or $_.Exception.Response.StatusCode -eq 301) {
        $location = $_.Exception.Response.Headers.Location
        Write-Host "❌ Redirect detected:" -ForegroundColor Red
        Write-Host "   Status: $($_.Exception.Response.StatusCode)" -ForegroundColor White
        Write-Host "   Location: $location" -ForegroundColor White
        Write-Host ""
        Write-Host "This means the server is redirecting /admin to another location." -ForegroundColor Yellow
    } else {
        Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Browser Testing Tips ===" -ForegroundColor Cyan
Write-Host "1. Try hard refresh: Ctrl + Shift + R" -ForegroundColor White
Write-Host "2. Try incognito/private mode" -ForegroundColor White
Write-Host "3. Clear browser cache" -ForegroundColor White
Write-Host "4. Check browser console for JavaScript errors" -ForegroundColor White
Write-Host "5. Try: https://finx.ai-builders.space/admin?nocache=$(Get-Date -Format 'yyyyMMddHHmmss')" -ForegroundColor White

