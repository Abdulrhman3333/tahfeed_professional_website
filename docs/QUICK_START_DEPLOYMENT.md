# 🚀 Quick Start Deployment Guide

## Choose Your Hosting Option

### Option 1: DigitalOcean or Linode (Recommended for beginners)

**Easiest Setup - Takes ~30 minutes**

```bash
# 1. Create a new Ubuntu 22.04 LTS droplet
# 2. SSH into your server:
ssh root@your_server_ip

# 3. Run the quick setup script:
cd /var/www
git clone <your-repo> tahfeed
cd tahfeed

# 4. Run initial setup
bash scripts/quick_deploy.sh

# 5. That's it! Your site is live
```

---

### Option 2: Docker Deployment (Most scalable)

**Perfect for modern hosting**

```bash
# 1. Install Docker and Docker Compose on your server

# 2. Copy .env.template to .env and fill in values:
cp .env.template .env
nano .env

# 3. Pull database backup (if migrating):
# (Copy your old database)

# 4. Start services:
docker-compose up -d

# 5. Run migrations:
docker-compose exec web python manage.py migrate

# 6. Create superuser:
docker-compose exec web python manage.py createsuperuser

# Done! Access at http://your_domain.com
```

---

### Option 3: PythonAnywhere (Simplest)

**No server management needed**

1. Sign up at pythanywhere.com
2. Upload your code
3. Configure in web app section
4. Set environment variables
5. Reload app
6. Done!

---

### Option 4: Heroku (Easy but has costs)

```bash
# Install Heroku CLI
npm install -g heroku

# Login
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set SECRET_KEY=your-key
heroku config:set DEBUG=False

# Deploy
git push heroku main

# Migrate
heroku run python manage.py migrate

# Done!
```

---

## Pre-Deployment Tasks (All Options)

### 1. Prepare Your Code

```bash
# Ensure all changes are committed
git status
git add .
git commit -m "Prepare for deployment"

# Generate new SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 2. Create Environment File

```bash
cp .env.template .env
# Edit .env with your actual values:
# - SECRET_KEY
# - ALLOWED_HOSTS (your domain)
# - Database credentials
# - Email settings
```

### 3. Test Locally

```bash
# In development environment
python manage.py check
python manage.py runserver 0.0.0.0:8000

# Visit http://localhost:8000
# Make sure everything works
```

---

## Step-by-Step Manual Deployment

### Server Setup (Ubuntu/Debian)

```bash
# Connect to your server
ssh root@your_server_ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install -y python3 python3-pip python3-venv

# Install Postgres
sudo apt install -y postgresql postgresql-contrib

# Install Nginx
sudo apt install -y nginx

# Install Git
sudo apt install -y git
```

### Setup PostgreSQL

```bash
sudo -u postgres psql

# Inside PostgreSQL:
CREATE DATABASE tahfeed_db;
CREATE USER tahfeed_user WITH PASSWORD 'your-password';
ALTER ROLE tahfeed_user SET client_encoding TO 'utf8';
ALTER ROLE tahfeed_user SET default_transaction_isolation TO 'read committed';
GRANT ALL PRIVILEGES ON DATABASE tahfeed_db TO tahfeed_user;
\q
```

### Deploy Your Project

```bash
# Create app directory
sudo mkdir -p /var/www/tahfeed
cd /var/www/tahfeed

# Clone project
sudo git clone <your-repo-url> .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Create .env file
cp .env.template .env
sudo nano .env  # Edit with your values

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Setup Gunicorn

```bash
# Test Gunicorn
gunicorn --bind 0.0.0.0:8000 myproject.wsgi:application

# Create service file
sudo nano /etc/systemd/system/gunicorn-tahfeed.service
```

Paste this content:
```ini
[Unit]
Description=Gunicorn for Tahfeed
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/tahfeed
ExecStart=/var/www/tahfeed/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/var/www/tahfeed/gunicorn.sock \
    myproject.wsgi:application

Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable service
sudo systemctl daemon-reload
sudo systemctl enable gunicorn-tahfeed
sudo systemctl start gunicorn-tahfeed
sudo systemctl status gunicorn-tahfeed
```

### Setup Nginx

```bash
# Copy Nginx config
sudo cp nginx.conf /etc/nginx/sites-available/tahfeed

# Enable site
sudo ln -s /etc/nginx/sites-available/tahfeed /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Setup SSL (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx

sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renew
sudo systemctl enable certbot.timer
```

---

## Verify Deployment

```bash
# Check services
sudo systemctl status gunicorn-tahfeed
sudo systemctl status nginx

# Check logs
tail -f /var/log/tahfeed/error.log
tail -f /var/log/tahfeed/access.log

# Test website
curl https://yourdomain.com

# Visit in browser
https://yourdomain.com
```

---

## After Going Live

### Daily Tasks
- [ ] Monitor error logs
- [ ] Check uptime
- [ ] Verify email delivery

### Weekly Tasks
- [ ] Review user feedback
- [ ] Check database size
- [ ] Review security logs

### Monthly Tasks
- [ ] Database optimization
- [ ] Dependency updates
- [ ] Performance review
- [ ] Backup verification

### Quarterly Tasks
- [ ] Security audit
- [ ] Disaster recovery drill
- [ ] Capacity planning

---

## Troubleshooting

### Site not loading
```bash
sudo nginx -t          # Check Nginx syntax
sudo systemctl status gunicorn-tahfeed  # Check Gunicorn
tail -f /var/log/nginx/error.log  # Check errors
```

### Database connection error
```bash
# Test database
sudo -u postgres psql -d tahfeed_db

# Check credentials in .env
cat /var/www/tahfeed/.env | grep DB
```

### Static files not loading
```bash
# Recollect static files
cd /var/www/tahfeed
source venv/bin/activate
python manage.py collectstatic --noinput --clear

# Check permissions
sudo chown -R www-data:www-data /var/www/tahfeed/staticfiles
```

### Email not sending
```bash
# Test email settings in .env
# Make sure SMTP credentials are correct
# Check firewall port 587 is open
```

---

## Important Files & Locations

```
/var/www/tahfeed/          # Project directory
/var/www/tahfeed/.env      # Environment variables (DO NOT COMMIT)
/var/www/tahfeed/venv/     # Python virtual environment
/var/www/tahfeed/staticfiles/   # Static files
/var/www/tahfeed/media/    # User uploads
/var/log/tahfeed/          # Application logs
/var/log/nginx/            # Web server logs
/etc/nginx/sites-available/tahfeed  # Nginx config
/etc/systemd/system/gunicorn-tahfeed.service  # Gunicorn service
```

---

## Useful Commands

```bash
# Restart all services
sudo systemctl restart gunicorn-tahfeed nginx

# View live logs
tail -f /var/log/tahfeed/error.log

# Run management commands
cd /var/www/tahfeed
source venv/bin/activate
python manage.py shell

# Backup database
pg_dump tahfeed_db > backup.sql

# Restore database
psql tahfeed_db < backup.sql
```

---

## Support & Resources

- **Django Docs**: https://docs.djangoproject.com/
- **Gunicorn Docs**: https://gunicorn.org/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **Nginx Docs**: https://nginx.org/en/docs/

---

**Last Updated:** February 15, 2026
**Difficulty Level:** Beginner-Friendly
