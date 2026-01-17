# Generate self-signed SSL certificate for localhost (PowerShell)
# Requires OpenSSL to be installed

$certName = "localhost"
$keyFile = "$certName-key.pem"
$certFile = "$certName.pem"

# Check if OpenSSL is available
$opensslPath = Get-Command openssl -ErrorAction SilentlyContinue
if (-not $opensslPath) {
    Write-Host "Error: OpenSSL is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Install OpenSSL from: https://slproweb.com/products/Win32OpenSSL.html" -ForegroundColor Yellow
    exit 1
}

# Generate certificate
openssl req -x509 -newkey rsa:4096 `
  -keyout $keyFile `
  -out $certFile `
  -days 365 `
  -nodes `
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

if ($LASTEXITCODE -eq 0) {
    Write-Host "SSL certificates generated successfully:" -ForegroundColor Green
    Write-Host "  - $keyFile (private key)" -ForegroundColor Cyan
    Write-Host "  - $certFile (certificate)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Note: You may need to accept the self-signed certificate in your browser." -ForegroundColor Yellow
} else {
    Write-Host "Error generating certificates" -ForegroundColor Red
    exit 1
}
