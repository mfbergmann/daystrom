# Deployment Guide for Daystrom

This guide covers deploying Daystrom on a production VPS.

## Prerequisites

- VPS with Ubuntu 22.04 or later (minimum 2GB RAM)
- Domain name with DNS configured
- Root or sudo access

## Step 1: Server Setup

### Update system
```bash
sudo apt update && sudo apt upgrade -y
```

### Install required packages
```bash
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib nginx certbot python3-certbot-nginx git build-essential
```

### Install pgvector extension
```bash
cd /tmp
git clone --branch v0.7.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

## Step 2: Database Setup

### Create database and user
```bash
sudo -u postgres psql
```

In PostgreSQL:
```sql
CREATE DATABASE daystrom;
CREATE USER daystrom_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE daystrom TO daystrom_user;
\c daystrom
CREATE EXTENSION vector;
\q
```

## Step 3: Application Setup

### Create application user
```bash
sudo useradd -m -s /bin/bash daystrom
sudo su - daystrom
```

### Clone repository
```bash
cd /home/daystrom
git clone <repository-url> app
cd app
```

### Create virtual environment
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Configure environment
```bash
cp .env.example .env
nano .env
```

Update the following values:
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - Your OpenAI API key
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `TELEGRAM_WEBHOOK_URL` - Your webhook URL (https://your-domain.com/webhook/telegram)
- `SECRET_KEY` - Generate with `openssl rand -hex 32`
- Calendar credentials if using

### Create logs directory
```bash
mkdir -p logs
```

### Run database migrations
```bash
alembic upgrade head
```

### Test the application
```bash
python main.py
```

Exit with Ctrl+C once confirmed working.

## Step 4: Systemd Service

Exit back to root/sudo user:
```bash
exit
```

### Create systemd service file
```bash
sudo nano /etc/systemd/system/daystrom.service
```

Copy the contents from `systemd/daystrom.service` (see below).

### Enable and start service
```bash
sudo systemctl daemon-reload
sudo systemctl enable daystrom
sudo systemctl start daystrom
sudo systemctl status daystrom
```

## Step 5: Nginx Configuration

### Create Nginx configuration
```bash
sudo nano /etc/nginx/sites-available/daystrom
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Enable site
```bash
sudo ln -s /etc/nginx/sites-available/daystrom /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Step 6: SSL Certificate

### Obtain SSL certificate
```bash
sudo certbot --nginx -d your-domain.com
```

Follow the prompts to configure HTTPS.

## Step 7: Set Telegram Webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://your-domain.com/webhook/telegram"
```

## Step 8: Database Backups

### Create backup script
```bash
sudo nano /usr/local/bin/backup-daystrom.sh
```

Add:
```bash
#!/bin/bash
BACKUP_DIR="/home/daystrom/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
sudo -u postgres pg_dump daystrom | gzip > $BACKUP_DIR/daystrom_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "daystrom_*.sql.gz" -mtime +7 -delete
```

### Make executable
```bash
sudo chmod +x /usr/local/bin/backup-daystrom.sh
```

### Schedule daily backups
```bash
sudo crontab -e
```

Add:
```
0 2 * * * /usr/local/bin/backup-daystrom.sh
```

## Monitoring

### View logs
```bash
# Application logs
sudo journalctl -u daystrom -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Check status
```bash
sudo systemctl status daystrom
```

### Restart service
```bash
sudo systemctl restart daystrom
```

## Updating the Application

```bash
sudo su - daystrom
cd app
git pull
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
exit
sudo systemctl restart daystrom
```

## Security Checklist

- ✓ Use strong passwords for database
- ✓ Keep API keys in `.env` file only
- ✓ Enable firewall (ufw)
- ✓ Configure SSH key authentication
- ✓ Disable root SSH login
- ✓ Keep system packages updated
- ✓ Use SSL/HTTPS for all connections
- ✓ Regular database backups
- ✓ Monitor logs for errors

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u daystrom -n 50
```

### Database connection errors
Check database credentials in `.env` and PostgreSQL is running:
```bash
sudo systemctl status postgresql
```

### Telegram webhook not working
Verify webhook is set:
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### High memory usage
Increase VPS RAM or adjust worker processes in uvicorn configuration.

## Performance Tuning

### Optimize PostgreSQL
Edit `/etc/postgresql/*/main/postgresql.conf`:
```
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### Enable compression in Nginx
Add to nginx configuration:
```nginx
gzip on;
gzip_types text/plain application/json;
```

## Support

For issues or questions, check the logs and refer to the README.md file.

