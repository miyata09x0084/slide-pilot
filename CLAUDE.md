# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SlidePilot is an AI-powered presentation slide generation system that automatically creates Slidev slides about AI industry news. It uses:
- **LangGraph** for orchestrating a multi-step AI agent workflow with quality evaluation
- **OpenAI GPT-4** for content generation
- **Tavily** for real-time web search (recent AI news from major vendors)
- **Slidev** for slide rendering (Markdown → PDF/HTML with modern design)
- **React + TypeScript** frontend with Google OAuth authentication

## Commands

### Backend Development

**Important**: You need to run **two servers** for full functionality:

#### 1. FastAPI Server (Port 8001) - Main API Gateway

```bash
cd backend/src
python3 main.py
# Alternative: uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

This server handles:
- PDF upload and download
- Slide download
- **LangGraph API proxy** (routes `/api/agent/*` to LangGraph server)
- Health checks

#### 2. LangGraph Server (Port 2024) - AI Agent Engine

```bash
cd backend
python3.11 -m langgraph_cli dev --host 0.0.0.0 --port 2024

# または、Python 3.11がデフォルトの場合:
# langgraph dev
```

**Note**:
- Requires Python 3.11+ for LangGraph dev server
- `langgraph dev` コマンドはPython 3.10では動作しません（`langgraph-api`が必要）
- 確実に動作させるには `python3.11 -m langgraph_cli dev` を使用してください

This server handles:
- AI agent workflow execution
- ReAct agent (Gmail + Slides)
- SSE streaming for real-time progress

**Architecture**:
```
Frontend (localhost:5173)
    ↓ All requests to localhost:8001
FastAPI (port 8001)
    ├── /api/upload-pdf → Direct handling
    ├── /api/slides/{fn} → Direct handling
    └── /api/agent/* → Proxy to LangGraph (port 2024)
            ↓
    LangGraph (port 2024) - Internal service
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server (port 5173)
npm run dev

# Build for production
npm run build

# Lint code
npm run lint

# Preview production build
npm run preview
```

## Architecture

### Backend Directory Structure (FastAPI + LangGraph)

```
backend/
├── src/
│   ├── main.py          # FastAPI application entry point
│   ├── config.py        # Unified settings (FastAPI + environment)
│   ├── dependencies.py  # FastAPI dependency injection
│   │
│   ├── routers/         # FastAPI routers (follows official pattern)
│   │   ├── health.py    # Health check endpoint
│   │   ├── uploads.py   # PDF upload endpoint
│   │   ├── slides.py    # Slide download endpoint
│   │   └── agent.py     # LangGraph API proxy (NEW)
│   │
│   ├── agents/          # LangGraph workflow definitions
│   │   ├── react_agent.py       # ReAct agent (Gmail + Slides)
│   │   └── slide_workflow.py    # Slide generation workflow
│   │
│   ├── tools/           # Tool implementations
│   │   ├── gmail.py     # Gmail sending
│   │   ├── pdf.py       # PDF text extraction
│   │   └── slides.py    # Slide generation tool wrapper
│   │
│   ├── core/            # Core utilities (LangGraph)
│   │   ├── config.py    # Environment variables (legacy, for agents)
│   │   ├── llm.py       # LLM client (OpenAI GPT-4)
│   │   └── utils.py     # Shared utility functions
│   │
│   ├── prompts/         # Prompt definitions
│   │   ├── slide_prompts.py       # Slide generation prompts
│   │   └── evaluation_prompts.py  # Evaluation prompts
│   │
│   └── auth/            # Authentication
│       └── gmail.py     # Gmail OAuth flow
│
├── data/
│   ├── uploads/         # Uploaded PDF files
│   └── slides/          # Generated slides
│
├── tests/               # Test files
└── langgraph.json       # LangGraph configuration
```

**Key architectural decisions**:
- **`routers/`** instead of `api/`: Follows FastAPI official documentation pattern
- **Dependency injection**: Path configuration via `dependencies.py` (DRY principle)
- **Unified settings**: `config.py` manages both FastAPI and environment variables
- **Proxy pattern**: FastAPI proxies LangGraph API (`/api/agent/*` → `localhost:2024`)
  - Frontend only connects to single endpoint (`localhost:8001`)
  - CORS managed in one place (FastAPI)
  - LangGraph runs as internal service
  - Performance overhead: +1-2ms (negligible)

### LangGraph Workflow (backend/src/agents/slide_workflow.py)

The backend is a **stateful LangGraph agent** with quality evaluation (Phase 3):

```
START → collect_info → generate_key_points → generate_toc → write_slides_slidev → evaluate_slides_slidev → save_and_render_slidev → END
                                                                                              ↓
                                                                                        (if score < 8.0)
                                                                                              ↓
                                                                  retry ← ← ← ← ← ← ← ← ← ← ← ←
```

**Node Responsibilities:**
1. **collect_info**: Searches Tavily for recent AI news (last 2 months) from official domains (Microsoft, OpenAI, Google, AWS, Meta, Anthropic)
2. **generate_key_points**: Extracts 5 key points from search results using GPT-4
3. **generate_toc**: Creates 5-8 section outline for the slide deck
4. **write_slides_slidev**: Generates Slidev-formatted markdown slides with modern design (apple-basic theme, v-clicks animation, two-cols layout)
5. **evaluate_slides_slidev**: Scores slides on 5 criteria (structure, practicality, accuracy, readability, conciseness) - must score ≥8.0 to pass
6. **save_and_render_slidev**: Saves markdown and renders to PDF using slidev export with Playwright/Chromium

**Key Design Decision**: The evaluation loop (max 3 attempts) ensures quality output. If evaluation fails, the workflow retries from `generate_key_points` with feedback.

### State Flow

The `State` TypedDict in backend/slide_agent.py flows through all nodes:

```python
State = {
    # Input
    "topic": str,

    # Intermediate data
    "sources": Dict[str, List[Dict]],      # Tavily search results
    "key_points": List[str],               # 5 key points
    "toc": List[str],                      # Table of contents
    "slide_md": str,                       # Generated markdown

    # Evaluation
    "score": float,                        # 0-10 score
    "passed": bool,                        # ≥8.0 threshold
    "attempts": int,                       # Retry counter (max 3)

    # Output
    "slide_path": str,                     # Saved file path
    "title": str,                          # Japanese title
    "error": str,                          # Error messages
    "log": List[str]                       # Execution logs
}
```

### Frontend Architecture

**Stack**: React 19 + TypeScript + Vite
**Authentication**: Google OAuth via `@react-oauth/google`
**API Communication**: Fetch API with Server-Sent Events (SSE) streaming

**Key Flow** (App.tsx:85-159):
1. User creates a thread (`POST /threads`)
2. User submits topic → frontend streams from `POST /threads/{id}/runs/stream`
3. Backend sends SSE events in format: `data: {"event": "updates", "data": {...}}\n\n`
4. Frontend parses SSE chunks, extracts node names, displays progress
5. When `save_and_render` node completes, download link appears

**State Management**: Component-level useState (no external state library). Key states:
- `threadId`: LangGraph thread identifier
- `progress`: Array of node execution status messages
- `slideData`: Final output (markdown, file path, title)
- `user`: Google OAuth user info (persisted to localStorage)

## Configuration

### Backend Environment Variables (backend/.env)

```bash
OPENAI_API_KEY=sk-...           # Required: OpenAI API key
TAVILY_API_KEY=tvly-...         # Required: Tavily search API key
LANGCHAIN_TRACING_V2=true       # Optional: Enable LangSmith tracing
LANGCHAIN_PROJECT=marp-agent    # Optional: LangSmith project name
LANGCHAIN_API_KEY=lsv2_...      # Optional: LangSmith API key
SLIDE_FORMAT=pdf                # Optional: Output format (pdf/png/html/empty for .md only)
MARP_THEME=default              # Optional: Marp theme (default/gaia/uncover)
MARP_PAGINATE=true              # Optional: Show page numbers
```

### Frontend Environment Variables (frontend/.env.local)

```bash
VITE_GOOGLE_CLIENT_ID=...       # Required: Google OAuth 2.0 Client ID
```

Get OAuth credentials from: https://console.cloud.google.com/apis/credentials

### LangGraph Configuration (backend/langgraph.json)

- Defines the graph export path: `react_agent.py:graph`
- Graph ID: `react-agent`
- LangGraph version: 0.5.2

## Important Implementation Details

### Slidev Slide Generation (Phase 0-3)

The `write_slides_slidev` node generates slides with modern design:
- **Theme**: apple-basic (clean, professional design)
- **Animations**: `<v-clicks>` for progressive disclosure
- **Layouts**: `two-cols` for vendor comparisons, `center` for summary
- **Visual enhancements**: Emojis, bold keywords, dates in bullets (Phase 2)
- **Multi-vendor coverage**: All 6 AI vendors (Microsoft, OpenAI, Google, AWS, Meta, Anthropic)
- **YAML frontmatter**: Slidev configuration (theme, layout, fonts)
- **Japanese titles**: Uses JST timezone to generate month-based titles

**Key features**:
- LLM generates optimized bullets with emojis, bold formatting, and dates
- Gradient backgrounds per vendor
- Summary slide with all vendor key points
- PDF export via `slidev export` with Playwright/Chromium

### SSE Streaming Protocol

LangGraph API returns Server-Sent Events:
```
data: {"event": "updates", "data": {"collect_info": {...}}}

data: {"event": "updates", "data": {"generate_key_points": {...}}}

data: {"event": "end"}
```

Frontend parsing (App.tsx:122-151):
1. Read stream chunks with `getReader()`
2. Decode bytes to text with `TextDecoder`
3. Split on `\n`, parse lines starting with `data: `
4. Extract node names from JSON keys
5. Map to human-readable progress messages via `nodeNames` lookup

### Prompt Management (Issue #23 Phase 3)

All prompts are externalized in `backend/src/prompts/`:

**`slide_prompts.py`** - Slide generation prompts:
- `get_key_points_map_prompt()` - PDF chunk → key points (Map phase)
- `get_key_points_reduce_prompt()` - Consolidate key points to 5 (Reduce phase)
- `get_key_points_ai_prompt()` - AI news → key points
- `get_toc_pdf_prompt()` - PDF key points → table of contents
- `get_toc_ai_prompt()` - AI key points → table of contents
- `get_slide_title_prompt()` - Generate slide title from PDF
- `get_slide_pdf_prompt()` - Generate Slidev markdown from PDF
- `get_slug_prompt()` - Japanese title → English filename

**`evaluation_prompts.py`** - Evaluation prompts:
- `get_evaluation_prompt()` - Slide quality evaluation (switches criteria based on input type)

**Design pattern**: Constants + Methods (Hybrid)
- Prompt text defined as constants (easy to version control, readable diffs)
- Methods provide type-safe interface with argument validation
- Example:
  ```python
  # Constant
  KEY_POINTS_MAP_USER = "以下のテキストから...{chunk}...{chunk_index}"

  # Method
  def get_key_points_map_prompt(chunk: str, chunk_index: int):
      return [("system", SYSTEM), ("user", USER.format(chunk=chunk[:3000], chunk_index=chunk_index))]
  ```

**How to customize prompts**:
1. Edit constants in `backend/src/prompts/*.py`
2. No code changes needed in `slide_workflow.py`
3. Restart `langgraph dev` to apply changes

### Evaluation Criteria (Phase 3)

The `evaluate_slides_slidev` node uses weighted scoring with **different criteria based on input type**:

**PDF input** (for educational slides):
- **structure** (20%): Logical flow, one-message-per-slide principle
- **comprehensiveness** (25%): Covers all important topics from PDF
- **clarity** (25%): Middle-school friendly language, term explanations
- **readability** (15%): Clarity, visual hierarchy, emoji usage
- **engagement** (15%): Storytelling, conversation format, visual elements

**AI news input** (for technical reports):
- **structure** (20%): Logical flow, one-message-per-slide principle
- **practicality** (25%): Actionable content, specific examples, warnings
- **accuracy** (25%): Factual correctness, terminology
- **readability** (15%): Clarity, visual hierarchy, bullet point granularity
- **conciseness** (15%): Minimal redundancy

**Pass threshold**: 8.0/10.0 total score
**Max retries**: 3 attempts (controlled by `MAX_ATTEMPTS` constant)
**Retry behavior**: If evaluation fails, workflow retries from `generate_key_points` with feedback

### Tavily Search Strategy

The `collect_info` node searches for AI news from the **last 2 months** across vendor-specific domains:

```python
vendors_domains = [
    (["azure.microsoft.com", "news.microsoft.com"], ["Microsoft AI updates", "Azure OpenAI updates"]),
    (["openai.com"], ["OpenAI announcements"]),
    (["blog.google", "ai.googleblog.com"], ["Google AI updates", "Gemini updates"]),
    (["aws.amazon.com"], ["AWS Bedrock updates"]),
    (["ai.meta.com"], ["Meta AI updates", "Llama updates"]),
    (["anthropic.com"], ["Anthropic Claude updates"]),
]
```

Each query is scoped to `include_domains` and `time_range: "month"` to ensure fresh, authoritative sources.

## Testing the System

### FastAPI Server Health Check

```bash
# Check root endpoint
curl http://localhost:8001/

# Check health endpoint
curl http://localhost:8001/api/health

# Upload PDF test
curl -X POST http://localhost:8001/api/upload-pdf \
  -F "file=@/path/to/test.pdf"

# Access API documentation
open http://localhost:8001/docs
```

### LangGraph Server Health Check

```bash
# Check server is running
curl http://localhost:2024/ok

# Get assistant ID
curl -X POST http://localhost:2024/assistants/search -H "Content-Type: application/json" -d '{"limit": 1}'

# Create thread
curl -X POST http://localhost:2024/threads -H "Content-Type: application/json" -d '{}'

# Run agent (replace {thread_id} and {assistant_id})
curl -N -X POST "http://localhost:2024/threads/{thread_id}/runs/stream" \
  -H "Content-Type: application/json" \
  -d '{"assistant_id": "{assistant_id}", "input": {"topic": "AI最新情報"}, "stream_mode": ["updates"]}'
```

### Development URLs

- **Frontend dev server**: http://localhost:5173
- **FastAPI server** (main gateway): http://localhost:8001
  - Swagger UI: http://localhost:8001/docs
  - Health check: http://localhost:8001/api/health
  - LangGraph proxy: http://localhost:8001/api/agent/*
- **LangGraph API** (internal): http://localhost:2024
  - Direct access: http://localhost:2024/ok
  - LangGraph Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

**Note**: Frontend should only connect to `http://localhost:8001` (FastAPI), which proxies LangGraph requests internally.

## Troubleshooting

### "Slidev not found" or PDF export fails
Install Slidev CLI and Playwright globally:
```bash
npm install -g @slidev/cli
npm install -g playwright-chromium
npx playwright-chromium install chromium
```
Without these, PDF export will fail (slides saved as `.md` only).

### CORS errors in frontend
The LangGraph dev server should allow CORS by default. If issues persist, add proxy configuration to `frontend/vite.config.ts`:
```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:2024',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

### Evaluation loop never passes
Check `state["log"]` for evaluation feedback. Common issues:
- Missing source citations in slides
- Too much content per slide (violates "one message per slide")
- Factual errors not found in Tavily search results

### Google OAuth fails
1. Verify `VITE_GOOGLE_CLIENT_ID` is set in `frontend/.env.local`
2. Ensure authorized redirect URIs include `http://localhost:5173` in Google Cloud Console
3. Clear browser localStorage and retry login
