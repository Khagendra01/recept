# Receipt Processing API

A FastAPI-based backend for automated receipt processing from Gmail emails using OpenAI.

## Features

- 🔐 Google OAuth2 authentication
- 📧 Gmail API integration for email fetching
- 🤖 OpenAI-powered receipt data extraction
- 💾 SQLite database with SQLAlchemy ORM
- 📊 Bank statement CSV upload and comparison
- ⚡ Background email polling
- 🔄 RESTful API endpoints
- 📝 Comprehensive logging and error handling

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud Project with Gmail API enabled
- OpenAI API key
- Redis (for background tasks)

### Installation

1. **Clone and setup:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Initialize database:**
   ```bash
   python app/db/init_db.py
   ```

4. **Run development server:**
   ```bash
   python run.py
   # Or: uvicorn app.main:app --reload
   ```

5. **API Documentation:**
   - Swagger UI: http://localhost:8005/docs
   - ReDoc: http://localhost:8005/redoc

## Configuration

### Required Environment Variables

```env
# Google OAuth2
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Security
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=sqlite:///./receipt_processing.db

# Frontend
FRONTEND_URL=http://localhost:3000
```

### Google Cloud Setup

1. Create a Google Cloud Project
2. Enable Gmail API
3. Create OAuth2 credentials
4. Add authorized redirect URIs:
   - `http://localhost:3000/auth/callback` (development)
   - Your production domain callback URL

## API Endpoints

### Authentication
- `GET /api/v1/auth/google/url` - Get Google OAuth URL
- `POST /api/v1/auth/google/callback` - Handle OAuth callback
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/gmail/sync` - Trigger Gmail sync

### Transactions
- `GET /api/v1/transactions/` - List transactions
- `GET /api/v1/transactions/recent` - Recent transactions
- `GET /api/v1/transactions/summary` - Transaction summary
- `GET /api/v1/transactions/categories` - Available categories

### Bank Transactions
- `GET /api/v1/bank-transactions/` - List bank transactions
- `POST /api/v1/bank-transactions/upload-csv` - Upload CSV
- `GET /api/v1/bank-transactions/compare` - Compare transactions

### Emails
- `GET /api/v1/emails/` - List emails
- `GET /api/v1/emails/notifications` - Recent notifications
- `GET /api/v1/emails/stats` - Email statistics

## Background Tasks

The application automatically:
- Polls Gmail every 30 seconds for new emails
- Processes PDF receipts using OpenAI
- Extracts structured transaction data
- Handles token refresh automatically

## Database Schema

- **Users**: User accounts and Gmail tokens
- **Emails**: Email metadata and processing status
- **Transactions**: Extracted receipt data
- **Bank Transactions**: Uploaded bank statement data

## Deployment

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build
```

### Manual Deployment

1. **Production setup:**
   ```bash
   pip install -r requirements.txt
   python app/db/init_db.py
   ```

2. **Run with Gunicorn:**
   ```bash
   pip install gunicorn
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

3. **Environment variables:**
   - Set production values for all required env vars
   - Use PostgreSQL for production database
   - Configure proper CORS origins

### Platform-Specific Deployment

#### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

#### Heroku
```bash
# Create Heroku app
heroku create your-app-name

# Set environment variables
heroku config:set GOOGLE_CLIENT_ID=your-id
heroku config:set GOOGLE_CLIENT_SECRET=your-secret
heroku config:set OPENAI_API_KEY=your-key

# Deploy
git push heroku main
```

#### AWS EC2
```bash
# Install dependencies on EC2
sudo apt update
sudo apt install python3-pip python3-venv nginx

# Setup application
git clone your-repo
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup systemd service
sudo nano /etc/systemd/system/receipt-api.service
sudo systemctl enable receipt-api
sudo systemctl start receipt-api

# Configure Nginx reverse proxy
sudo nano /etc/nginx/sites-available/receipt-api
sudo ln -s /etc/nginx/sites-available/receipt-api /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

## Development

### Adding New Features

1. **Models**: Add to `app/models/`
2. **Schemas**: Add Pydantic models to `app/schemas/`
3. **Services**: Add business logic to `app/services/`
4. **APIs**: Add endpoints to `app/api/v1/`
5. **Tests**: Add tests to `tests/`

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Troubleshooting

### Common Issues

1. **Gmail API quota exceeded**
   - Check Google Cloud Console quotas
   - Reduce polling frequency

2. **OpenAI API errors**
   - Verify API key is correct
   - Check billing and usage limits

3. **Token refresh failures**
   - Re-authenticate users
   - Check OAuth consent screen settings

4. **CSV upload errors**
   - Verify CSV format matches expected columns
   - Check file size limits

### Logs

```bash
# View application logs
tail -f app.log

# Database logs
tail -f db.log

# Background task logs
tail -f background.log
```

## Security Considerations

- Store sensitive credentials in environment variables
- Use HTTPS in production
- Implement rate limiting
- Validate all input data
- Regular security updates
- Monitor for suspicious activity

## License

MIT License - see LICENSE file for details.
