# ラクヨミ

PDFをマルチモーダルなスライドに変換する実験プロジェクト（開発途中）

## 現在の機能

技術論文や資料PDFを、テキスト+ビジュアルのスライド形式に変換します。

**注意**: マルチモーダルコンテンツ生成への移行途中のため、機能は限定的です。

**使い方**: Googleログイン → PDFアップロード → 2-5分待つ → ダウンロード

---

## なぜ作ったか

### 技術的背景

AIのスケーリング法則（モデルを大きくするほど性能が上がるという法則）が正しければ、こんなことが起きるはずです：

- 訓練が効率化されて、小さいモデルでも高性能になる
- 使うときのコストがどんどん下がる
- テキスト・画像・動画・音声、全部で同じことが起きる

実際、ここ2年で観測されているデータ：

| 種類 | 変化 | 出典 |
|------|------|------|
| **テキスト** | コスト2年で280分の1 | [All You Need to Know about Inference Cost](https://primitiva.substack.com/p/all-you-need-to-know-about-inference) |
| **テキスト** | 生成速度169.5 tokens/sec | [Gemini 2.0 Flash benchmark](https://artificialanalysis.ai/models/gemini-2-0-flash) |
| **画像** | 訓練費用$1で実行可能 | [Fine-tune Stable Diffusion with LoRA](https://julsimon.medium.com/fine-tune-stable-diffusion-with-lora-for-as-low-as-1-58b4a459fd0b) |
| **動画** | 開発費$200Kで商用品質 | [Open-Sora 2.0 paper](https://arxiv.org/abs/2503.09642) |
| **動画** | 生成時間3分（10倍高速化） | [Open-Sora 2.0: Cost-Efficient Excellence](https://medium.com/@cerebroneai/open-sora-2-0-ai-video-generation-with-cost-efficient-excellence-23cdd30ee624) |
| **音声** | 人間録音比70-90%削減 | [Text to Speech Guide 2025](https://callin.io/text-to-speech-the-definitive-guide-to-voice-synthesis-technology-in-2025/) |

このデータが正しければ、一人ひとりに合わせたコンテンツを作ってもコストが見合うようになる、ということです。

実際の事例：
- **Khan Academy**: Khanmigo（GPT-4ベース）で個人別学習パス提供 [[実装詳細]](https://www.khanmigo.ai/)
- **適応型学習**: Knewtonの研究で10,000人の学生がテストスコア62%向上 [[研究]](https://axonpark.com/how-effective-is-ai-in-education-10-case-studies-and-examples/)
- **企業TTS導入**: コスト70-90%削減の報告 [[統計]](https://callin.io/text-to-speech-the-definitive-guide-to-voice-synthesis-technology-in-2025/)

### このプロジェクトについて

スケーリング法則が正しく、この傾向が続くなら、数年後には「一人ひとりに最適化されたマルチモーダルコンテンツがその場で生成される」世界が来るはずです。

その未来を見越して作っています。GPT-4でテキスト、Slidevでビジュアルを生成する形で、個人向けコンテンツ生成の実現可能性を確認中です。

あくまで実験用です。

---

## 技術スタック

- **Frontend**: React 19 + TypeScript, Google OAuth
- **Backend**: FastAPI（port 8001）+ LangGraph（port 2024）
- **AI**: OpenAI GPT-4, Tavily検索, Slidev出力

### ワークフロー

```
情報収集 → 要点抽出 → 目次生成 → スライド執筆 → 品質評価（8.0/10点）→ PDF化
                                              ↓（不合格なら最大3回リトライ）
```

---

## セットアップ

### 必要なもの
- Python 3.11+, Node.js 18+
- 各種API Key（詳細は準備中）

### 環境変数

準備中

### 起動

```bash
# 1. LangGraph（AI Engine）- リポジトリルートで実行
python3.11 -m langgraph_cli dev --host 0.0.0.0 --port 2024

# 2. FastAPI（Gateway）
cd backend/app && python3 main.py

# 3. Frontend
cd frontend && npm install && npm run dev
```

→ http://localhost:5173

---

## プロジェクト構造

```
slide-pilot/
├── backend/app/
│   ├── routers/      # API endpoints
│   ├── agents/       # LangGraphワークフロー
│   ├── tools/        # Gmail, PDF, Slides
│   └── prompts/      # プロンプト管理
├── frontend/src/
└── langgraph.json
```

詳細: [CLAUDE.md](./CLAUDE.md)

---

## License

MIT License

## Contributing

Issue、PR歓迎。技術詳細: [CLAUDE.md](./CLAUDE.md)
