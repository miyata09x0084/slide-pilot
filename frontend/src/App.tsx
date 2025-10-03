import { useState } from 'react';

function App() {
  const [result, setResult] = useState('');
  const [threadId, setThreadId] = useState<string | null>(null);
  const [topic, setTopic] = useState('AI最新情報');
  const [progress, setProgress] = useState<string[]>([]);
  const [status, setStatus] = useState('');

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

  const createThread = async () => {
    try {
      const res = await fetch('http://localhost:2024/threads', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({})
      });
      const data = await res.json();
      setThreadId(data.thread_id);
    } catch (error: any) {
      alert('ERROR: ' + error.message);
    }
  };

  const runAgent = async () => {
    if (!threadId) {
      alert('まずスレッドを作成してください');
      return;
    }

    setProgress([]);
    setStatus('⏳ Running...');

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
          stream_mode: ['updates']
        })
      });

      // 3. ストリームを読む
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const {done, value} = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const json = JSON.parse(line.slice(6));
              const nodeNames = Object.keys(json);
              setProgress(prev => [...prev, `✓ ${nodeNames.join(', ')}`]);
            } catch (e) {
              console.warn('Parse error:', e);
            }
          }
        }
      }

      setStatus('✅ Complete!');
    } catch (error: any) {
      setStatus('❌ ERROR: ' + error.message);
      console.error(error);
    }
  };

  return (
    <div style={{padding: '20px'}}>
      <h1>LangGraph API Test</h1>
      <button onClick={testApi}>アシスタント情報を取得</button>
      <pre>{result}</pre>

      <hr />
      <h2>Step 2: スレッド作成</h2>
      <input
        type="text"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="トピックを入力"
      />
      <button onClick={createThread}>スレッド作成</button>
      {threadId && <div>✅ Thread created: <code>{threadId}</code></div>}

      <hr />
      <h2>Step 3: エージェント実行（ストリーミング）</h2>
      <button onClick={runAgent}>実行</button>
      <ul>
        {progress.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
      <div>{status}</div>
    </div>
  );
}

export default App;
