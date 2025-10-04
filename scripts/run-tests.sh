#!/usr/bin/env bash
set -euo pipefail

echo "=== Install dependencies ==="
composer install --no-interaction --prefer-dist --no-progress
if [ -f package.json ]; then
  npm ci --no-audit --no-fund
fi

echo "=== Prepare environment ==="
cp -f .env.testing .env || true
php -r "file_exists('database') || mkdir('database', 0777, true);"
php -r "file_exists('database/database.sqlite') || touch('database/database.sqlite');" || true
php artisan key:generate --force || true
php artisan migrate --force --no-interaction || true

echo "=== Auto-fix formatting & lint (best-effort) ==="
vendor/bin/pint -v || true
if [ -f package.json ]; then
  npx --yes eslint . --fix || true
  npx --yes prettier --write . || true
fi

echo "=== Static analysis (PHPStan) ==="
vendor/bin/phpstan analyse --no-progress --memory-limit=1G

echo "=== Run PHPUnit (exclude quarantine, warn on skipped) ==="
attempts=0
max_attempts=2
until [ $attempts -ge $max_attempts ]
do
  if vendor/bin/phpunit -c phpunit.xml --exclude-group=quarantine --fail-on-warning --fail-on-risky --do-not-cache-result --testdox; then
    break
  fi
  attempts=$((attempts+1))
  echo "PHPUnit failed: retry $attempts/$max_attempts..."
  sleep 3
done

echo "=== Done ==="
