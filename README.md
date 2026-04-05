# AI Research Assistant Agent

Production-oriented FastAPI backend that searches research papers, downloads and parses PDFs, builds embeddings, retrieves relevant evidence, and answers with citations.

## Features

- `POST /query` executes the full research workflow
- `/` serves a lightweight frontend for submitting research questions
- arXiv paper discovery
- PDF download and text extraction
- local embedding generation with `sentence-transformers`
- in-memory vector retrieval for request-scoped RAG
- structured JSON answers with citations
- optional OpenAI answer synthesis when `OPENAI_API_KEY` is configured

## Architecture

- `app/clients/arxiv.py`: paper discovery
- `app/services/pdf_service.py`: PDF download and parsing
- `app/services/chunking.py`: paragraph-aware chunking
- `app/services/embedding_service.py`: embedding generation
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

## Environment

Copy `.env.example` to `.env` and set values as needed:

```env
OPENAI_API_KEY=
```

If `OPENAI_API_KEY` is omitted, the system still returns structured responses using extractive synthesis from retrieved paper content.

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
