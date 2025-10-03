# LangGraphとフロントエンド統合ガイド

## 概要

このガイドでは、LangGraph APIとフロントエンドを段階的に統合する方法を説明します。
**各フェーズで動作確認を行い、エラーが発生したら前のフェーズに戻って原因を特定できる設計**になっています。

---

## 全体構成

```
Phase 0 (バックエンド検証) → Phase 1 (最小HTML) → Phase 2 (スレッド作成) →
Phase 3 (ストリーミング) → Phase 4 (React化) → Phase 5 (useStream統合) → Phase 6 (UI改善)
```

**推奨実装順序**:
- **最速ルート**: Phase 0 → Phase 1 → Phase 3 → Phase 5 → Phase 6
- **学習ルート**: Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6

---

## Phase 0: バックエンド検証（5分）

### 目的
LangGraph APIサーバーが正常に動作しているか確認

### 実施手順

#### ステップ0.1: サーバー起動確認
```bash
curl http://localhost:2024/ok
```
**期待結果**: `200 OK` または `{"ok": true}`

#### ステップ0.2: アシスタント情報取得
```bash
curl -X POST http://localhost:2024/assistants/search \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'
```
**期待結果**:
```json
[{
  "assistant_id": "d67b2a76-c1e8-53af-a4d3-ce8399c3c72a",
  "graph_id": "poc-aiagent",
  ...
}]
```
**重要**: `assistant_id`を**メモする**（後で使用）

#### ステップ0.3: スレッド作成テスト
```bash
curl -X POST http://localhost:2024/threads \
  -H "Content-Type: application/json" \
  -d '{}'
```
**期待結果**: `{"thread_id": "...", ...}`

#### ステップ0.4: ストリーミング動作確認
```bash
curl -N -X POST "http://localhost:2024/threads/{thread_id}/runs/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "{assistant_id}",
    "input": {"topic": "test"},
    "stream_mode": ["updates"]
  }'
```
**期待結果**: SSE形式のストリームデータ
```
data: {"event": "updates", "data": {...}}

data: {"event": "updates", "data": {...}}
```

### 成功判定
✅ 全てのcurlコマンドが正常に応答する

### エラー時の対処
- ❌ サーバーが応答しない → `langgraph dev`で再起動
- ❌ OpenAI APIエラー → APIキー確認（Phase 0で停止）

---

## Phase 1: 最小HTML（10分）

### 目的
ブラウザからLangGraph APIに接続できることを確認

### ファイル構成
```
frontend/
└── index.html  # 新規作成
```

### 実施手順

#### HTMLファイル作成
**ファイル**: `frontend/index.html`

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>LangGraph Test</title>
</head>
<body>
  <h1>LangGraph API Test</h1>
  <button onclick="testApi()">アシスタント情報を取得</button>
  <pre id="result"></pre>

  <script>
    async function testApi() {
      try {
        const res = await fetch('http://localhost:2024/assistants/search', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({limit: 10})
        });
        const data = await res.json();
        document.getElementById('result').textContent = JSON.stringify(data, null, 2);
      } catch (error) {
        document.getElementById('result').textContent = 'ERROR: ' + error.message;
      }
    }
  </script>
</body>
</html>
```

#### 実行方法
```bash
# 方法1: 直接開く
open frontend/index.html

# 方法2: ローカルサーバー起動
python3 -m http.server 8000 --directory frontend
# ブラウザで http://localhost:8000
```

### 成功判定
✅ ボタンをクリック → アシスタント情報（JSON）が表示される

### エラー時の対処
#### CORSエラー（最も一般的）
```
Access to fetch at 'http://localhost:2024' has been blocked by CORS policy
```

**解決策**: Phase 1で停止し、サーバーのCORS設定を確認

#### Failed to fetch
→ サーバーが起動しているか確認

---

## Phase 2: スレッド作成（10分）

### 目的
ユーザー入力からスレッドを作成する機能を追加

### 実施手順

#### Phase 1のHTMLに追加
```html
<!-- index.html の <body> に追加 -->
<hr>
<h2>Step 2: スレッド作成</h2>
<input id="topic" type="text" placeholder="トピックを入力" value="AI最新情報">
<button onclick="createThread()">スレッド作成</button>
<div id="thread-info"></div>

<script>
let threadId = null;  // グローバル変数で保持

