#!/bin/bash
# Database initialization script for Docker container

set -e

echo "Waiting for PostgreSQL to start..."
until pg_isready -h db -p 5432 -U ${POSTGRES_USER}; do
  echo "Waiting for database connection..."
  sleep 2
done

echo "PostgreSQL is ready!"

echo "Running migrations..."
for migration in /docker-entrypoint-initdb.d/migrations/*.sql; do
    echo "Applying migration: $(basename $migration)"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$migration"
done

echo "Running seeds (if any)..."
for seed in /docker-entrypoint-initdb.d/seeds/*.sql; do
    if [ -f "$seed" ]; then
        echo "Applying seed: $(basename $seed)"
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$seed"
    fi
done

echo "Database initialization complete!"
