# Receipt Processing Frontend

A modern React application for automated receipt processing and bank statement comparison.

## Features

- 🔐 Google OAuth2 authentication
- 📧 Gmail integration with real-time notifications
- 🤖 AI-powered receipt processing visualization
- 📊 Interactive transaction comparison
- 📱 Responsive design (mobile/tablet/desktop)
- ♿ Accessibility features
- 🎨 Framer Motion animations
- 🔄 Real-time data updates

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and optimized builds
- **Tailwind CSS** for styling
- **Framer Motion** for animations
- **TanStack Query** for data fetching and caching
- **React Router** for navigation
- **Axios** for API communication
- **React Hook Form** for form management
- **React Dropzone** for file uploads
- **Lucide React** for icons

## Quick Start

### Prerequisites

- Node.js 18+
- pnpm (recommended) or npm
- FastAPI backend running on port 8000

### Installation

1. **Install dependencies:**
   ```bash
   pnpm install
   ```

2. **Environment setup:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start development server:**
   ```bash
   pnpm dev
   ```

4. **Open in browser:**
   - Development: http://localhost:3000
   - Backend API: http://localhost:8005

## Environment Variables

```env
# API Configuration
VITE_API_URL=http://localhost:8005

# App Configuration
VITE_APP_NAME="Receipt Processing"
VITE_APP_DESCRIPTION="AI-powered receipt processing and bank statement comparison"
```

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # Base UI components
│   ├── Layout.tsx      # Main layout wrapper
│   ├── Navbar.tsx      # Navigation bar
│   ├── TransactionTable.tsx
│   ├── CSVUploader.tsx
│   └── ...
├── pages/              # Page components
│   ├── LoginPage.tsx
│   ├── DashboardPage.tsx
│   ├── NotificationsPage.tsx
│   └── ComparePage.tsx
├── lib/                # Utilities and configurations
│   ├── api.ts          # API client and types
│   ├── auth.tsx        # Authentication context
│   └── query-client.ts # React Query configuration
├── hooks/              # Custom React hooks
└── App.tsx             # Main application component
```

## Key Features

### Authentication
- Google OAuth2 integration
- Persistent login state
- Automatic token refresh
- Protected routes

### Dashboard
- Transaction summary statistics
- Recent transaction display
- Gmail integration status
- CSV upload interface
- Category-based spending breakdown

### Notifications
- Real-time email processing notifications
- Advanced filtering and search
- Pagination for large datasets
- Virtual scrolling for performance

### Transaction Comparison
- Three-way comparison view (Matched/Ledger Only/Bank Only)
- Color-coded confidence indicators
- Detailed match analysis
- CSV bank statement processing

### User Experience
- Responsive design for all screen sizes
- Smooth animations and transitions
- Loading states and skeleton loaders
- Toast notifications for user feedback
- Accessibility features (ARIA labels, keyboard navigation)

## API Integration

The frontend communicates with the FastAPI backend through a centralized API client:

- **Authentication**: Google OAuth flow, user management
- **Transactions**: CRUD operations, filtering, search
- **Emails**: Notification management, processing status
- **Bank Transactions**: CSV upload, comparison logic
- **Real-time Updates**: Automatic data refetching

## Styling Guidelines

The application follows a modern design system:

- **Color Palette**: Professional blue primary with semantic colors
- **Typography**: Inter font family with clear hierarchy
- **Spacing**: Consistent 4px grid system
- **Components**: Reusable, accessible UI components
- **Animations**: Subtle, meaningful motion design

## Performance Optimizations

- **Code Splitting**: Automatic route-based splitting
- **Image Optimization**: Optimized loading and formats
- **Caching**: TanStack Query for intelligent data caching
- **Virtual Scrolling**: Efficient rendering of large lists
- **Bundle Optimization**: Tree shaking and minification

## Build and Deployment

### Development
```bash
pnpm dev          # Start development server
pnpm lint         # Run ESLint
pnpm type-check   # TypeScript checking
```

### Production Build
```bash
pnpm build        # Build for production
pnpm preview      # Preview production build
```

### Deployment Options

#### Vercel (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

#### Netlify
```bash
# Build and deploy
pnpm build
# Upload dist/ folder to Netlify
```

#### Traditional Hosting
```bash
# Build static files
pnpm build

# Serve dist/ folder with any static file server
serve -s dist
```

#### Docker
```dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Testing

### Manual Testing Checklist

- [ ] Google OAuth login flow
- [ ] Dashboard data loading
- [ ] Transaction filtering and search
- [ ] CSV file upload
- [ ] Transaction comparison views
- [ ] Mobile responsiveness
- [ ] Accessibility features

### Automated Testing (Future)

```bash
# Add testing dependencies
pnpm add -D @testing-library/react @testing-library/jest-dom vitest

# Run tests
pnpm test
```

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Ensure backend CORS settings include frontend URL
   - Check environment variables

2. **Authentication Failures**
   - Verify Google OAuth credentials
   - Check redirect URI configuration

3. **API Connection Issues**
   - Confirm backend is running on correct port
   - Verify API_URL environment variable

4. **Build Errors**
   - Clear node_modules and reinstall
   - Check TypeScript errors
   - Verify environment variables

### Development Tips

- Use React Developer Tools for debugging
- Check Network tab for API request issues
- Use TanStack Query DevTools for cache inspection
- Enable verbose logging in development

## Contributing

1. Follow TypeScript best practices
2. Use semantic commit messages
3. Add proper error handling
4. Maintain responsive design
5. Test accessibility features
6. Update documentation

## License

MIT License - see LICENSE file for details.
