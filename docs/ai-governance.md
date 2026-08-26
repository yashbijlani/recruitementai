# AI Governance, Security, and Evaluation

## CV pipeline

`Upload -> object storage -> event -> parser/OCR -> structured extraction -> Pydantic validation -> normalization -> identity resolution -> change proposal -> human approval -> audit -> index update`.

The document service exposes `extract_text(document)` for PDF, DOCX, and TXT adapters. OCR is a separate adapter for scanned images. Raw model output is never persisted as trusted profile data: schemas, confidence, provenance, and business rules validate it first.

Use a provider interface such as `LLMProvider.extract(schema, text)` and `LLMProvider.explain(context)` so OpenAI, Azure OpenAI, or another approved provider can be substituted. Minimize PII sent externally, redact fields where possible, use environment-managed secrets, and retain provider/model/token/latency metadata.

## Identity and updates

Match in layers: normalized exact email, exact phone, name plus attributes, fuzzy identity, then semantic profile similarity. Configurable thresholds should auto-identify only high confidence matches, send medium confidence matches to review, and create a new candidate at low confidence. Never merge silently. Change detection produces field-level old/new values, confidence, source document, and an approval proposal. Approval creates an audit event; rejection leaves the profile unchanged.

## Access and data protection

Admin can manage users and audit logs; Recruiter can search, upload, approve, and edit permitted candidates; Viewer can only search/view. Enforce these permissions in API dependencies as well as hiding actions in the UI. Every query is organization-scoped. Use TLS, encrypted object storage, signed short-lived document URLs, malware scanning, retention/deletion workflows, and secret managers in production. Do not log CV text or unnecessary PII.

## Cost controls

Stage ingestion: cheap text extraction, deterministic parsing, rule-based normalization, a small model for standard extraction, a larger model only for ambiguous cases, and human review for low confidence. Generate embeddings asynchronously, cache by text/version hash, batch work, and re-embed only changed documents. Main cost drivers are document volume, OCR, model tokens, embedding refreshes, storage, and retrieval cluster size.

## Evaluation

Maintain a manually validated, stratified evaluation set rather than claiming the 1,000 seed rows are training data. Track field-level extraction precision/recall, identity precision, false merge and false-new rates, Search Precision@K/Recall@K/NDCG@K, recruiter acceptance rate, shortlist rate, and candidate conversion. Log request ID, query, retrieved IDs, scores, model/version, token usage, latency, confidence, errors, and update decisions for reproducible review.
