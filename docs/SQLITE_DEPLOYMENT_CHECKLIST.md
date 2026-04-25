# ✅ PythonAnywhere SQLite Deployment - Quick Checklist

## Account Setup
- [ ] Create PythonAnywhere account at pythonanywhere.com
- [ ] Verify email and log in
- [ ] Create web app (manual config, Python 3.10)
- [ ] Note your domain: `yourusername.pythonanywhere.com`

---

## Code Deployment
- [ ] Open Bash console on PythonAnywhere
- [ ] Clone project: `git clone <repo-url> tahfeed`
- [ ] Navigate to project: `cd ~/tahfeed`
- [ ] Create virtualenv: `mkvirtualenv --python=/usr/bin/python3.10 tahfeed`
- [ ] Upgrade pip: `pip install --upgrade pip`
- [ ] Install requirements: `pip install -q -r requirements.txt`

---

## Database Setup
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
  - [ ] Enter username
  - [ ] Enter email
  - [ ] Enter password (strong!)
  - [ ] Confirm password
- [ ] Verify database created: `ls -la db.sqlite3`

---

## Static Files
- [ ] Collect static files: `python manage.py collectstatic --noinput`
- [ ] Verify staticfiles directory created: `ls -la staticfiles/`

---

## Web App Configuration (PythonAnywhere Dashboard)

### Virtualenv
- [ ] Go to **Web** tab → select your web app
- [ ] Scroll to **Virtualenv** section
- [ ] Enter path: `/home/yourusername/tahfeed`
- [ ] Press Enter

### Static Files
- [ ] Scroll to **Static files** section
- [ ] Click **Add a new static files mapping**
- [ ] Enter:
  - [ ] URL: `/static/`
  - [ ] Directory: `/home/yourusername/tahfeed/staticfiles`
- [ ] Click **Add**

### Reload
- [ ] Click green **Reload** button at top
- [ ] Wait 30 seconds

---

## Testing
- [ ] Visit site: `https://yourusername.pythonanywhere.com`
- [ ] Homepage loads?
- [ ] Admin panel works: `/admin`
- [ ] Login works (superuser account)
- [ ] CSS/images load?
- [ ] Test main features

---

## Error Checking
- [ ] Check error logs: `tail -50 /var/log/yourusername.pythonanywhere.com.error.log`
- [ ] No critical errors?
- [ ] If 500 error, see PYTHONANYWHERE_SQLITE_GUIDE.md troubleshooting

---

## Backup Setup
- [ ] Create backup: `cp ~/tahfeed/db.sqlite3 ~/tahfeed/db.sqlite3.backup`
- [ ] Export data: `python manage.py dumpdata > backup.json`
- [ ] Store backups safely (download to computer)

---

## Optional: Custom Domain
- [ ] Register domain (GoDaddy, Namecheap, etc.)
- [ ] In **Web** tab, click **Add a domain**
- [ ] Enter domain name
- [ ] Follow DNS instructions
- [ ] SSL auto-configures
- [ ] Test domain works

---

## Final Security Check
- [ ] Superuser password is strong
- [ ] Database backed up
- [ ] Error logs reviewed
- [ ] HTTPS working
- [ ] You have restore plan

---

## Maintenance Schedule
- [ ] Daily: Check error logs
- [ ] Weekly: Backup database
- [ ] Monthly: Review access logs & test features

---

## Quick Commands Reference

```bash
# Activate virtualenv (next bash session)
source /home/yourusername/tahfeed/bin/activate

# View errors
tail -50 /var/log/yourusername.pythonanywhere.com.error.log

# Create superuser
python manage.py createsuperuser

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Backup database
cp db.sqlite3 db.sqlite3.backup

# Export all data
python manage.py dumpdata > backup.json

# Import data
python manage.py loaddata backup.json

# Check database
python manage.py dbshell

# Open Django shell
python manage.py shell

# Exit Django shell
>>> exit()
```

---

## Common Issues & Solutions

| Problem | Solution |
|---------|----------|
| 500 Error | `tail /var/log/yourusername.pythonanywhere.com.error.log` |
| Static files missing | `python manage.py collectstatic --noinput --clear` then reload |
| Database missing | `python manage.py migrate` |
| Can't login | Verify superuser created: `python manage.py createsuperuser` |
| Admin page 404 | Ensure migrations ran: `python manage.py migrate` |

---

## Status: Ready for Deployment ✅

All steps completed? Your site is live! Check it at:
👉 `https://yourusername.pythonanywhere.com`

---

**Having issues?** See **PYTHONANYWHERE_SQLITE_GUIDE.md** for detailed troubleshooting.

**Need more details?** Read **PYTHONANYWHERE_SQLITE_GUIDE.md** for complete guide.
