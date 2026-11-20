#!/usr/bin/env bash
# Brings the test server up to date with a branch of the GitHub repository and
# restarts SyRH. Run on the server, from anywhere:  /srv/syrh/deploy/update.sh [branch]
# See docs/deployment.md.
set -euo pipefail

# The whole script is one function, read before it runs: the pull below may
# replace this very file.
main() {
  BRANCH="${1:-main}"
  APP=/srv/syrh
  export PATH="$HOME/.local/bin:$PATH"

  cd "$APP"
  git fetch --prune origin
  git checkout "$BRANCH"
  git reset --hard "origin/$BRANCH"

  echo "== Backend"
  cd "$APP/backend"
  uv sync --frozen --no-dev
  uv run --no-sync python manage.py migrate --noinput
  uv run --no-sync python manage.py collectstatic --noinput --clear >/dev/null
  uv run --no-sync python manage.py check
  # Informational: no HTTPS and no email yet on the test server (docs/deployment.md).
  uv run --no-sync python manage.py check --deploy --fail-level CRITICAL >/dev/null 2>&1 \
    || echo "check --deploy reports issues (expected without HTTPS and email)."

  echo "== Frontend"
  cd "$APP/frontend"
  npm ci --no-audit --no-fund
  npm run build-only

  echo "== Services"
  sudo install -m 644 "$APP/deploy/syrh.service" /etc/systemd/system/syrh.service
  sudo install -m 644 "$APP/deploy/nginx-syrh.conf" /etc/nginx/sites-available/syrh
  sudo ln -sf /etc/nginx/sites-available/syrh /etc/nginx/sites-enabled/syrh
  sudo systemctl daemon-reload
  sudo systemctl enable --now syrh nginx
  sudo systemctl restart syrh
  sudo nginx -t
  sudo systemctl reload nginx

  echo "SyRH $(git -C "$APP" rev-parse --short HEAD) deployed from $BRANCH."
}

main "$@"
