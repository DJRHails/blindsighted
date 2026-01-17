# CSV Endpoint URLs

## HTTPS Endpoint (Recommended)

The CSV endpoints are accessible via HTTPS on port 8000:

### Get Latest CSV File
```
https://localhost:8000/csv/get-summary
```

**Full URL:**
```
https://localhost:8000/csv/get-summary
```

**Example using curl:**
```bash
curl -k https://localhost:8000/csv/get-summary
```

**Example using PowerShell:**
```powershell
Invoke-WebRequest -Uri "https://localhost:8000/csv/get-summary" -SkipCertificateCheck
```

### Upload CSV File
```
https://localhost:8000/csv/upload
```

**Full URL:**
```
https://localhost:8000/csv/upload
```

**Example using curl:**
```bash
curl -k -X POST https://localhost:8000/csv/upload -F "file=@example.csv"
```

**Example using PowerShell:**
```powershell
$file = Get-Item "example.csv"
Invoke-WebRequest -Uri "https://localhost:8000/csv/upload" -Method Post -Form @{file=$file} -SkipCertificateCheck
```

## HTTP Endpoint (Fallback)

If SSL certificates are not found, the server will run on HTTP:

```
http://localhost:8000/csv/get-summary
http://localhost:8000/csv/upload
```

## Interactive API Documentation

Once the server is running, you can access the interactive API documentation:

- **Swagger UI (HTTPS):** https://localhost:8000/docs
- **ReDoc (HTTPS):** https://localhost:8000/redoc

## Important Notes

1. **Self-Signed Certificate Warning:** Browsers and some HTTP clients will show a security warning for self-signed certificates. This is normal for localhost development.

2. **Skip Certificate Check:** When using `curl` or `Invoke-WebRequest`, you may need to:
   - Use `-k` flag with curl (skips certificate verification)
   - Use `-SkipCertificateCheck` with PowerShell's `Invoke-WebRequest`

3. **Port Configuration:** The default port is 8000. You can change it by setting the environment variable:
   ```powershell
   $env:BLINDSIGHTED_API_PORT=8001
   ```

4. **Server Status:** Check if the server is running:
   ```
   https://localhost:8000/
   ```
   Should return: `{"message":"Welcome to Blindsighted API","status":"healthy"}`
