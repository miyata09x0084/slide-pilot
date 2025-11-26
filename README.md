# Multimode Lab – PDFから動画を自動生成する実験プロダクト

難しいPDFを、わかりやすい動画に。LangGraphで構築したエージェントが、PDF解析からスライド生成、ナレーション音声、動画化までを自動で行います。

## できること
- PDFを数分で要約し、スライド＋ナレーション動画を生成
- LLMによる台本生成とOpenAI TTSを最大5並列で実行し高速化
- 生成した動画をブラウザでプレビューし、そのままダウンロード

## 使い方
1. Googleでログイン
2. PDFをアップロード
3. 数分待つ
4. 生成された動画をプレビュー/ダウンロード

## ワークフロー（5ステップ）
```
解析 → 要約/目次 → スライドレンダリング → ナレーション/TTS → 動画書き出し
```

## ユースケースとメリット
- 社内共有: 長い資料のポイントを動画で短時間キャッチアップ
- 顧客説明: サービス説明資料を動画化し、閲覧ハードルを下げる
- 教育用途: 学習者向けに、難解PDFを平易な動画に変換
- メリット: 速い（数分）、安い（自動生成）、分かりやすい（音声＋スライド）

## アーキテクチャ
- **Frontend**: React 19 + TypeScript, Google OAuth
- **Backend**: FastAPI（port 8001）+ LangGraph（port 2024）
- **AI/生成**: GPT-4 (LLM)、OpenAI TTS、Slidevベースのスライドレンダリング（独自レンダラー）
- **データ/その他**: Supabase（Auth/Storage）、Tavily検索

## セットアップ
- 前提: Python 3.11+, Node.js 18+, 必要なAPI Key（後日整備）

```bash
# 1. LangGraph（AI Engine）- リポジトリルートで実行
python3.11 -m langgraph_cli dev --host 0.0.0.0 --port 2024

# 2. FastAPI（Gateway）
cd backend/app && python3 main.py

# 3. Frontend
cd frontend && npm install && npm run dev
```

→ http://localhost:5173

## 進行中/制約
- 実験段階。モデル/速度/コストは今後調整予定
- 一部機能は内部用の設定やキーが必要です

## 背景（簡略版）
マルチモーダル生成コストが急速に低下しており、動画/音声も個別最適化が現実的になりつつあります。Multimode Labはその将来を見越し、PDFから動画への自動変換パイプラインを検証する実験です。より詳細な実装メモや設計は [CLAUDE.md](./CLAUDE.md) を参照してください。

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

## License
MIT License

## Contributing
Issue、PR歓迎。技術詳細: [CLAUDE.md](./CLAUDE.md)
