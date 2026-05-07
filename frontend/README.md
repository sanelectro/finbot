# FinBot Frontend

## Overview

This is the NextJS frontend application for FinBot, FinSolve Technologies' intelligent assistant with Role-Based Access Control (RBAC).

## Features

### 🔐 **Authentication & Authorization**
- **5 Demo User Accounts** - One for each role (employee, finance, engineering, marketing, hr, c_level)
- **Role-Based UI** - Interface adapts based on user permissions
- **Session Management** - Secure login/logout with local storage

### 💬 **Chat Interface**
- **Intelligent Query Interface** - Natural language interaction with FinBot
- **Real-time Response Display** - Shows all assignment-required fields:
  - Answer with cited source documents and page numbers
  - Semantic route selected for the query
  - User's active role and accessible collections
  - Warning banners when guardrails are triggered
  - Graceful RBAC blocked messages
- **Response Metadata** - Confidence scores, response times, source citations
- **Typing Indicators** - Visual feedback during processing

### ⚙️ **Admin Panel** (C-Level Only)
- **User Management** - View and manage user accounts and roles
- **Document Management** - Upload, delete, and reindex documents
- **Collection Management** - Manage document collections and access rights
- **System Statistics** - Overview of users, documents, and collections

### 🎨 **Modern UI/UX**
- **Responsive Design** - Mobile-first approach with desktop optimization
- **Tailwind CSS** - Clean, modern styling with custom components
- **Loading States** - Smooth transitions and loading indicators
- **Toast Notifications** - Real-time feedback for user actions

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Notifications**: React Hot Toast
- **Markdown**: React Markdown
- **Date Handling**: date-fns

## Demo User Accounts

| Role | Username | Password | Description | Access |
|------|----------|----------|-------------|---------|
| Employee | `john.employee` | `demo123` | General employee | General policies only |
| Finance | `sarah.finance` | `demo123` | Finance analyst | Finance docs + General |
| Engineering | `mike.engineer` | `demo123` | Senior engineer | Engineering docs + General |
| Marketing | `lisa.marketing` | `demo123` | Marketing manager | Marketing docs + General |
| HR | `robert.hr` | `demo123` | HR director | HR docs + General |
| C-Level | `maria.ceo` | `demo123` | CEO | Full access to all collections |

## Setup Instructions

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Running Python backend (FinBot API)

### Installation

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env.local
   ```
   
   Update `.env.local` with your configuration:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. **Start development server:**
   ```bash
   npm run dev
   ```

5. **Open browser:**
   Navigate to `http://localhost:3000`

### Production Build

```bash
npm run build
npm run start
```

## Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   ├── page.tsx          # Home page (redirects)
│   ├── login/            # Login page
│   ├── chat/             # Chat interface
│   └── admin/            # Admin panel
├── components/            # Reusable components
│   ├── ChatInterface.tsx # Main chat component
│   └── Header.tsx        # Navigation header
├── lib/                  # Utilities and configuration
│   ├── types.ts          # TypeScript type definitions
│   ├── auth-context.tsx  # Authentication context
│   ├── api.ts            # API client functions
│   └── utils.ts          # Helper functions
└── public/               # Static assets
```

## Key Components

### Authentication Flow
1. User selects demo account or enters credentials
2. Frontend validates against demo user list
3. User context is stored in localStorage
4. All API requests include user role headers

### Chat Interface Features
- **Message Bubbles** - User and assistant messages with metadata
- **Source Citations** - Expandable document references
- **RBAC Indicators** - Visual feedback for access levels
- **Guardrail Warnings** - Safety alerts and blocked content notices
- **Response Metadata** - Confidence, timing, and routing information

### Admin Panel Capabilities
- **User Overview** - All demo accounts with role badges
- **Document Management** - Upload, reindex, delete operations
- **Collection Control** - Access role configuration
- **System Statistics** - Real-time metrics dashboard

## API Integration

The frontend communicates with the Python backend through:

- **Search Endpoint** - `/api/v1/search` for FinBot queries
- **Admin Endpoints** - User, document, and collection management
- **System Endpoints** - Health checks and status monitoring

All requests include authentication headers:
```typescript
{
  'X-User-Role': user.role,
  'X-User-ID': user.id
}
```

## RBAC Implementation

### Frontend Enforcement
- Route protection based on user role
- Conditional UI components
- Role-based feature access

### Visual Indicators
- Role badges in header and user menu
- Collection access displays
- Permission warnings and messages

### Security Notes
- Frontend RBAC is for UX only
- Backend enforces actual security
- All sensitive operations validated server-side

## Development Guidelines

### Code Style
- TypeScript strict mode enabled
- ESLint configuration for Next.js
- Tailwind CSS for styling
- Component-based architecture

### State Management
- React Context for authentication
- Local state for component data
- No external state management library needed

### Error Handling
- Try-catch blocks for async operations
- Toast notifications for user feedback
- Graceful degradation for API failures

## Deployment

### Environment Variables
```env
NEXT_PUBLIC_API_URL=http://localhost:8000  # Backend API URL
```

### Build Commands
```bash
npm run build    # Production build
npm run start    # Start production server
npm run dev      # Development server
npm run lint     # ESLint check
```

### Docker Support
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Ensure Python backend is running on port 8000
   - Check NEXT_PUBLIC_API_URL in environment variables

2. **Demo Login Not Working**
   - Verify demo credentials match types.ts
   - Check browser console for authentication errors

3. **RBAC Not Showing Correctly**
   - Confirm user role is properly set in context
   - Check backend API responses include role information

4. **Styling Issues**
   - Run `npm run dev` to rebuild Tailwind CSS
   - Check for console errors related to CSS loading

### Debug Mode
Set `NODE_ENV=development` for enhanced logging and error messages.

## Assignment Compliance

This frontend application fully implements Component 5 requirements:

✅ **Login Screen** - 5 demo user accounts with role descriptions
✅ **Chat Interface** - All required response fields displayed
✅ **RBAC Display** - Role and collection access clearly shown  
✅ **Guardrail Warnings** - Visual indicators for blocked content
✅ **Admin Panel** - User, document, and collection management
✅ **Modern UI/UX** - Responsive design with professional styling

---

**FinBot Frontend** - Built for FinSolve Technologies  
Advanced RAG Assistant with Enterprise Security