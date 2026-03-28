# GadgetHub - Full-Stack E-Commerce Platform

A modern, production-ready e-commerce platform for selling gadgets with Payuee escrow integration.

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Payuee Integration](#payuee-integration)
- [Deployment](#deployment)
- [Admin Guide](#admin-guide)

## ✨ Features

### User Features
- 🛍️ Browse products by category
- 🔍 Advanced search with filters
- 🛒 Shopping cart with real-time updates
- 💳 Secure checkout with Payuee escrow
- 📦 Order tracking
- ❤️ Wishlist/favorites
- 👤 User profile management
- 🌙 Dark/Light mode
- 📱 Fully responsive design

### Admin Features
- 📊 Dashboard with analytics
- 📦 Product management (CRUD)
- 📋 Order management
- 👥 User management
- 📈 Sales reports
- 🔔 Inventory alerts

### Technical Features
- 🔐 JWT authentication
- 🖼️ Backblaze B2 image storage
- 🔄 Real-time cart updates
- 📧 Email notifications
- 🎯 SEO optimized
- ⚡ Fast loading with lazy loading
- 🎨 Smooth animations

## 🛠️ Tech Stack

### Frontend
- React 19 + TypeScript
- Vite (build tool)
- Tailwind CSS
- Framer Motion (animations)
- TanStack Query (data fetching)
- Zustand (state management)
- shadcn/ui components

### Backend
- Django 5.x
- Django REST Framework
- PostgreSQL
- Redis (caching & Celery)
- Celery (background tasks)
- Simple JWT (authentication)

### Third-Party Services
- Payuee Escrow API (payments)
- Backblaze B2 (file storage)

## 📁 Project Structure

```
/mnt/okcomputer/output/
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── components/      # Reusable components
│   │   ├── contexts/        # React contexts
│   │   ├── hooks/           # Custom hooks
│   │   ├── layouts/         # Page layouts
│   │   ├── lib/             # Utilities
│   │   ├── pages/           # Page components
│   │   ├── types/           # TypeScript types
│   │   └── App.tsx          # Main app
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                  # Django backend
│   ├── gadgethub/           # Main project
│   ├── accounts/            # User management
│   ├── products/            # Product catalog
│   ├── orders/              # Orders & cart
│   ├── payments/            # Payuee integration
│   ├── admin_dashboard/     # Admin APIs
│   ├── requirements.txt
│   └── manage.py
│
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Node.js 20+
- Python 3.11+
- PostgreSQL 14+
- Redis (optional, for caching)

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create superuser:
```bash
python manage.py createsuperuser
```

7. Start server:
```bash
python manage.py runserver
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env` file:
```bash
cp .env.example .env
```

4. Start development server:
```bash
npm run dev
```

## 🔐 Environment Variables

### Backend (.env)

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=gadgethub
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432

# Payuee API
PAYUEE_API_KEY=your-api-key
PAYUEE_API_SECRET=your-api-secret
PAYUEE_BASE_URL=https://escrow.payuee.com/v1

# Backblaze B2
B2_KEY_ID=your-key-id
B2_APPLICATION_KEY=your-app-key
B2_BUCKET_NAME=your-bucket
USE_S3=False

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000/api
```

## 📚 API Documentation

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login user |
| POST | `/api/auth/refresh/` | Refresh JWT token |
| GET | `/api/auth/profile/` | Get user profile |
| PATCH | `/api/auth/profile/update/` | Update profile |
| POST | `/api/auth/password/change/` | Change password |

### Product Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products/` | List products |
| GET | `/api/products/featured/` | Featured products |
| GET | `/api/products/:slug/` | Product detail |
| GET | `/api/products/categories/` | List categories |
| POST | `/api/products/search/` | Search products |
| GET | `/api/products/wishlist/` | User wishlist |
| POST | `/api/products/wishlist/add/` | Add to wishlist |

### Order Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orders/cart/` | Get cart |
| POST | `/api/orders/cart/add/` | Add to cart |
| PATCH | `/api/orders/cart/update/:id/` | Update quantity |
| DELETE | `/api/orders/cart/remove/:id/` | Remove item |
| POST | `/api/orders/checkout/` | Place order |
| GET | `/api/orders/` | List orders |
| GET | `/api/orders/:orderNumber/` | Order detail |

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/stats/` | Dashboard stats |
| GET | `/api/admin/users/` | List users |
| GET | `/api/admin/products/` | List all products |
| POST | `/api/admin/products/` | Create product |
| GET | `/api/admin/orders/` | List all orders |

## 💳 Payuee Integration

### How Escrow Works

1. **Order Creation**: When a customer places an order, we create an order in Payuee's escrow system
2. **Payment**: Customer pays into the escrow account
3. **Fulfillment**: Seller ships the product
4. **Verification**: Customer confirms receipt
5. **Release**: Funds are released to the seller

### HMAC Signature Generation

All API requests to Payuee must include an HMAC SHA256 signature:

```python
payload = timestamp + METHOD + PATH + BODY
signature = HMAC_SHA256(api_secret, payload)
```

Headers required:
- `X-API-Key`: Your API key
- `X-Signature`: Generated signature
- `X-Timestamp`: Unix timestamp
- `Idempotency-Key`: For POST requests (prevents duplicates)

### Webhook Events

The following webhooks are handled:

| Event | Description |
|-------|-------------|
| `order.created` | Order created in Payuee |
| `order.paid` | Payment received |
| `order.verified` | Delivery verified |
| `order.refunded` | Order refunded |
| `wallet.funded` | Wallet funded |

## 🚀 Deployment

### Render Deployment

#### Backend

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set build command:
```bash
pip install -r requirements.txt
```
4. Set start command:
```bash
gunicorn gadgethub.wsgi:application
```
5. Add environment variables in Render dashboard
6. Create PostgreSQL database on Render

#### Frontend

1. Create a new Static Site on Render
2. Connect your GitHub repository
3. Set build command:
```bash
npm install && npm run build
```
4. Set publish directory: `dist`
5. Add environment variables

### Environment Variables for Production

Make sure to set these in your production environment:

- `SECRET_KEY`: Generate a strong random key
- `DEBUG`: Set to `False`
- `ALLOWED_HOSTS`: Your domain names
- `DATABASE_URL`: PostgreSQL connection string
- `PAYUEE_API_KEY` & `PAYUEE_API_SECRET`: From Payuee dashboard
- `B2_*`: Backblaze B2 credentials
- `CORS_ALLOWED_ORIGINS`: Your frontend URL

## 👨‍💼 Admin Guide

### Accessing Admin Panel

1. Login with superuser credentials at `/admin`
2. Or use the frontend admin dashboard at `/admin`

### Managing Products

1. Go to Admin Dashboard → Products
2. Click "Add Product" to create new
3. Fill in product details:
   - Name, description, price
   - Category selection
   - Inventory tracking
   - Images (uploaded to B2)
4. Save product

### Managing Orders

1. Go to Admin Dashboard → Orders
2. View all orders with filters
3. Click order to see details
4. Update status:
   - `pending` → `confirmed` → `processing` → `shipped` → `delivered`
5. Add tracking information

### Managing Users

1. Go to Admin Dashboard → Users
2. View all registered users
3. Toggle user status (active/inactive)
4. View user order history

## 🔒 Security Best Practices

1. **Keep secrets safe**: Never commit `.env` files
2. **Use HTTPS**: Always in production
3. **Validate inputs**: Both frontend and backend
4. **Rate limiting**: Implement on API endpoints
5. **CORS**: Configure properly for your domains
6. **File uploads**: Validate file types and sizes

## 📝 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For support, please contact:
- Email: support@gadgethub.com
- Documentation: https://docs.gadgethub.com

---

Built with ❤️ by the GadgetHub Team
