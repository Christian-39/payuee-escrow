# GadgetHub Deployment Guide

This guide covers deploying the GadgetHub e-commerce platform to Render.

## Prerequisites

- Render account (https://render.com)
- GitHub repository with your code
- Payuee API credentials
- Backblaze B2 account (for file storage)

## Project Structure

The project is organized into two separate folders:

```
/mnt/okcomputer/output/
├── frontend/          # React + Vite frontend
└── backend/           # Django REST API backend
```

## Backend Deployment (Render)

### 1. Create PostgreSQL Database

1. Go to Render Dashboard → New → PostgreSQL
2. Name: `gadgethub-db`
3. Database: `gadgethub`
4. User: `gadgethub`
5. Create database
6. Save the connection string for later

### 2. Create Web Service for Backend

1. Go to Render Dashboard → New → Web Service
2. Connect your GitHub repository
3. Configure:
   - **Name**: `gadgethub-api`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     gunicorn gadgethub.wsgi:application
     ```

### 3. Environment Variables

Add these environment variables in Render dashboard:

```env
# Django
SECRET_KEY=your-very-secret-key-here-min-50-chars-long-for-security
DEBUG=False
ALLOWED_HOSTS=gadgethub-api.onrender.com,localhost

# Database (from step 1)
DB_NAME=gadgethub
DB_USER=gadgethub
DB_PASSWORD=your-db-password
DB_HOST=your-db-host.render.com
DB_PORT=5432

# Payuee API
PAYUEE_API_KEY=your-payuee-api-key
PAYUEE_API_SECRET=your-payuee-api-secret
PAYUEE_BASE_URL=https://escrow.payuee.com/v1

# Backblaze B2 (optional for file storage)
B2_KEY_ID=your-b2-key-id
B2_APPLICATION_KEY=your-b2-app-key
B2_BUCKET_NAME=your-bucket-name
B2_ENDPOINT=https://s3.us-east-005.backblazeb2.com
B2_REGION=us-east-005
USE_S3=True

# Redis (optional - can use Render Redis or external)
REDIS_URL=redis://redis-host:6379/0

# CORS - Add your frontend URL
CORS_ALLOWED_ORIGINS=https://gadgethub.onrender.com,http://localhost:5173

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### 4. Run Migrations

After deployment, run migrations using Render Shell:

```bash
cd backend
python manage.py migrate
```

### 5. Create Superuser

```bash
cd backend
python manage.py createsuperuser
```

## Frontend Deployment (Render)

### 1. Create Static Site

1. Go to Render Dashboard → New → Static Site
2. Connect your GitHub repository
3. Configure:
   - **Name**: `gadgethub`
   - **Root Directory**: `frontend`
   - **Build Command**:
     ```bash
     npm install && npm run build
     ```
   - **Publish Directory**: `dist`

### 2. Environment Variables

```env
VITE_API_URL=https://gadgethub-api.onrender.com/api
```

### 3. Redirects/Rewrites

Add a rewrite rule in Render dashboard:
- Source: `/*`
- Destination: `/index.html`

## Payuee Webhook Configuration

1. Login to your Payuee dashboard
2. Go to Webhooks settings
3. Add webhook URL:
   ```
   https://gadgethub-api.onrender.com/api/webhooks/payuee
   ```
4. Select events:
   - `order.created`
   - `order.paid`
   - `order.verified`
   - `order.refunded`
   - `wallet.funded`

## Post-Deployment Checklist

- [ ] Backend API is accessible
- [ ] Frontend loads correctly
- [ ] Database migrations applied
- [ ] Superuser created
- [ ] Payuee webhooks configured
- [ ] CORS settings updated with frontend URL
- [ ] Environment variables set correctly
- [ ] SSL/HTTPS working

## Troubleshooting

### CORS Errors

Update `CORS_ALLOWED_ORIGINS` in backend environment variables with your exact frontend URL.

### Database Connection Issues

1. Verify database credentials
2. Check if database is in the same region as web service
3. Test connection using `psql` command line

### Static Files Not Loading

1. Check `USE_S3` setting
2. Verify B2 credentials
3. Check bucket permissions (should be public-read)

### Payuee Webhooks Not Working

1. Verify webhook URL is correct and publicly accessible
2. Check webhook signature verification
3. Review backend logs for errors

## Updating Deployment

### Backend Updates

1. Push changes to GitHub
2. Render automatically deploys
3. Run migrations if needed:
   ```bash
   python manage.py migrate
   ```

### Frontend Updates

1. Push changes to GitHub
2. Render automatically builds and deploys

## Monitoring

- Check Render logs for errors
- Monitor database usage
- Track Payuee transaction logs
- Set up alerts for critical errors

## Backup

### Database Backup

Render PostgreSQL includes automated backups. You can also manually backup:

```bash
pg_dump -h your-db-host.render.com -U gadgethub gadgethub > backup.sql
```

### Media Files Backup

If using Backblaze B2, files are automatically backed up. For local storage:

```bash
rsync -avz backend/media/ backup/media/
```

## Security Considerations

1. **Never commit `.env` files**
2. Use strong `SECRET_KEY` (50+ characters)
3. Enable `SECURE_SSL_REDIRECT` in production
4. Regularly rotate API keys
5. Monitor for suspicious activity
6. Keep dependencies updated

## Support

For deployment issues:
- Render Docs: https://render.com/docs
- Django Deployment: https://docs.djangoproject.com/en/stable/howto/deployment/
- Payuee API Docs: https://escrow.payuee.com/docs
