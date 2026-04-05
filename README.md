# AI Research Assistant Agent

Production-oriented FastAPI backend that searches research papers, downloads and parses PDFs, builds embeddings, retrieves relevant evidence, and answers with citations.

## Features

- `POST /query` executes the full research workflow
- `/` serves a lightweight frontend for submitting research questions
- arXiv paper discovery
- PDF download and text extraction
- OpenAI embeddings for lightweight deployment
- in-memory vector retrieval for request-scoped RAG
- OpenAI answer synthesis with structured citations

## Architecture

- `app/clients/arxiv.py`: paper discovery
- `app/services/pdf_service.py`: PDF download and parsing
- `app/services/chunking.py`: paragraph-aware chunking
- `app/services/embedding_service.py`: OpenAI embedding generation
- `app/services/vector_store.py`: hybrid retrieval and re-ranking
- `app/services/answer_service.py`: structured answer synthesis
- `app/services/research_pipeline.py`: end-to-end orchestration
- `app/main.py`: FastAPI API and frontend serving

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/` in your browser.

## Deploy

### Railway

This repo includes a `Dockerfile` and `railway.json`, so Railway can deploy it directly from GitHub using the Docker build path.

1. Push the repo to GitHub.
2. In Railway, create a new project from the GitHub repo.
3. Railway will detect the root `Dockerfile` and build the service from it.
4. In the Railway service settings, set the healthcheck path to `/health`.
5. Add environment variables:
   - `OPENAI_API_KEY` is required for this deployment
   - `MAX_PAPERS=5` to match the app default, or lower it manually if your instance is memory-constrained
6. Deploy and open the generated Railway domain.

Notes:
- This app serves both the frontend and backend from the same service.
- This version avoids local ML model downloads and uses OpenAI for embeddings and final answer generation.
- `data/` is ephemeral on Railway unless you attach a volume.
- If memory is tight, lower `MAX_PAPERS` manually and use a larger Railway instance if needed.

### Docker

You can also run it directly with Docker:

```bash
docker build -t ai-research-assistant .
docker run -p 8000:8000 --env OPENAI_API_KEY=your_key_here ai-research-assistant
```

## Environment

Copy `.env.example` to `.env` and set values as needed:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

`OPENAI_API_KEY` is required because this lightweight version uses OpenAI for both embeddings and final answer generation.

## Example request

```bash
curl -X POST http://127.0.0.1:8000/query ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"retrieval augmented generation for scientific question answering\",\"max_papers\":5}"
```

## Example response

```json
{
  "answer": "Based on the retrieved papers, the evidence for 'retrieval augmented generation for scientific question answering' points to ...",
  "key_points": [
    "Retrieved models improve factual grounding by conditioning generation on external scientific context. (Paper Title)",
    "Hybrid retrieval helps recover relevant evidence across dense and lexical signals. (Paper Title)"
  ],
  "citations": [
    {
      "title": "Example Paper",
      "link": "https://arxiv.org/abs/1234.5678"
    }
  ]
}
```

## Response shape

```json
{
  "answer": "string",
  "key_points": ["string"],
  "citations": [
    {
      "title": "string",
      "link": "https://example.com"
    }
  ]
}
```