async function createThread() {
  try {
    const res = await fetch('http://localhost:2024/threads', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({})
    });
    const data = await res.json();
    threadId = data.thread_id;  // 保存
    document.getElementById('thread-info').innerHTML =
      `✅ Thread created: <code>${threadId}</code>`;
  } catch (error) {
    document.getElementById('thread-info').textContent = '❌ ERROR: ' + error.message;
  }
}
</script>
```

### 成功判定
✅ ボタンクリック → Thread IDが表示される
✅ `threadId`変数に値が保存される

### デバッグポイント
- ブラウザのDevTools > Network タブでリクエスト確認
- `console.log(data)` を追加して返却値を確認

---

## Phase 3: ストリーミング実装（20分）

### 目的
Fetch APIを使ってストリームデータをリアルタイム受信

### 技術的な仕組み

#### SSE（Server-Sent Events）形式
LangGraph APIは以下の形式でデータを送信:
```
data: {"event": "updates", "data": {"collect_info": {...}}}

data: {"event": "updates", "data": {"generate_key_points": {...}}}

data: {"event": "end"}
```

#### Fetch APIでの受信
```javascript
const response = await fetch('http://localhost:2024/threads/{thread_id}/runs/stream', {
  method: 'POST',
  body: JSON.stringify({...})
});

const reader = response.body.getReader();  // ストリームリーダー取得
const decoder = new TextDecoder();

while (true) {
  const {done, value} = await reader.read();  // チャンクを1つ読む
  if (done) break;

  const chunk = decoder.decode(value);  // バイナリ→文字列
  // chunk = "data: {...}\n\ndata: {...}\n\n" のような形式
}
```

### 実施手順

#### Phase 2のHTMLに追加
```html
<hr>
<h2>Step 3: エージェント実行（ストリーミング）</h2>
<button onclick="runAgent()">実行</button>
<div id="status"></div>
<ul id="progress"></ul>

<script>
async function runAgent() {
  if (!threadId) {
    alert('まずスレッドを作成してください');
    return;
  }

  const topic = document.getElementById('topic').value;
  const statusEl = document.getElementById('status');
  const progressEl = document.getElementById('progress');

  statusEl.textContent = '⏳ Running...';
  progressEl.innerHTML = '';

  try {
    // 1. assistant_idを取得
    const assistantRes = await fetch('http://localhost:2024/assistants/search', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({limit: 1})
    });
    const assistants = await assistantRes.json();
    const assistantId = assistants[0].assistant_id;

    // 2. ストリーミング開始
    const response = await fetch(`http://localhost:2024/threads/${threadId}/runs/stream`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        assistant_id: assistantId,
        input: {topic: topic},
        stream_mode: ['updates']  // 'updates' = ノードの更新のみ
      })
    });

    // 3. ストリームを読む
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      console.log('受信:', chunk);  // デバッグ用

      // 4. SSE形式をパース
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const json = JSON.parse(line.slice(6));  // "data: " を除去
            const li = document.createElement('li');
            li.textContent = JSON.stringify(json);
            progressEl.appendChild(li);
          } catch (e) {
            console.warn('Parse error:', e);
          }
        }
      }
    }

    statusEl.textContent = '✅ Complete!';
  } catch (error) {
    statusEl.textContent = '❌ ERROR: ' + error.message;
    console.error(error);
  }
}
</script>
```

### 成功判定
✅ ボタンクリック → リスト（`<ul>`）に各ノードの更新が順次表示される
✅ ブラウザのConsoleに `console.log` の出力が表示される

### デバッグポイント
1. **Network タブ**: `runs/stream` リクエストを確認
   - Status: 200 OK
   - Response: ストリームデータが流れている
2. **Console タブ**: `chunk` の内容を確認
   - `data: {...}` 形式か確認
3. **エラー時**: `console.error(error)` で詳細を確認

---

## Phase 4: React化（30分）

### 目的
HTMLからReactに移行（状態管理を導入）

### ファイル構成
```
frontend/
├── package.json
├── vite.config.ts
├── index.html
└── src/
    ├── main.tsx
    └── App.tsx
```

### 実施手順

#### ステップ4.1: Viteプロジェクト作成
```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
```

#### ステップ4.2: 最小構成のApp.tsx
**ファイル**: `frontend/src/App.tsx`

```tsx
import { useState } from 'react';

function App() {
  const [result, setResult] = useState('');

  const testApi = async () => {
    try {
      const res = await fetch('http://localhost:2024/assistants/search', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({limit: 10})
      });
      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (error: any) {
      setResult('ERROR: ' + error.message);
    }
  };

  return (
    <div style={{padding: '20px'}}>
      <h1>LangGraph Test</h1>
      <button onClick={testApi}>Test API</button>
      <pre>{result}</pre>
    </div>
  );
}

