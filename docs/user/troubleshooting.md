# Troubleshooting

## Common Issues

### 1. "Failed to connect to backend"

**Symptoms**: Frontend shows connection error, API unreachable.

**Solutions**:
- Verify the backend is running: `curl http://localhost:8000/health`
- Check the port is not in use: `lsof -i :8000`
- Verify Python environment has all dependencies: `pip install -r src/backend/requirements.txt`
- Check logs: `tail -f logs/healthcentral.log`

### 2. "Authentication failed" or 401 errors

**Symptoms**: Login fails or API returns 401.

**Solutions**:
- Verify correct password (passwords are case-sensitive)
- Check if profile is locked (unlock first)
- Token may have expired (auto-lock after 15 min) — log in again
- If rate limited (429), wait for the `Retry-After` duration

### 3. Document import fails

**Symptoms**: Upload completes but no observations extracted.

**Solutions**:
- Ensure the file is a supported format (PDF, PNG, JPG, JPEG)
- Check file size is under 50 MB
- For images, ensure OCR is enabled (`OCR_ENABLED=true`) and Tesseract installed
- Check if the document is a lab report (non-lab documents won't extract observations)
- Review backend logs for extraction errors

### 4. SQLCipher errors on startup

**Symptoms**: Database initialization fails, encryption errors.

**Solutions**:
- Install SQLCipher: `sudo apt-get install libsqlcipher-dev`
- macOS: `brew install sqlcipher`
- Verify installation: `python -c "import pysqlcipher3; print('OK')"`
- For development without encryption: set `DATABASE_ENCRYPTION_REQUIRED=false`

### 5. Slow performance or high memory usage

**Symptoms**: App is sluggish, pages load slowly.

**Solutions**:
- Check model tier — lower tiers are faster
- Reduce concurrent requests if running multiple tabs
- Check disk space for the `data/` directory
- Restart the backend to clear in-memory caches
- Check `/health` endpoint for application status

### 6. Rate limiting (429 Too Many Requests)

**Symptoms**: API returns 429 status code.

**Solutions**:
- Wait for the duration in the `Retry-After` response header
- Default limit: 100 requests per 60 seconds
- Auth endpoints: 10 attempts per 60 seconds
- If hitting limits consistently, consider adjusting `API_RATE_LIMIT_MAX_REQUESTS`

### 7. AI assistant gives incorrect answers

**Symptoms**: Chat responses are inaccurate or not grounded.

**Solutions**:
- Verify your observations are correct (verify after import)
- Check verification status: the assistant uses verified data
- Try rephrasing your question
- For complex queries, use the panel interpretation feature instead

### 8. Data backup/restore issues

**Symptoms**: Backup fails or restore produces errors.

**Solutions**:
- Ensure sufficient disk space in the backup directory
- Verify backup integrity: `python scripts/backup.py --action verify`
- For restore, stop the application first
- Check `.bak` files if restore overwrote existing data
- See [Disaster Recovery Runbook](../compliance/disaster-recovery.md)

## Getting Help

### Logs

Application logs are in `logs/healthcentral.log`. Set `LOG_LEVEL=DEBUG` for
verbose output.

### Health Check

```bash
curl http://localhost:8000/health | python -m json.tool
```

Returns application status, mode, and version.

### Metrics

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/monitoring/metrics | python -m json.tool
```

Returns detailed performance metrics for debugging slow endpoints (auth required).
