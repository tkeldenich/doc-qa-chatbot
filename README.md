# Document Q&A Chatbot

![Coverage Badge](./coverage.svg)
![CI](https://github.com/yourusername/doc-qa-chatbot/workflows/Backend%20CI/badge.svg)

A comprehensive document-based Q&A chatbot that leverages RAG (Retrieval Augmented Generation) to provide intelligent answers from uploaded documents.

## Architecture

- **Backend**: FastAPI + LangChain + SQLAlchemy
- **Frontend**: Next.js + TailwindCSS + shadcn/ui
- **Database**: PostgreSQL + ChromaDB/Pinecone (Vector)
- **Infrastructure**: AWS + Docker + Terraform

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- AWS CLI (for deployment)

### Development Setup
1. Clone the repository
2. Install pre-commit hooks: `pre-commit install`
3. Start services: `docker-compose up -d`
4. Backend: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
5. Frontend: `cd frontend && npm install && npm run dev`

### Environment Variables
Copy `.env.example` to `.env` and configure:
- Database credentials
- OpenAI/Anthropic API keys
- AWS credentials
- Vector database settings

## Project Structure
- `/backend` - FastAPI application
- `/frontend` - Next.js application
- `/infrastructure` - Terraform and deployment configs
- `/docs` - Project documentation

## Contributing
1. Create feature branch
2. Make changes
3. Run tests: `make test`
4. Submit PR

## License
MIT License
