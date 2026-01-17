# CSV File Storage Setup

This backend now includes a CSV file storage system with HTTPS support.

## Features

- **Database storage**: CSV files are stored in PostgreSQL database
- **HTTPS endpoint**: `/csv/get-summary` endpoint accessible via HTTPS
- **File upload**: Upload CSV files via `/csv/upload` endpoint

## Setup Instructions

### 1. Run Database Migration

Apply the database migration to create the `csv_files` table:

```bash
cd api
alembic upgrade head
```

### 2. Generate SSL Certificates for HTTPS

**On Windows (PowerShell):**
```powershell
cd api
.\generate_ssl_cert.ps1
```

**On Linux/Mac:**
```bash
cd api
chmod +x generate_ssl_cert.sh
./generate_ssl_cert.sh
```

**Manual (if OpenSSL is installed):**
```bash
openssl req -x509 -newkey rsa:4096 \
  -keyout localhost-key.pem \
  -out localhost.pem \
  -days 365 \
  -nodes \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

This will create:
- `localhost-key.pem` (private key)
- `localhost.pem` (certificate)

### 3. Start the Server

The server will automatically use HTTPS if the certificates are found:

```bash
cd api
python main.py
```

Or set environment variables:
```bash
$env:BLINDSIGHTED_API_PORT=8000
$env:SSL_KEYFILE="localhost-key.pem"
$env:SSL_CERTFILE="localhost.pem"
python main.py
```

The server will run on `https://localhost:8000` (or `http://localhost:8000` if certificates are not found).

## API Endpoints

### GET `/csv/get-summary`

Returns the latest CSV file from the database.

**Response:**
```json
{
  "id": "uuid",
  "filename": "example.csv",
  "content": "col1,col2\nval1,val2",
  "file_size_bytes": 20,
  "created_at": "2026-01-20T12:00:00Z",
  "updated_at": "2026-01-20T12:00:00Z"
}
```

**Example (HTTPS):**
```bash
curl -k https://localhost:8000/csv/get-summary
```

### POST `/csv/upload`

Upload a CSV file to the database.

**Request:**
- Content-Type: `multipart/form-data`
- Body: CSV file

**Example:**
```bash
curl -k -X POST https://localhost:8000/csv/upload \
  -F "file=@example.csv"
```

## Notes

- The `-k` flag in curl is needed for self-signed certificates
- Browsers will show a security warning for self-signed certificates - this is normal for localhost development
- For production, use proper SSL certificates from a Certificate Authority
