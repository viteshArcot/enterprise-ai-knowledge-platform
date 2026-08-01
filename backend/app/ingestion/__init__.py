"""
Document ingestion pipeline — package root.

The ingestion pipeline handles the full lifecycle of importing external
content into the knowledge base: source acquisition → parsing → chunking
→ embedding → storage.

Phase 1 (current): Package structure only.
  Nothing is implemented. The package exists to signal architectural intent
  and reserve the namespace so future work can be added without restructuring.

Phase 2 (planned):
  - File upload API (PDF, DOCX, TXT, Markdown)
  - Format-agnostic document parser (uses Unstructured.io or equivalent)
  - Document metadata extraction (title, author, date, source URL)
  - Storage in PostgreSQL with chunked text

Phase 3 (planned):
  - Chunking strategies (fixed-size, sentence, semantic)
  - Embedding pipeline (OpenAI text-embedding-3-small, BGE-M3)
  - pgvector storage for dense retrieval
  - BM25 index for sparse retrieval

Phase 4 (planned):
  - Async ingestion queue (Celery + Redis or ARQ)
  - Progress tracking and webhook notifications
  - Multi-tenant isolation

Connector roadmap (Phase 3+):
  - Confluence Cloud
  - SharePoint / OneDrive
  - Google Drive
  - Notion
  - GitHub Repositories
  - Web crawl / sitemap
"""
