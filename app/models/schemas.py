from pydantic import BaseModel, Field, HttpUrl


class QueryRequest(BaseModel):
    query: str = Field(min_length=3, description="Research question or topic to investigate.")
    max_papers: int | None = Field(default=None, ge=1, le=10)


class Citation(BaseModel):
    title: str
    link: HttpUrl | str


class QueryResponse(BaseModel):
    answer: str
    key_points: list[str]
    citations: list[Citation]


class Paper(BaseModel):
    paper_id: str
    title: str
    summary: str
    pdf_url: HttpUrl | str
    entry_url: HttpUrl | str
    published: str
    authors: list[str]


class ParsedDocument(BaseModel):
    paper: Paper
    pdf_path: str
    text: str
    page_count: int


class DocumentChunk(BaseModel):
    chunk_id: str
    paper_id: str
    title: str
    content: str
    source_url: HttpUrl | str


class RetrievedChunk(BaseModel):
    chunk: DocumentChunk
    score: float
    semantic_score: float
    lexical_score: float
