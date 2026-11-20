# Test server

The test server lets stakeholders try SyRH before each milestone ships. It pulls the code from
GitHub by hand for now; a CI/CD pipeline will later run the same update script.

| | |
| --- | --- |
| Machine | Ubuntu 26.04 on the local network, `192.168.1.67` |
| Address | <http://192.168.1.67:8080> (port 80 belongs to the GLPI container already on the machine) |
| Code | `/srv/syrh`, a clone of `https://github.com/ArmandoSudi/SyRH.git` (public, so no key), owned by `armando` |
| Backend | gunicorn on `127.0.0.1:8001`, systemd unit `syrh` ([`deploy/syrh.service`](../deploy/syrh.service)) |
| Frontend | the built Vue app (`frontend/dist`), served by nginx with `/api`, `/admin` and `/static` ([`deploy/nginx-syrh.conf`](../deploy/nginx-syrh.conf)) |
| Database | PostgreSQL 18, database and role `syrh`, local only |
| Secrets | `/srv/syrh/backend/.env` and `~/syrh-secrets.env`, both readable by `armando` only, never committed |

## Update the server

Push the branch to GitHub, then on the server:

```bash
/srv/syrh/deploy/update.sh main
```

The script resets `/srv/syrh` to `origin/<branch>`, installs the backend dependencies, migrates,
collects the static files, builds the frontend, reinstalls the systemd unit and the nginx site,
and restarts both. It stops at the first error. Django's `check --deploy` only prints a note:
it reports the missing HTTPS and the console email backend, both expected on this server for now. A branch other than `main` can be shown to the
stakeholders the same way.

## What was installed once

These steps were done by hand the first time; they don't need repeating for an update.

1. **System packages**: `nodejs`, `npm`, `postgresql`, `nginx`, `git`, `build-essential`,
   `pipx`, then `pipx install uv` for `armando`.
2. **Database**: role `syrh` with a generated password, database `syrh` owned by it, and the
   `btree_gist` extension (the reference tables' exclusion constraints need it).
3. **Code**: `/srv/syrh` created, owned by `armando`, and the repository cloned into it over
   HTTPS. If the repository becomes private, add a read-only deploy key under Settings → Deploy
   keys and switch `origin` to the SSH address.
4. **Access**: the developer's machine signs in to `armando` with an SSH key, and `armando` has
   sudo without a password (`/etc/sudoers.d/armando-setup`), which `update.sh` needs.
5. **Configuration**: `/srv/syrh/backend/.env`:

   ```ini
   DJANGO_SECRET_KEY=<generated>
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=192.168.1.67,localhost
   DJANGO_SECURE_COOKIES=False
   DATABASE_URL=postgres://syrh:<generated>@localhost:5432/syrh
   ```

   `DJANGO_SECURE_COOKIES=False` because the server has no HTTPS yet: without it the browser
   would never send the session cookie back, and sign-in would fail. Remove it once the server
   has a certificate.
6. **Firewall**: `ufw allow 8080/tcp`.
7. **First deployment**: `deploy/update.sh main`.
8. **Demo data**: the demo accounts and reference data, so stakeholders have something to try.
   The `create_demo_*` commands refuse to run without `DEBUG`, so they are run once with it
   forced on for that command only:

   ```bash
   cd /srv/syrh/backend
   . ~/syrh-secrets.env
   export DJANGO_DEBUG=True
   uv run --no-sync python manage.py create_demo_users --password "$DEMO"
   for c in organisation classification fonctions types_contrat pieces sorties banques parametres; do
     uv run --no-sync python manage.py create_demo_$c
   done
   ```

   The demo accounts' password is `DEMO` in `~/syrh-secrets.env` on the server, different from
   the one on development machines.

## Troubleshooting

| Symptom | Look at |
| --- | --- |
| 502 Bad Gateway | `sudo systemctl status syrh` and `sudo journalctl -u syrh -n 50` |
| Page not found or old screens | Did `update.sh` finish? `ls /srv/syrh/frontend/dist` |
| Sign-in loops back to the login page | `DJANGO_SECURE_COOKIES=False` missing from `.env` while the site is served over HTTP |
| 400 Bad Request | The address used is not in `DJANGO_ALLOWED_HOSTS` |
| nginx errors | `sudo nginx -t` and `sudo tail /var/log/nginx/error.log` |
