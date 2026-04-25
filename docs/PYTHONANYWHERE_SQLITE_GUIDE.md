# 🚀 PythonAnywhere Deployment Guide - SQLite Edition

This guide shows how to deploy the Tahfeed Professional Website on PythonAnywhere using **SQLite database** (simple, no MySQL setup required).

---

## Why SQLite on PythonAnywhere?

✅ **Advantages:**
- No database server setup needed
- File-based database (easy backup)
- Zero configuration
- Suitable for small to medium applications
- Works perfectly on free tier PythonAnywhere

⚠️ **Limitations:**
- Limited concurrent users compared to MySQL
- Works best with < 100 daily active users
- Choose MySQL later if you need to scale

---

## Step 1: Create PythonAnywhere Account

1. Go to [pythonanywhere.com](https://www.pythonanywhere.com/)
2. Sign up for a free account
3. Verify your email
4. Log in to dashboard

---

## Step 2: Create Web App

1. Click **Web** tab in left menu
2. Click **Add a new web app**
3. Select **Manual configuration** 
4. Choose **Python 3.10** (or your preferred version)
5. Accept the domain name (e.g., `yourusername.pythonanywhere.com`)
6. Click through to create

Your web app is now created. Note your domain name.

---

## Step 3: Clone Your Project

Open **Bash console** in PythonAnywhere:

```bash
# Go to home directory
cd ~

# Clone your repository
git clone <your-repo-url> tahfeed

# Navigate to project
cd tahfeed

# List contents to verify
ls -la
```

---

## Step 4: Create Virtual Environment

```bash
# Create virtualenv
mkvirtualenv --python=/usr/bin/python3.10 tahfeed

# Virtualenv is automatically activated after creation
# (You'll see (tahfeed) at the beginning of your prompt)

# Verify activation
which python
```

---

## Step 5: Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all requirements
pip install -q -r requirements.txt
```

This installs Django and all dependencies listed in requirements.txt.

---

## Step 6: Create Database & Run Migrations

```bash
# Navigate to project directory (if not already there)
cd ~/tahfeed

# Run migrations to create database tables
python manage.py migrate

# You should see messages about migrations applied
```

The SQLite database (`db.sqlite3`) is now created in your project directory.

---

## Step 7: Create Superuser (Admin Account)

```bash
# Create admin account
python manage.py createsuperuser

# Follow the prompts:
# Username: (enter your admin username)
# Email: (enter your email)
# Password: (enter a strong password - min 8 chars)
# Password (again): (confirm password)
```

Remember these credentials - you'll need them to access `/admin/` on your live site.

---

## Step 8: Collect Static Files

```bash
# Collect all static files (CSS, images, images, etc.)
python manage.py collectstatic --noinput

# This creates a 'staticfiles' directory with all your assets
```

---

## Step 9: Configure Web App Settings

Go to **Web** tab:

### 9a: Set Virtualenv Path
- Scroll to **Virtualenv** section
- Enter: `/home/yourusername/tahfeed`
- Press Enter

### 9b: Configure Static Files
- Scroll down to **Static files** section
- Click **Add a new static files mapping**
- URL: `/static/`
- Directory: `/home/yourusername/tahfeed/staticfiles`
- Click **Add**

### 9c: Check WSGI File (Optional)
- The WSGI file should already be configured
- If needed, it's at: `/var/www/yourusername_pythonanywhere_com_wsgi.py`
- The default configuration is fine for Django

---

## Step 10: Reload Web App

1. In **Web** tab, click the green **Reload** button at the top
2. Wait 30 seconds for reload to complete
3. Visit your site: `https://yourusername.pythonanywhere.com`

You should see your Tahfeed application homepage!

---

## Step 11: Test Core Features

Visit your site and test:

- [ ] Homepage loads
- [ ] Admin panel: `https://yourusername.pythonanywhere.com/admin`
- [ ] Login works (use superuser account)
- [ ] Student/Teacher data displays
- [ ] Key features work
- [ ] CSS/Images load properly

---

## Step 12: Check Error Logs

If something doesn't work:

```bash
# View last 50 lines of error log
tail -50 /var/log/yourusername.pythonanywhere.com.error.log

# View last 100 lines
tail -100 /var/log/yourusername.pythonanywhere.com.error.log
```

---

## Customizing for Your Needs

### Add Custom Domain (Optional)

1. Register a domain (GoDaddy, Namecheap, etc.)
2. In **Web** tab, click **Add a domain**
3. Enter your domain name
4. Follow DNS setup instructions
5. SSL certificate auto-configures

### Set Custom Configuration

For production settings, create a `.env` file:

```bash
# Create .env file
cat > .env << EOF
SECRET_KEY=your-very-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com,yourdomain.com
EOF
```

Then update `myproject/settings.py` to read from it (optional enhancement).

---

## Managing Your Database

### Backup SQLite Database

```bash
# Backup database
cp ~/tahfeed/db.sqlite3 ~/tahfeed/db.sqlite3.backup

# Download to your computer (via Files tab)
# Or use: scp command if you have SSH access
```

### View Database via Django Shell

```bash
# Open Django shell
cd ~/tahfeed
python manage.py shell

# Check data
>>> from quran_center.models import Student
>>> Student.objects.count()
10

# Exit
>>> exit()
```

### Export Data as JSON

```bash
# Backup all data
python manage.py dumpdata > backup.json

# Backup specific app
python manage.py dumpdata quran_center > quran_center_backup.json
```

### Import Data into Database

```bash
# Restore from JSON backup
python manage.py loaddata backup.json
```

---

## Troubleshooting

### Issue: 500 Internal Server Error

**Solution:**
```bash
# Check error logs
tail -100 /var/log/yourusername.pythonanywhere.com.error.log

# Look for the actual error message
# Common issues:
# - Missing staticfiles directory (run collectstatic again)
# - Missing database (run migrate again)
# - Import errors (check pip install completed)
```

### Issue: Static Files Not Loading

**Solution:**
```bash
# Recollect static files
cd ~/tahfeed
python manage.py collectstatic --noinput --clear

# Then reload web app in Web tab
```

### Issue: Can't Connect to Database

**Solution:**
```bash
# Check if database exists
ls -la ~/tahfeed/db.sqlite3

# If missing, run migrations
python manage.py migrate

# If still issues, recreate:
rm ~/tahfeed/db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### Issue: Admin Panel Won't Load

**Solution:**
```bash
# Check migrations are applied
python manage.py showmigrations

# All should show [X] mark
# If not, run:
python manage.py migrate
```

---

## Useful Commands (Bash Console)

```bash
# Activate virtualenv (auto-done after mkvirtualenv)
source /home/yourusername/tahfeed/bin/activate

# Create superuser
python manage.py createsuperuser

# Check migrations status
python manage.py showmigrations

# Apply migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Run tests
python manage.py test

# Database shell
python manage.py dbshell

# Django shell
python manage.py shell

# View settings
python manage.py diffsettings

# Check for issues
python manage.py check
```

---

## Security Checklist

Before considering your site "live":

- [ ] Superuser password is STRONG (admin account critical)
- [ ] You have backed up `db.sqlite3`
- [ ] Error logs don't expose sensitive info
- [ ] HTTPS is working (PythonAnywhere provides SSL)
- [ ] You know how to restore from backup
- [ ] Admin URL is not publicized

---

## Regular Maintenance

### Daily
- Check error logs for issues: `tail /var/log/yourusername.pythonanywhere.com.error.log`

### Weekly
- Backup database: `cp db.sqlite3 db.sqlite3.backup`
- Test key features

### Monthly
- Review access logs
- Check database size: `du -h db.sqlite3`
- Update dependencies (if needed): `pip list --outdated`

---

## Scaling to MySQL (Later)

If your application grows and you need more users:

1. Create MySQL database on PythonAnywhere
2. Update `requirements.txt` with `mysqlclient`
3. Update `settings.py` to use MySQL
4. Dump data: `python manage.py dumpdata > backup.json`
5. Run migrations with MySQL
6. Load data: `python manage.py loaddata backup.json`

But for now, SQLite is perfect for your needs!

---

## Database Size Reference

```
Typical Size Growth:
- Fresh database: 50 KB
- 100 students: 200 KB
- 500 students: 500 KB
- 1000 students: 1 MB
```

SQLite works well up to ~50 MB without performance issues.

---

## Getting Help

### Error in logs?
```bash
tail -100 /var/log/yourusername.pythonanywhere.com.error.log
```
The error message will tell you exactly what's wrong.

### Django issue?
You can run management commands locally to test:
```bash
python manage.py shell
python manage.py check
```

### PythonAnywhere help?
Visit: https://www.pythonanywhere.com/help/

---

## Quick Summary

1. ✅ Create PythonAnywhere account
2. ✅ Clone project
3. ✅ Create virtualenv
4. ✅ `pip install -r requirements.txt`
5. ✅ `python manage.py migrate`
6. ✅ `python manage.py createsuperuser`
7. ✅ `python manage.py collectstatic --noinput`
8. ✅ Configure Web app (virtualenv + static files)
9. ✅ Reload web app
10. ✅ Test at your domain
11. ✅ Done! 🎉

**Estimated Time:** 30 minutes for complete setup

---

## Next Steps

1. Follow steps 1-12 above in order
2. Test your site thoroughly
3. Monitor error logs for first few days
4. Set up regular backups
5. Consider custom domain setup (optional)

---

**Deployment Ready!** Your SQLite database works perfectly on PythonAnywhere. No complex MySQL setup needed. Simple and reliable! ✨

---

*Last Updated: February 15, 2026*
*Django Version: 5.2.11*
*Python: 3.10+*
