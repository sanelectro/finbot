# FinBot Quick Start Guide

## 🚀 Get FinBot Running in 5 Minutes

### Prerequisites
- Docker Desktop installed and running
- Python 3.9+
- Node.js 18+
- Git

### Step 1: Get the Code
```bash
git clone https://github.com/sanelectro/finbot
cd finbot
```

### Step 2: Install Python Dependencies
```bash
pip install -e .
```

### Step 3: Set Up Environment
```bash
cp .env.example .env
# Add your GROQ_API_KEY to the .env file
```

### Step 4: Start Services (PostgreSQL + Qdrant)
```bash
docker compose up -d
```

Wait ~10 seconds for services to be healthy.

### Step 5: Start the Backend
```bash
PYTHONPATH=. python main.py
```

Demo users are seeded automatically on first startup.

### Step 6: Start the Frontend
```bash
cd frontend
npm install
npm run dev
```

Visit: **http://localhost:3001**

## 🧪 Demo Users (seeded automatically on startup)

| Role | Email | Password |
|------|-------|----------|
| Employee | employee@finbot.com | demo123 |
| Finance | finance@finbot.com | demo123 |
| Engineering | engineering@finbot.com | demo123 |
| Marketing | marketing@finbot.com | demo123 |
| HR | hr@finbot.com | demo123 |
| C-Level | clevel@finbot.com | demo123 |

### Quick API Test
```bash
curl http://localhost:8000/health
```

## 🛑 Stop Everything
```bash
docker compose down        # Stop PostgreSQL + Qdrant
# Stop Backend: Ctrl+C in terminal
# Stop Frontend: Ctrl+C in terminal
```

## ❓ Troubleshooting

### Services not starting
```bash
# Check status
docker compose ps

# View logs
docker compose logs

# Reset and restart
docker compose down -v && docker compose up -d
```

### Connection Info
- **PostgreSQL**: localhost:5435 (finbot/finbot123/finbot_db)
- **Qdrant**: localhost:6333
- **Backend API**: localhost:8000 (docs at /docs)
- **Frontend**: localhost:3001


## 🎯 What's Next?
1. Explore the admin panel at http://localhost:3001/admin
2. Try different user roles and see RBAC in action
3. Upload new documents and see them get processed
4. Run the evaluation system: `python src/evaluation/ragas_orchestrator.py`

**For more details, see [README.md](README.md)**