export default App;
```

#### 実行方法
```bash
npm run dev
# ブラウザで http://localhost:5173
```

### 成功判定
✅ Phase 1と同じ動作（アシスタント情報が表示される）

#### ステップ4.3: スレッド作成を追加
```tsx
const [threadId, setThreadId] = useState<string | null>(null);
const [topic, setTopic] = useState('AI最新情報');

const createThread = async () => {
  const res = await fetch('http://localhost:2024/threads', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({})
  });
  const data = await res.json();
  setThreadId(data.thread_id);
};

// JSX に追加
<input value={topic} onChange={(e) => setTopic(e.target.value)} />
<button onClick={createThread}>Create Thread</button>
{threadId && <div>✅ Thread: {threadId}</div>}
```

#### ステップ4.4: ストリーミングを追加
```tsx
const [progress, setProgress] = useState<string[]>([]);
const [status, setStatus] = useState('');

const runAgent = async () => {
  if (!threadId) return;

  setStatus('⏳ Running...');
  setProgress([]);

  // Phase 3のストリーミングコードをReactに移植
  // setProgress([...progress, newItem]) で更新
};
```

---

## Phase 5: useStream統合（20分）

### 目的
公式の`useStream`フックで自動状態管理

### 技術的な仕組み

#### useStream フック
```tsx
const thread = useStream<State>({
  apiUrl: 'http://localhost:2024',
  assistantId: 'あなたのassistant_id',
  streamMode: ['values', 'updates']
});

// 自動的に以下が管理される:
// - thread.state: 現在の状態
// - thread.isLoading: ローディング状態
// - thread.error: エラー
// - thread.submit(): 実行開始
```

#### State型定義
```tsx
type State = {
  topic: string;
  sources?: {...};
  key_points?: string[];
  toc?: string[];
  slide_md?: string;
  slide_path?: string;
  title?: string;
  error?: string;
};
```

### 実施手順

#### ステップ5.1: SDKインストール
```bash
npm install @langchain/langgraph-sdk
```

#### ステップ5.2: useStreamに置き換え
**ファイル**: `frontend/src/App.tsx`

```tsx
import { useStream } from '@langchain/langgraph-sdk/react';

type State = {
  topic: string;
  slide_path?: string;
  slide_md?: string;
  title?: string;
  error?: string;
};

