#  Multimode Lab 
*A multimodal LLM-powered tool that converts PDFs into presentation slides and narrated videos.*

---

##  Overview / 概要

EN:
In recent years, the cost of multimodal generation has steadily decreased, and as it continues to decline, generating text, audio, and video is becoming increasingly practical and accessible. This trend suggests new opportunities for automating content production workflows.
Multimode Lab explores this direction by prototyping a system that transforms a static PDF into narrated slides and a rendered video — positioning the project as an experiment toward future multimodal content automation.

JP（補足）：
近年、マルチモーダル生成のコストは着実に低下しており、今後さらに下がることで、テキストだけでなく音声や動画生成もより現実的な選択肢になっていくと考えられます。
こうした変化は、コンテンツ生成パイプラインの自動化に新たな可能性をもたらしつつあります。
Multimode Labtは、PDFをスライドとナレーション付き動画へ変換するシステムを試作することで、将来的なマルチモーダル生成の活用可能性を探る実験的プロジェクトです。

---

##  Demo  

- [Multimode Lab
](https://slide-pilot-474305.web.app/)
---

##  Key Features

-  PDF text extraction & structure parsing  
-  LLM-based summarization and slide content generation  
-  LangGraph-based workflow orchestration  
-  Automatic narration using text-to-speech  
-  Video generation combining slides + narration  
-  Modular architecture for experimenting with different LLM providers  
-  Browser UI for previewing and exporting output  

---

##  Architecture

### **Frontend**
- Next.js + React  
- TypeScript  
- UI preview for slides & generated video  

### **Backend**
- Python + FastAPI  
- LangGraph for workflow orchestration  
- LLM API integration (OpenAI, etc.)  
- Supabase for file handling (optional future direction)

### **Additional Components**
- Optional parallel processing for TTS & rendering  
- Video composition layer  

---

##  Tech Stack

| Category | Technologies |
|---------|-------------|
| Frontend | Next.js / React / TypeScript |
| Backend | Python / FastAPI / LangGraph |
| AI / LLM | OpenAI API (multimodal) |
| Processing | FFmpeg (planned), async workflows |
| Tools | Docker / Supabase (optional) |

---

##  My Role & Contributions

- Designed full system architecture  
- Implemented backend workflow using FastAPI + LangGraph  
- Integrated LLM API for summarization and content generation  
- Developed UI for preview and interaction  
- Experimented with parallel processing for faster rendering  
- Created automation scripts and prototypes using Python  

---

##  What I Learned

- Practical approaches to LLM API integration (not model training)  
- Workflow orchestration using LangGraph  
- Multimodal UI/UX challenges (text → slides → video)  
- Improved backend structure, naming, and async patterns  
- Balancing prototype velocity vs. maintainable architecture  

---

##  Usage / Quick Start

> Note: Environment variables are required for LLM API access (setup instructions in progress).

```sh
git clone https://github.com/miyata09x0084/slide-pilot
cd slide-pilot

# 1. LangGraph (AI Engine) - Run in the repository root
python3.11 -m langgraph_cli dev --host 0.0.0.0 --port 2024

# 2. FastAPI (Gateway)
cd backend/app && python3 main.py

# 3. Frontend
cd frontend && npm install && npm run dev
```
