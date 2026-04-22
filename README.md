# 🔍 Multimodal RAG System
A production-grade Retrieval-Augmented Generation (RAG) system capable of analyzing
PDF documents containing text, images, and tables — and answering questions about them
using a fully open-source stack.

---

## Tech Stack

| Layer | Tool |
|---|---|
| UI | Gradio |
| LLM (text) | Mistral 7B via Ollama |
| LLm (vision) | LLAVA 7B via Ollama |
| Embeddings | BGE-M3 (sentence-transformers) |
| Vector DB | Qdrant |
| PDF parsing | PyMuPDF + pdfplumber |
| OCR | pytesseract |
| Finetuning | LoRA (embeddings) + QLoRA (LLM) |
| CI/CD | Github Actions |
| Deployment | AWS ECS + ECR |

---

