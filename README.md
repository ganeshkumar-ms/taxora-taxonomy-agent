# TAXORA — AI Taxonomy Expert

> Organize it.

## Prerequisites
- Python 3.10+
- Node.js 18+
- AWS account with Bedrock access (Nova Pro model enabled in us-east-1)

## Backend Setup

```bash
cd taxora/backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
# Edit .env with your AWS credentials
uvicorn main:app --reload --port 8000
```

## Frontend Setup

```bash
cd taxora/frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

## Usage

1. Open **http://localhost:3000**
2. Type text or upload a document (PDF, DOCX, TXT, CSV, XLSX)
3. TAXORA classifies it into the enterprise taxonomy and explains why
4. Approve, Edit, or Reject the recommendation
5. Ask follow-up questions in the same conversation

## AWS Setup

- Enable Amazon Bedrock in `us-east-1`
- Request access to **Amazon Nova Pro** (`us.amazon.nova-pro-v1:0`)
- Set AWS credentials in `.env`

## Project Structure

```
taxora/
├── backend/
│   ├── main.py                    ← FastAPI app entry point
│   ├── routers/
│   │   └── classify.py            ← /api/classify, /api/taxonomy, /api/feedback
│   ├── services/
│   │   ├── bedrock_service.py     ← AWS Bedrock (Nova Pro) integration
│   │   ├── document_service.py    ← PDF/DOCX/CSV/XLSX text extraction
│   │   └── taxonomy_service.py    ← Taxonomy loader + formatter
│   ├── models/
│   │   └── schemas.py             ← Pydantic request/response models
│   ├── taxonomy/
│   │   └── taxonomy.json          ← Single source of truth for all categories
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── package.json
    └── src/
        ├── main.jsx
        ├── App.jsx                 ← Root state, session management
        ├── App.css                 ← All CSS (exact match to HTML prototype)
        ├── components/
        │   ├── AuroraBackground.jsx
        │   ├── HomePage.jsx
        │   ├── ChatPage.jsx
        │   ├── Sidebar.jsx
        │   ├── MessageList.jsx
        │   ├── Composer.jsx
        │   ├── ThinkingBubble.jsx
        │   └── ClassificationResult.jsx
        └── services/
            └── api.js              ← axios API calls
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/taxonomy` | Full taxonomy tree (JSON) |
| POST | `/api/classify` | Classify text/document |
| POST | `/api/feedback` | Record human review decision |

## Notes

- Taxonomy is **only** defined in `backend/taxonomy/taxonomy.json` — the frontend never hardcodes any category names
- Sessions are persisted in browser `localStorage`
- The `ClassificationResult` component shows confidence-color-coded badges, expandable explanations, alternatives, and human review buttons
