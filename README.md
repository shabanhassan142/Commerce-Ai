# CommerceFlow AI

**Multi-Agent AI Customer Support & Order Management Platform**

A production-grade AI platform for e-commerce customer support, powered by LangGraph, FAISS, and OpenRouter.

---

## Overview

CommerceFlow AI intelligently routes customer requests to specialized AI agents, retrieves information from structured databases and company knowledge documents, and responds with accurate, cited answers.

### Key Capabilities
- 🤖 **Multi-Agent System** — Supervisor routes to Order, Refund, Billing, Product, Knowledge, Support & Escalation agents
- 🔍 **RAG Pipeline** — Semantic search over company policy documents using FAISS
- 📊 **Marketplace Data** — Full PostgreSQL-backed order, customer, and product management
- 🔐 **JWT Authentication** — Secure role-based access (Customer / Support / Admin)
- 📈 **Analytics Dashboard** — Real-time agent performance and conversation metrics

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, TypeScript, Tailwind CSS, Framer Motion, Radix UI |
| Backend | FastAPI, SQLAlchemy (Async), Alembic, PostgreSQL |
| AI Agents | LangGraph, OpenRouter (Qwen3-30B) |
| Vector DB | FAISS + BAAI/bge-small-en-v1.5 |
| Auth | JWT (Access + Refresh tokens) |

---

## Project Structure

```
commerceflow-ai/
├── backend/          # FastAPI application
├── frontend/         # React application
├── docs/             # Documentation
└── docker-compose.yml
```

---

## Development Modules

| Module | Status | Description |
|--------|--------|-------------|
| M1 | ✅ Complete | Project Setup, Auth, PostgreSQL |
| M2 | 🔲 Pending | Database Models & Seed Data |
| M3 | 🔲 Pending | RAG Pipeline & Knowledge Base |
| M4 | 🔲 Pending | LangGraph Supervisor Agent |
| M5 | 🔲 Pending | Specialized AI Agents |
| M6 | 🔲 Pending | Customer Chat UI |
| M7 | 🔲 Pending | Admin Dashboard & Analytics |
| M8 | 🔲 Pending | Testing & Deployment |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Docker (optional)

### 1. Start with Docker
```bash
docker-compose up -d
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
cp .env.example .env           # Edit with your credentials
alembic upgrade head
uvicorn app.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Access
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Environment Variables

See `backend/.env.example` for all required variables.

---

## License

MIT
