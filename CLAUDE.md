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

```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start LangGraph development server (port 2024)
langgraph dev

# Direct execution (for testing the agent without the API server)
python slide_agent.py
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

### LangGraph Workflow (backend/slide_agent.py)

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

### Evaluation Criteria (Phase 3)

The `evaluate_slides_slidev` node uses weighted scoring:
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

### Backend Health Check

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

### Frontend Development URLs

- **Frontend dev server**: http://localhost:5173
- **LangGraph API**: http://localhost:2024
- **LangGraph Studio**: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

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
