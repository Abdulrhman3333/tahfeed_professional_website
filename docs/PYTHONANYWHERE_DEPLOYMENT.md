# 🚀 Complete PythonAnywhere Deployment Guide

## Overview
This guide walks you through deploying the **Tahfeed Professional Website** on PythonAnywhere using SQLite database.

**Deployment Time:** ~30-45 minutes  
**Difficulty:** Beginner-friendly  
**Cost:** Free tier available

---

## Table of Contents
1. [Pre-Deployment Preparation](#1-pre-deployment-preparation)
2. [PythonAnywhere Account Setup](#2-pythonanywhere-account-setup)
3. [Upload Your Code](#3-upload-your-code)
4. [Virtual Environment Setup](#4-virtual-environment-setup)
5. [Database Configuration](#5-database-configuration)
6. [Static Files Setup](#6-static-files-setup)
7. [Web App Configuration](#7-web-app-configuration)
8. [Testing & Verification](#8-testing--verification)
9. [Production Settings](#9-production-settings)
10. [Troubleshooting](#10-troubleshooting)
11. [Maintenance & Backups](#11-maintenance--backups)

---

## 1. Pre-Deployment Preparation

### A. Local Testing
Before deploying, ensure your app works locally:

```bash
# Run development server
python manage.py runserver

# Test at http://127.0.0.1:8000/
# Verify all features work
```

### B. Prepare Your Repository
If using Git:

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Ready for deployment"

# Push to GitHub/GitLab/Bitbucket
git remote add origin <your-repo-url>
git push -u origin main
```

### C. Create Requirements File (if needed)
Your project already has `requirements.txt`. Verify it contains Django:

```bash
# Check if Django is listed
cat requirements.txt | grep -i django
```

---

## 2. PythonAnywhere Account Setup

### Step 1: Create Account
1. Visit [www.pythonanywhere.com](https://www.pythonanywhere.com/)
2. Click **Pricing & signup**
3. Choose **Create a Beginner account** (Free)
4. Fill in:
   - Username (this becomes part of your URL)
   - Email
   - Password
5. Verify your email address
6. Log in to your dashboard

### Step 2: Understand Your Free Tier Limits
- 1 web app at `yourusername.pythonanywhere.com`
- 512 MB disk space
- HTTP/HTTPS support (SSL included)
- Perfect for small to medium sites

---

## 3. Upload Your Code

### Option A: Using Git (Recommended)

**Step 1:** Open a **Bash console** from PythonAnywhere dashboard

**Step 2:** Clone your repository
```bash
# Navigate to home directory
cd ~

# Clone your repository
git clone https://github.com/yourusername/your-repo.git tahfeed

# Navigate into project
cd tahfeed

# Verify files are there
ls -la
```

### Option B: Upload Files Manually

**Step 1:** Click **Files** tab in PythonAnywhere

**Step 2:** Create directory
```bash
# In Files tab, navigate to home directory
# Create new directory: tahfeed
```

**Step 3:** Upload files
- Click **Upload a file**
- Upload your project files
- Or upload a ZIP and extract:
```bash
unzip tahfeed.zip
```

---

## 4. Virtual Environment Setup

### Step 1: Open Bash Console
From dashboard, click **Consoles** → **Bash**

### Step 2: Create Virtual Environment
```bash
# Navigate to project directory
cd ~/tahfeed

# Create virtual environment with Python 3.10
mkvirtualenv --python=/usr/bin/python3.10 tahfeed-env

# The environment will be activated automatically
# You'll see (tahfeed-env) in your prompt
```

### Step 3: Install Dependencies
```bash
# Upgrade pip first
pip install --upgrade pip

# Install all project dependencies
pip install -r requirements.txt

# This may take 5-10 minutes depending on your requirements
```

**Wait for installation to complete.** You'll see each package being installed.

---

## 5. Database Configuration

### Step 1: Run Migrations
```bash
# Ensure you're in the project directory
cd ~/tahfeed

# Activate virtual environment (if not already active)
workon tahfeed-env

# Run migrations to create database tables
python manage.py migrate
```

You should see output like:
```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, quran_center
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  ...
```

### Step 2: Create Superuser (Admin Account)
```bash
python manage.py createsuperuser
```

Follow the prompts:
```
Username: admin
Email address: your-email@example.com
Password: ******** (min 8 characters)
Password (again): ********
```

**Important:** Remember these credentials! You'll need them to access `/admin/`

### Step 3: Verify Database Created
```bash
# Check if database file exists
ls -la db.sqlite3

# Should show: db.sqlite3 with file size
```

---

## 6. Static Files Setup

### Step 1: Configure Static Root
Edit `myproject/settings.py`:

```bash
# Open file in PythonAnywhere editor or use nano
nano ~/tahfeed/myproject/settings.py
```

Add this line after `STATIC_URL`:
```python
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # Add this line
```

### Step 2: Collect Static Files
```bash
# Navigate to project directory
cd ~/tahfeed

# Collect all static files
python manage.py collectstatic --noinput
```

You should see:
```
Copying 'admin/css/...'
...
X static files copied to '/home/yourusername/tahfeed/staticfiles'.
```

---

## 7. Web App Configuration

### Step 1: Create Web App
1. Click **Web** tab in PythonAnywhere dashboard
2. Click **Add a new web app**
3. Choose your domain: `yourusername.pythonanywhere.com`
4. Select **Manual configuration**
5. Select **Python 3.10**
6. Click **Next**

### Step 2: Configure Source Code
In the **Web** tab:

1. Scroll to **Code** section
2. Set **Source code:** `/home/yourusername/tahfeed`
3. Set **Working directory:** `/home/yourusername/tahfeed`

### Step 3: Configure Virtual Environment
1. Scroll to **Virtualenv** section
2. Enter path: `/home/yourusername/.virtualenvs/tahfeed-env`
3. Press Enter

### Step 4: Configure WSGI File

Click on the WSGI configuration file link (usually `/var/www/yourusername_pythonanywhere_com_wsgi.py`)

**Delete all content** and replace with:

```python
import os
import sys

# Add your project directory to the sys.path
path = '/home/yourusername/tahfeed'
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variable to tell Django where settings are
os.environ['DJANGO_SETTINGS_MODULE'] = 'myproject.settings'

# Import Django's WSGI handler
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**Important:** Replace `yourusername` with your actual PythonAnywhere username!

Click **Save** (top right)

### Step 5: Configure Static Files Mapping

In the **Web** tab, scroll to **Static files** section:

Click **Enter URL** and **Enter path**:
- **URL:** `/static/`
- **Directory:** `/home/yourusername/tahfeed/staticfiles`

Click the checkmark to save.

### Step 6: Configure Media Files (Optional)
If you have media uploads:
- **URL:** `/media/`
- **Directory:** `/home/yourusername/tahfeed/media`

---

## 8. Testing & Verification

### Step 1: Reload Web App
In the **Web** tab, click the green **Reload** button at the top.

Wait 30 seconds for the app to reload.

### Step 2: Test Your Website
Visit: `https://yourusername.pythonanywhere.com`

You should see your homepage!

### Step 3: Test Admin Panel
Visit: `https://yourusername.pythonanywhere.com/admin`

Login with the superuser credentials you created.

### Step 4: Check Error Logs
If you get an error, check logs:

```bash
# In Bash console
tail -50 /var/log/yourusername.pythonanywhere.com.error.log
```

Read the error message carefully - it tells you exactly what's wrong.

### Step 5: Test Key Features
- [ ] Homepage loads
- [ ] Admin login works
- [ ] Student/Teacher pages work
- [ ] Forms submit correctly
- [ ] CSS and images load
- [ ] Navigation works

---

## 9. Production Settings

### Update Settings for Production

Edit `myproject/settings.py`:

```python
import os

# Security settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-tk3^ya)p#+kcc*6(tua-=_@nz!kam8q!v)ui&ee5%31q9(c%_w')

# Set DEBUG to False in production
DEBUG = False

# Add your domain to allowed hosts
ALLOWED_HOSTS = ['yourusername.pythonanywhere.com']
```

### Generate New Secret Key
```bash
# In Bash console
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and update `SECRET_KEY` in settings.py

### Reload Web App
After changes, click **Reload** in Web tab.

---

## 10. Troubleshooting

### Problem: "Something went wrong" or 500 Error

**Solution:**
```bash
# Check error logs
tail -100 /var/log/yourusername.pythonanywhere.com.error.log
```

Common causes:
- Wrong path in WSGI file
- Virtual environment not activated
- Missing migrations
- Incorrect ALLOWED_HOSTS

### Problem: Static Files Not Loading (No CSS)

**Solution:**
```bash
# Recollect static files
cd ~/tahfeed
python manage.py collectstatic --noinput --clear

# Verify static files mapping in Web tab:
# URL: /static/
# Directory: /home/yourusername/tahfeed/staticfiles
```

Then reload the web app.

### Problem: "DisallowedHost" Error

**Solution:**
Edit `settings.py`:
```python
ALLOWED_HOSTS = ['yourusername.pythonanywhere.com']
```

Reload web app.

### Problem: Database Errors

**Solution:**
```bash
# Check if database exists
ls -la ~/tahfeed/db.sqlite3

# If missing, run migrations
cd ~/tahfeed
python manage.py migrate
```

### Problem: Import Errors / Module Not Found

**Solution:**
```bash
# Activate virtual environment
workon tahfeed-env

# Reinstall requirements
pip install -r requirements.txt

# Verify Django is installed
pip show django
```

Update WSGI file to ensure correct virtualenv path.

### Problem: Permission Denied Errors

**Solution:**
```bash
# Fix permissions
chmod 644 ~/tahfeed/db.sqlite3
chmod 755 ~/tahfeed
```

---

## 11. Maintenance & Backups

### Regular Backups

**Daily Backup:**
```bash
# Backup database
cp ~/tahfeed/db.sqlite3 ~/backups/db_$(date +%Y%m%d).sqlite3

# Backup as JSON
cd ~/tahfeed
python manage.py dumpdata > ~/backups/backup_$(date +%Y%m%d).json
```

**Download Backup:**
1. Go to **Files** tab
2. Navigate to `backups/`
3. Click on file to download

### Updating Your App

```bash
# Pull latest code
cd ~/tahfeed
git pull origin main

# Activate virtual environment
workon tahfeed-env

# Install any new dependencies
pip install -r requirements.txt

# Run new migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Reload web app (in Web tab)
```

### Monitoring

**Check Error Logs:**
```bash
tail -50 /var/log/yourusername.pythonanywhere.com.error.log
```

**Check Access Logs:**
```bash
tail -50 /var/log/yourusername.pythonanywhere.com.access.log
```

**Database Size:**
```bash
du -h ~/tahfeed/db.sqlite3
```

---

## Quick Command Reference

```bash
# Activate virtual environment
workon tahfeed-env

# Navigate to project
cd ~/tahfeed

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# View errors
tail -100 /var/log/yourusername.pythonanywhere.com.error.log

# Backup database
cp db.sqlite3 ../db_backup.sqlite3

# Export data
python manage.py dumpdata > backup.json

# Import data
python manage.py loaddata backup.json

# Django shell
python manage.py shell

# Generate secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Custom Domain Setup (Optional)

### Step 1: Register Domain
Register a domain from providers like:
- Namecheap
- GoDaddy
- Google Domains

### Step 2: Configure DNS
Add CNAME record:
```
www.yourdomain.com → yourusername.pythonanywhere.com
```

### Step 3: Add Domain in PythonAnywhere
1. **Web** tab → **Add a new domain**
2. Enter: `www.yourdomain.com`
3. Follow instructions for DNS setup

### Step 4: Update Settings
```python
ALLOWED_HOSTS = [
    'yourusername.pythonanywhere.com',
    'www.yourdomain.com',
    'yourdomain.com'
]
```

---

## Security Checklist

Before going live:

- [ ] Set `DEBUG = False`
- [ ] Generate new `SECRET_KEY`
- [ ] Update `ALLOWED_HOSTS`
- [ ] Strong superuser password
- [ ] HTTPS enabled (automatic on PythonAnywhere)
- [ ] Regular backups configured
- [ ] Error logs monitored

---

## Support Resources

- **PythonAnywhere Help:** https://help.pythonanywhere.com/
- **PythonAnywhere Forums:** https://www.pythonanywhere.com/forums/
- **Django Docs:** https://docs.djangoproject.com/
- **Your Error Logs:** `/var/log/yourusername.pythonanywhere.com.error.log`

---

## Summary Checklist

- [ ] Created PythonAnywhere account
- [ ] Uploaded code (git clone or manual)
- [ ] Created virtual environment
- [ ] Installed requirements
- [ ] Ran migrations
- [ ] Created superuser
- [ ] Collected static files
- [ ] Created web app
- [ ] Configured WSGI file
- [ ] Set static files mapping
- [ ] Set virtualenv path
- [ ] Reloaded web app
- [ ] Tested website
- [ ] Updated production settings
- [ ] Set up backups

---

## You're Live! 🎉

Your Tahfeed website should now be accessible at:
**https://yourusername.pythonanywhere.com**

Monitor your error logs regularly and keep backups up to date!

---

*Last Updated: February 16, 2026*  
*Django Version: 5.2.11*  
*Python: 3.10+*  
*Platform: PythonAnywhere*
