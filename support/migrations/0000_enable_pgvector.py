"""
Migration 0000 — Enable pgvector PostgreSQL extension.

This MUST run before 0001_initial which creates the `vector` column type.
Without this, migrate fails with:
    django.db.utils.ProgrammingError: type "vector" does not exist

Safe to run multiple times (IF NOT EXISTS).
"""
from django.db import migrations


class Migration(migrations.Migration):

    # No dependencies — this is the very first migration to run
    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;",
        ),
    ]
