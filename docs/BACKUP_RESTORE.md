# Backup and Restore

The Docker Compose stack stores PostgreSQL data in `postgres_data` and project files in `document_data`. Both must be backed up for a complete local recovery point. Backups are written under the ignored `backups/` directory and must not be committed.

## Create a backup

With the stack running:

```bash
./scripts/backup.sh
```

The script creates matching UTC-timestamped artifacts:

- `backups/loris-pmo-<timestamp>.dump`: PostgreSQL custom-format dump
- `backups/loris-pmo-documents-<timestamp>.tar.gz`: document-volume archive

It uses the database name/user already present inside the Compose database container and does not read or print passwords. Copy both artifacts to a protected location appropriate for the data sensitivity.

## Restore

Restore is destructive to the current local database and, when supplied, the current document volume. Review the paths first:

```bash
./scripts/restore.sh backups/loris-pmo-<timestamp>.dump   backups/loris-pmo-documents-<timestamp>.tar.gz
```

The script:

1. validates Docker, the input files, PostgreSQL dump structure, and archive paths;
2. displays the exact target and asks for `RESTORE` confirmation;
3. writes pre-restore database/document safety backups under `backups/`;
4. stops backend/frontend access, replaces the database schema, and restores the dump;
5. optionally replaces document storage from the matching archive;
6. restarts backend/frontend so Alembic and health checks run normally.

Use `--yes` only in a deliberate non-interactive recovery procedure after independently validating the paths. If restoration fails, the pre-restore artifacts remain available.

## Data-safety rules

Safe, volumes retained:

```bash
docker compose down
```

Destructive, both named volumes removed:

```bash
docker compose down -v
```

Do not use `-v` unless permanent deletion of the local PostgreSQL database and document storage is intended. Document storage is a Compose named volume (`document_data`), not a frontend/public directory or ordinary host folder.

A database dump without its matching document archive can restore document metadata whose files are absent. A document archive without its matching database can contain files that no restored record references. Keep matching timestamps together.

## Validation after restore

```bash
./scripts/status.sh
docker compose exec backend alembic current
```

Then log in and verify project counts, one document download, and one deterministic report. Do not make a Gemini call solely to validate restore.

## Object-storage and managed-database mode

The shell scripts intentionally cover the local Compose database and `DOCUMENT_STORAGE_BACKEND=local` only. `backup.sh` refuses to claim a complete backup when S3 storage is active; `restore.sh` refuses a document archive restore into S3. A database-only restore remains a separate operator procedure.

For a cloud-ready deployment, configure and test two independent recovery paths:

1. managed PostgreSQL point-in-time recovery and a portable `pg_dump --format=custom --no-owner --no-acl` export;
2. private object-storage versioning/lifecycle policy plus a provider inventory or copy to an independent protected bucket.

Provider snapshots are not a substitute for exports you have restored successfully. Keep database and object recovery points correlated by timestamp, verify object count and byte size, and test authorized downloads after recovery. Loris PMO does not automate cloud backups or local-to-object-storage migration.

## Integration encryption-key recovery

Back up `INTEGRATION_TOKEN_ENCRYPTION_KEY` separately from the database, with access controls matching other production secrets. Losing it makes existing OAuth ciphertext undecryptable. The application cannot recover provider tokens from the database alone; affected users must disconnect/reconnect providers (or an operator must restore the original key). Never print the key during a recovery test.
