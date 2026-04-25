# ⚡ SQLite + PythonAnywhere - 5 Minute Quick Start

## Commands in Order

**In PythonAnywhere Bash Console:**

```bash
# 1. Clone project
cd ~
git clone <your-repo-url> tahfeed
cd tahfeed

# 2. Create virtualenv (auto-activated)
mkvirtualenv --python=/usr/bin/python3.10 tahfeed

# 3. Install dependencies
pip install --upgrade pip
pip install -q -r requirements.txt

# 4. Setup database
python manage.py migrate
python manage.py createsuperuser

# 5. Prepare static files
python manage.py collectstatic --noinput
```

## PythonAnywhere Dashboard Setup

**Web Tab → Your Web App:**

1. **Virtualenv:** `/home/yourusername/tahfeed`
2. **Static files:**
   - URL: `/static/`
   - Directory: `/home/yourusername/tahfeed/staticfiles`
3. **Reload** (green button)

## Test

- Visit: `https://yourusername.pythonanywhere.com`
- Admin: `https://yourusername.pythonanywhere.com/admin`

## If Error

```bash
tail -100 /var/log/yourusername.pythonanywhere.com.error.log
```

---

## Files Needed

- ✅ `requirements.txt` (dependencies)
- ✅ `myproject/settings.py` (Django config)
- ✅ `manage.py` (Django CLI)
- ✅ All app code

## That's It!

Your SQLite database deploys with your code. No MySQL setup needed.

---

**Full Guide:** See `PYTHONANYWHERE_SQLITE_GUIDE.md`  
**Checklist:** See `SQLITE_DEPLOYMENT_CHECKLIST.md`  
**Troubleshooting:** Check error logs: `tail /var/log/yourusername.pythonanywhere.com.error.log`

**Ready? Let's deploy! 🚀**
