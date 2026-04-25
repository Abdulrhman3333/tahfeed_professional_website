# 🚀 Deployment Guide for Tahfeed Professional Website

## Step 1: Prepare Your Server

### Linux Server Setup (Ubuntu/Debian)
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git

# Install additional system dependencies
sudo apt install -y libpq-dev python3-dev build-essential
```

---

## Step 2: Clone & Setup Project

```bash
# Navigate to deployment directory
cd /var/www

# Clone your project
git clone <your-repo-url> tahfeed
cd tahfeed

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install additional production packages
pip install gunicorn psycopg2-binary python-decouple
```

---

## Step 3: Database Setup (PostgreSQL)

```bash
# Login to PostgreSQL as root
sudo -u postgres psql

# Inside PostgreSQL shell:
CREATE DATABASE tahfeed_db;
CREATE USER tahfeed_user WITH PASSWORD 'your-secure-password';

ALTER ROLE tahfeed_user SET client_encoding TO 'utf8';
ALTER ROLE tahfeed_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE tahfeed_user SET default_transaction_deferrable TO on;
ALTER ROLE tahfeed_user SET default_transaction_read_uncommitted TO off;

GRANT ALL PRIVILEGES ON DATABASE tahfeed_db TO tahfeed_user;
\q
```

---

## Step 4: Configure Environment Variables

```bash
# Create .env file in project root
nano /var/www/tahfeed/.env
```

Add these settings:
```
# Django Settings
SECRET_KEY=your-generated-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=tahfeed_db
DB_USER=tahfeed_user
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

---

## Step 5: Collect Static Files & Run Migrations

```bash
cd /var/www/tahfeed
source venv/bin/activate

# Collect static files
python manage.py collectstatic --noinput

# Run database migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

---

## Step 6: Setup Gunicorn

### Create Gunicorn Service File

```bash
sudo nano /etc/systemd/system/gunicorn-tahfeed.service
```

Add this content:
```ini
[Unit]
Description=Gunicorn application server for Tahfeed
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/tahfeed
ExecStart=/var/www/tahfeed/venv/bin/gunicorn \
    --workers 3 \
    --worker-class sync \
    --bind unix:/var/www/tahfeed/gunicorn.sock \
    --timeout 60 \
    --access-logfile /var/log/tahfeed/access.log \
    --error-logfile /var/log/tahfeed/error.log \
    myproject.wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn-tahfeed
sudo systemctl start gunicorn-tahfeed
sudo systemctl status gunicorn-tahfeed
```

---

## Step 7: Configure Nginx

### Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/tahfeed
```

Add this content:
```nginx
upstream tahfeed_app {
    server unix:/var/www/tahfeed/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    client_max_body_size 5M;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (use Let's Encrypt - certbot)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 5M;

    location / {
        proxy_pass http://tahfeed_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location /static/ {
        alias /var/www/tahfeed/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/tahfeed/media/;
        expires 7d;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/tahfeed /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

---

## Step 8: Setup Let's Encrypt SSL (HTTPS)

```bash
sudo apt install -y certbot python3-certbot-nginx

sudo certbot certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renew SSL certificates
sudo systemctl enable certbot.timer
```

---

## Step 9: Setup Backup Strategy

### Database Backup Script
```bash
sudo nano /usr/local/bin/backup-tahfeed.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/tahfeed"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
sudo -u postgres pg_dump tahfeed_db | gzip > $BACKUP_DIR/db_$TIMESTAMP.sql.gz

# Backup uploads
tar -czf $BACKUP_DIR/media_$TIMESTAMP.tar.gz /var/www/tahfeed/media/

# Keep only last 30 days of backups
find $BACKUP_DIR -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
```

Make it executable:
```bash
sudo chmod +x /usr/local/bin/backup-tahfeed.sh

# Schedule daily backups (crontab)
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-tahfeed.sh
```

---

## Step 10: Monitoring & Logs

### Check Application Status
```bash
# Check Gunicorn
sudo systemctl status gunicorn-tahfeed

# Check Nginx
sudo systemctl status nginx

# View logs
tail -f /var/log/tahfeed/error.log
tail -f /var/log/tahfeed/access.log
```

### Create Logs Directory
```bash
sudo mkdir -p /var/log/tahfeed
sudo chown www-data:www-data /var/log/tahfeed
```

---

## Pre-Deployment Checklist

- [ ] Change `DEBUG = False` in production settings
- [ ] Set a new, unique `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Setup HTTPS/SSL certificate
- [ ] Configure database (PostgreSQL recommended)
- [ ] Setup environment variables in `.env`
- [ ] Run `python manage.py migrate`
- [ ] Run `python manage.py collectstatic`
- [ ] Create superuser account
- [ ] Test locally: `python manage.py runserver 0.0.0.0:8000`
- [ ] Configure email settings
- [ ] Setup database backups
- [ ] Configure firewall (ufw)
- [ ] Monitor logs and errors
- [ ] Setup error tracking (Sentry recommended)
- [ ] Performance optimization (caching, CDN)

---

## Firewall Setup (UFW)

```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable
sudo ufw status
```

---

## Troubleshooting

### Check Gunicorn Socket
```bash
ls -la /var/www/tahfeed/gunicorn.sock
```

### Check Nginx Configuration
```bash
sudo nginx -t
```

### View Gunicorn Logs
```bash
sudo journalctl -u gunicorn-tahfeed -f
```

### Restart Services
```bash
sudo systemctl restart gunicorn-tahfeed
sudo systemctl restart nginx
```

---

## Performance Optimization

### Enable Gzip Compression
Add to Nginx config:
```nginx
gzip on;
gzip_types text/plain text/css text/xml text/javascript application/x-javascript;
gzip_vary on;
```

### Setup Redis Caching
```bash
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### Database Optimization
```bash
# Analyze query performance
python manage.py shell

# Run Django ORM optimization
python manage.py dbshell
VACUUM ANALYZE;
```

---

## Useful Commands

```bash
# Restart all services
sudo systemctl restart gunicorn-tahfeed nginx

# View all running services
systemctl list-units --type service

# Check disk usage
df -h

# Monitor real-time
htop
```

---

## Support Hosting Options

Recommended hosting providers for Django:
- **PythonAnywhere** - Easy Python hosting
- **Heroku** - Simple deployment (now paid)
- **DigitalOcean** - Affordable VPS
- **Linode** - Reliable cloud hosting
- **AWS** - Scalable cloud solution
- **Google Cloud Platform** - Enterprise option

---

**Last Updated:** February 15, 2026
**Project:** Tahfeed Professional Website
