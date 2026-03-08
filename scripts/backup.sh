#!/usr/bin/env bash
set -euo pipefail

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="/opt/openbrain/backups/$STAMP"
mkdir -p "$BACKUP_DIR"

pg_dump "postgresql://openbrain:Pb4openbrain@127.0.0.1:5432/openbrain" > "$BACKUP_DIR/openbrain.sql"
tar -czf "$BACKUP_DIR/archive.tar.gz" /opt/openbrain/archive
cp /opt/openbrain/.env "$BACKUP_DIR/.env.backup"

echo "Backup complete: $BACKUP_DIR"

