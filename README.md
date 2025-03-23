 # DocuSage : A PDF AI Assistant

A RAG (Retrieval-Augmented Generation) based application that allows users to upload PDFs and ask questions about their content using the Gemini AI model. The system extracts text from the PDFs, processes it into vector embeddings, and retrieves relevant content to answer user queries.

## Features

- Upload multiple PDF files (up to 20MB total)
- Extract text from PDFs and store vector embeddings
- Ask questions about the uploaded documents
- Interactive chat interface for Q&A

## Tech Stack

- **Backend:** FastAPI, LangChain, FAISS, Google Gemini AI
- **Frontend:** HTML, CSS, JavaScript (VanillaJS)
- **Libraries:** PyPDF2, FastAPI, Starlette, uvicorn, LangChain, FAISS, Google Generative AI

## Installation

### Prerequisites

- Python 3.8+
- A Google API key with access to Gemini AI

### Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/MadhavBohra/DocuSage
   cd DocuSage
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables: Create a `.env` file in the root directory and add:

   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   ```

4. Run the FastAPI server:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Access the frontend: Open `http://localhost:8000` in your browser.

## API Endpoints

### 1. Upload PDFs

**Endpoint:** `POST /upload-pdfs/`

- Accepts multiple PDF files.
- Enforces a 20MB total size limit.

### 2. Check Processing Status

**Endpoint:** `GET /processing-status/`

- Returns the current PDF processing status (`idle`, `processing`, `completed`, `failed`).

### 3. Ask a Question

**Endpoint:** `POST /ask-question/`

- Requires a `question` as a form parameter.
- Returns an AI-generated answer based on the processed PDFs.

## File Structure

```
/DocuSage
│── main.py               # FastAPI backend
│── pdf_processor.py      # PDF text extraction and AI processing
│── static/
│   ├── index.html        # Frontend UI
│   ├── script.js         # Frontend logic
│   ├── styles.css        # Styling
│── uploads/              # Temporary storage for uploaded PDFs
│── vector_store/         # FAISS vector index storage
│── .env                  # API key configuration
│── requirements.txt      # Python dependencies
```

## Future Enhancements

- Support for more file types (DOCX, TXT, etc.)
- Persistent storage for vector embeddings
- User authentication for personalized document storage

## License

MIT License

## Author

Developed by Madhav Bohra