function App() {
  const thread = useStream<State>({
    apiUrl: 'http://localhost:2024',
    assistantId: 'd67b2a76-c1e8-53af-a4d3-ce8399c3c72a',  // 実際のIDに置き換え
    streamMode: ['values', 'updates']
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const topic = formData.get('topic') as string;
    thread.submit({topic});  // これだけで実行開始
  };

  return (
    <div style={{padding: '20px'}}>
      <form onSubmit={handleSubmit}>
        <input name="topic" placeholder="トピック入力" defaultValue="AI最新情報" />
        <button type="submit">実行</button>
      </form>

      {thread.isLoading && <div>⏳ 処理中...</div>}
      {thread.error && <div>❌ {thread.error.message}</div>}

      {thread.state && (
        <div>
          <h3>現在の状態:</h3>
          <pre>{JSON.stringify(thread.state, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default App;
```

### 成功判定
✅ フォーム送信 → `thread.state`が自動更新される
✅ 各ノード実行ごとに状態が更新される

### デバッグポイント
- `console.log(thread)` で内部状態を確認
- `thread.state` の変化を監視
- エラー時は `thread.error` を確認

---

## Phase 6: UI改善（30分）

### 目的
実用的なUIに仕上げる

### 実施手順

#### 6.1: ノード別の進捗表示
```tsx
const nodeNames: Record<string, string> = {
  collect_info: '🔍 情報収集中...',
  generate_key_points: '📝 キーポイント抽出中...',
  generate_toc: '📋 目次生成中...',
  write_slides: '✍️ スライド生成中...',
  evaluate_slides: '⭐ 評価中...',
  save_and_render: '💾 保存中...'
};

// 進捗表示
{thread.state?.log?.map((log, i) => (
  <div key={i}>{log}</div>
))}
```

#### 6.2: Markdownプレビュー
```bash
npm install react-markdown
```

```tsx
import ReactMarkdown from 'react-markdown';

{thread.state?.slide_md && (
  <div style={{
    border: '1px solid #ccc',
    padding: '20px',
    marginTop: '20px'
  }}>
    <h3>スライドプレビュー:</h3>
    <ReactMarkdown>{thread.state.slide_md}</ReactMarkdown>
  </div>
)}
```

#### 6.3: ダウンロードリンク
```tsx
{thread.state?.slide_path && (
  <a
    href={`http://localhost:2024/files/${thread.state.slide_path}`}
    download
    style={{
      display: 'inline-block',
      padding: '10px 20px',
      background: '#007bff',
      color: 'white',
      textDecoration: 'none',
      borderRadius: '5px'
    }}
  >
    📥 スライドをダウンロード
  </a>
)}
```

---

## よくあるエラーと対処法

### 1. CORSエラー
```
Access to fetch has been blocked by CORS policy
```

**原因**: LangGraphサーバーがフロントエンドのオリジンを許可していない

#### 解決策A: プロキシ設定
**ファイル**: `frontend/vite.config.ts`

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
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

フェッチ時:
```tsx
fetch('/api/assistants/search', ...)  // プロキシ経由
```

#### 解決策B: LangGraphのCORS設定
```bash
langgraph dev --cors-allow-origins "http://localhost:5173"
```

### 2. ストリーミングが来ない

**確認手順**:
1. Network タブ → `runs/stream` のResponse確認
2. Response が空 → バックエンドエラー（サーバーログ確認）
3. Response がある → パース処理の問題

**デバッグコード**:
```tsx
const chunk = decoder.decode(value);
console.log('RAW CHUNK:', chunk);  // 生データ確認
```

### 3. useStreamが動かない

**チェックリスト**:
- [ ] `assistantId`が正しいか（Phase 0でメモしたID）
- [ ] `apiUrl`が正しいか（`http://localhost:2024`）
- [ ] `thread.error`を確認
- [ ] Phase 4のFetch実装に戻って動作確認

---

## 実装スケジュール

| Phase | 所要時間 | 累計 | 成功判定 |
|-------|---------|------|---------|
| 0 | 5分 | 5分 | curlで全エンドポイント応答 |
| 1 | 10分 | 15分 | ブラウザでアシスタント情報表示 |
| 2 | 10分 | 25分 | Thread ID取得＆表示 |
| 3 | 20分 | 45分 | コンソールにストリームデータ表示 |
| 4 | 30分 | 1時間15分 | React版で同じ動作確認 |
| 5 | 20分 | 1時間35分 | useStreamで自動状態管理 |
| 6 | 30分 | **2時間5分** | 実用的なUIが完成 |

**推奨**: 1日目にPhase 0-3、2日目にPhase 4-6

---

## 最終的な成果物

### ファイル構成
```
slide-pilot/
├── marp_agent.py              # バックエンド（既存）
├── langgraph.json             # 設定（既存）
├── requirements.txt           # 依存関係（既存）
├── .env                       # 環境変数（既存）
└── frontend/                  # 新規
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx            # メインコンポーネント
        └── vite-env.d.ts
```

### 機能一覧
- ✅ トピック入力
- ✅ リアルタイム進捗表示
- ✅ スライドプレビュー（Markdown）
- ✅ ファイルダウンロード
- ✅ エラーハンドリング
- ✅ ローディング状態表示

---

## 開発環境の起動手順

### バックエンド
```bash
cd /Users/miyata_ryo/projects/slide-pilot
source venv/bin/activate
langgraph dev
```

### フロントエンド
```bash
cd /Users/miyata_ryo/projects/slide-pilot/frontend
npm run dev
```

### 確認
- バックエンド: http://localhost:2024
- フロントエンド: http://localhost:5173
- API Docs: http://localhost:2024/docs
- Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

---

## 参考リソース

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph React Integration](https://docs.langchain.com/langgraph-platform/use-stream-react)
- [LangGraph API Reference](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html)
- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)

---

## トラブルシューティング

### サーバーが起動しない
```bash
# ポート確認
lsof -i:2024

# 強制終了
lsof -ti:2024 | xargs kill -9

# 再起動
langgraph dev
```

### OpenAI APIエラー
1. https://platform.openai.com/settings/organization/billing で残高確認
2. 残高不足の場合、クレジット追加
3. 新しいAPIキーを作成
4. `.env`の`OPENAI_API_KEY`を更新
5. サーバー再起動

### npm installエラー
```bash
# Node.jsバージョン確認
node --version  # v18以上推奨

# キャッシュクリア
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

---

## まとめ

このガイドに従うことで、LangGraph APIとReactフロントエンドを段階的に統合できます。
各フェーズで動作確認を行うため、エラー発生時の原因特定が容易です。

質問や問題が発生した場合は、該当するPhaseのデバッグポイントを確認してください。
