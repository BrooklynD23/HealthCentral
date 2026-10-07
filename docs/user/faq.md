# Frequently Asked Questions

## General

### What is HealthCentral?

HealthCentral is a local-first medical results companion that helps you track,
understand, and share your lab results. All data is encrypted and stored on your
device.

### Is my data sent to the cloud?

No. By default, all processing happens locally on your device. AI models run
locally. If you explicitly enable the optional external API feature, the app can
send the current question, relevant conversation context, and referenced lab
observations needed for the response. It does not upload your whole profile
database automatically, but selected health context can be sent to the external
provider after opt-in.

### What file formats are supported?

PDF lab reports and image files (PNG, JPG, JPEG). OCR for scans requires Tesseract,
**Document import (OCR)** enabled in Settings for your profile, and `OCR_ENABLED=true`
in the server `.env`.

### Can multiple people use the same installation?

Yes. Each person creates their own profile with a separate password. Each
profile has its own encrypted database — profiles cannot access each other's data.

### How do I delete my data?

Delete your profile through the app, or manually remove the vault file from
`data/vaults/`. The master database entry is cleaned up automatically.

## Security

### How is my data encrypted?

Profile databases use SQLCipher (AES-256 encryption). Your password is used to
derive the encryption key. The master database stores only profile metadata
(name, creation date), not health data.

### What happens if I forget my password?

When you create a profile, Asclexis shows a **one-time recovery code**. Store it
somewhere safe. While you can still sign in, you can create a new code (or a
first one, for a profile made before recovery codes existed) under **Settings →
Recovery code**. It asks for your password, and it replaces any earlier code.

If you forget your password, the recovery code is the only way back in: choose
**Use your recovery code** on the profile setup screen. Without a code the vault cannot
be opened. The password derives the encryption key, so there is no backdoor by
design. **Keep backups of your data** using the backup utility, and keep your
recovery code with them.

### Is HealthCentral HIPAA compliant?

HealthCentral implements many HIPAA technical safeguards (encryption at rest,
audit logging, access controls). However, HIPAA compliance depends on your
specific deployment context. See [HIPAA Controls](../compliance/hipaa-controls.md).

### How does rate limiting work?

All API endpoints are rate-limited to prevent abuse:
- General: 100 requests per 60 seconds
- Authentication: 10 attempts per 60 seconds
- Rate limit headers are included on every response

## Features

### How accurate is the document extraction?

Extraction accuracy depends on document quality and format. Always verify
extracted observations against your original document. Verified observations
are marked separately from unverified ones.

### Can I edit extracted values?

Yes. Use the verify/edit feature on any observation to correct values that
were extracted incorrectly.

### What AI models are used?

HealthCentral supports multiple model tiers:
- **Low tier**: Small, fast models suitable for any hardware
- **Mid tier**: Balanced performance and quality
- **High tier**: Best quality, requires powerful hardware

You can also configure external APIs (OpenAI, Anthropic) for cloud processing.

### What lab panels are supported?

Currently: Complete Blood Count (CBC), Comprehensive Metabolic Panel (CMP),
Lipid Panel, and Thyroid Panel. Individual analytes are supported regardless of
panel grouping.

### Can I export my data?

Yes, multiple formats:
- **Doctor Summary**: Formatted report for clinician visits
- **CSV**: Spreadsheet-compatible observation export
- **JSON**: Machine-readable complete export
- **Discussion Questions**: AI-generated questions for doctor visits

### Does the assistant have access to my full history?

The RAG assistant queries your observation history to provide grounded,
personalized answers. Verified observations are marked and should be preferred
for clinical confidence, but unverified extracted observations can still appear
in grounded context until you correct or verify them.

### What do the [Your Results] / [Reference] labels mean in assistant answers?

The assistant lists the sources behind an answer under **Sources**, below the answer. Where it marks a specific sentence, it uses a number in square brackets, such as [1]. Each source shows its title (for example "Your LDL Result" or "Medical Reference: LDL") or, when it has no title, one of these labels:
- **Your Results** — your own lab values from imported documents, including your latest result, normal range, and whether the value is trending up or down
- **Your Document** — a passage from a document you imported
- **Reference** — general medical knowledge from a trusted reference library

This dual-source approach means you can verify clinical facts against your actual measurements and cross-check general information against medical sources.

### Can I turn off the assistant's memory of past conversations?

Assistant Memory in **Settings** lets you view, add, edit, and delete stored memory items. The backend also has a per-profile memory toggle API, but the current Settings screen does not expose a separate on/off toggle.

## Technical

### What databases does HealthCentral use?

SQLite (master database) and SQLCipher (encrypted profile vaults). No external
database server required.

### Can I run HealthCentral on a server?

Yes. Set `APP_MODE=server` and configure `CORS_ORIGINS`, `JWT_SECRET`, and
other server settings. See the API documentation for details.

### How do I update HealthCentral?

Pull the latest code and run database migrations:
```bash
git pull
pip install -r src/backend/requirements.txt
cd src/frontend && npm install
```
Migrations run automatically on startup.

### How do I back up my data?

Use the backup utility:
```bash
python src/backend/scripts/backup.py --action backup --data-dir data/
```
See [Disaster Recovery](../compliance/disaster-recovery.md) for the full runbook.

### What ports does HealthCentral use?

- Backend API: port 8000 (configurable via `PORT`)
- Frontend dev server: port 3000
- In local mode, both bind to `127.0.0.1` only
