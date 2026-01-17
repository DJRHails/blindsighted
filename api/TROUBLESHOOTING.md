# Troubleshooting Guide

## Common Errors and Solutions

### 1. Migration Error: "Target database is not up to date"

**Error:**
```
alembic.util.exc.CommandError: Target database is not up to date
```

**Solution:**
```bash
cd api
alembic upgrade head
```

### 2. Import Error: "No module named 'models'"

**Error:**
```
ModuleNotFoundError: No module named 'models'
```

**Solution:**
Make sure you're running commands from the `api` directory:
```bash
cd api
python main.py
```

### 3. Database Connection Error

**Error:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution:**
- Check your database is running
- Verify `DATABASE_URL` in `.env` file is correct
- Default: `postgresql+psycopg://localhost/blindsighted`

### 4. SSL Certificate Error

**Error:**
```
Warning: SSL certificates not found. Running HTTP only.
```

**Solution:**
Generate SSL certificates:
```powershell
# Windows
cd api
.\generate_ssl_cert.ps1

# Linux/Mac
cd api
./generate_ssl_cert.sh
```

### 5. Migration Revision Error

**Error:**
```
alembic.util.exc.CommandError: Multiple heads detected
```

**Solution:**
Check current migration status:
```bash
cd api
alembic heads
alembic current
```

If there are multiple heads, merge them:
```bash
alembic merge heads -m "merge_csv_migration"
alembic upgrade head
```

### 6. Port Already in Use

**Error:**
```
OSError: [WinError 10048] Only one usage of each socket address
```

**Solution:**
- Change the port: `$env:BLINDSIGHTED_API_PORT=8001`
- Or stop the process using port 8000

### 7. CSV Router Not Found

**Error:**
```
404 Not Found: /csv/get-summary
```

**Solution:**
- Verify the router is included in `main.py`
- Check the server is running: `python main.py`
- Verify the endpoint: `https://localhost:8000/docs` (Swagger UI)

## Step-by-Step Setup Verification

1. **Check database connection:**
   ```bash
   cd api
   python -c "from database import engine; import asyncio; asyncio.run(engine.connect())"
   ```

2. **Check models are importable:**
   ```bash
   cd api
   python -c "from models import CSVFile; print('OK')"
   ```

3. **Check migration status:**
   ```bash
   cd api
   alembic current
   alembic heads
   ```

4. **Run migration:**
   ```bash
   cd api
   alembic upgrade head
   ```

5. **Start server:**
   ```bash
   cd api
   python main.py
   ```

6. **Test endpoint:**
   ```bash
   curl -k https://localhost:8000/csv/get-summary
   ```

## Getting Help

If you're still experiencing issues:

1. Check the full error message and stack trace
2. Verify all dependencies are installed: `pip install -r requirements.txt`
3. Check Python version: `python --version` (should be 3.11+)
4. Verify database is accessible and migrations are up to date
