import { useState, useEffect } from 'react';
import type { CredentialResponse } from '@react-oauth/google';
import { jwtDecode } from 'jwt-decode';
import Login from './components/Login';

// ユーザー情報の型定義
interface UserInfo {
  name: string;
  email: string;
  picture: string;
}

// Phase 6.1: ノード名マッピング
const nodeNames: Record<string, string> = {
  collect_info: '情報収集中...',
  generate_key_points: 'キーポイント抽出中...',
  generate_toc: '目次生成中...',
  write_slides: 'スライド生成中...',
  evaluate_slides: '評価中...',
  save_and_render: '保存中...'
};

function App() {
  // 認証状態
  const [user, setUser] = useState<UserInfo | null>(null);

  // 既存の状態
  const [threadId, setThreadId] = useState<string | null>(null);
  const [topic, setTopic] = useState('AI最新情報');
  const [progress, setProgress] = useState<string[]>([]);
  const [status, setStatus] = useState('');
  const [slideData, setSlideData] = useState<{
    slide_md?: string;
    slide_path?: string;
    title?: string;
  }>({});

  // ログイン成功時の処理
  const handleLoginSuccess = (credentialResponse: CredentialResponse) => {
    if (credentialResponse.credential) {
      const decoded: any = jwtDecode(credentialResponse.credential);
      const userInfo: UserInfo = {
        name: decoded.name,
        email: decoded.email,
        picture: decoded.picture
      };
      setUser(userInfo);
      localStorage.setItem('user', JSON.stringify(userInfo));
    }
  };

  // ログアウト処理
  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  // ページロード時にlocalStorageから復元
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  // ログインしていない場合はログイン画面を表示
  if (!user) {
    return <Login onSuccess={handleLoginSuccess} />;
  }

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
    setSlideData({});

    try {
      const assistantRes = await fetch('http://localhost:2024/assistants/search', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({limit: 1})
      });
      const assistants = await assistantRes.json();
      const assistantId = assistants[0].assistant_id;

      const response = await fetch(`http://localhost:2024/threads/${threadId}/runs/stream`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          assistant_id: assistantId,
          input: {topic: topic},
          stream_mode: ['updates']
        })
      });

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

              // Phase 6.1: 絵文字付き進捗表示
              const keys = Object.keys(json);
              const displayText = keys
                .map(key => nodeNames[key] || `✓ ${key}`)
                .join(', ');

              setProgress(prev => [...prev, displayText]);

              // スライドデータを抽出
              if (json.save_and_render) {
                setSlideData({
                  slide_md: json.save_and_render.slide_md,
                  slide_path: json.save_and_render.slide_path,
                  title: json.save_and_render.title
                });
              }
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
    <div style={{padding: '20px', maxWidth: '900px', margin: '0 auto', fontFamily: 'Arial, sans-serif'}}>
      {/* ユーザーヘッダー */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px',
        padding: '10px',
        background: '#f8f9fa',
        borderRadius: '5px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <img
            src={user.picture}
            alt={user.name}
            style={{ width: '40px', height: '40px', borderRadius: '50%' }}
          />
          <div>
            <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{user.name}</div>
            <div style={{ fontSize: '12px', color: '#666' }}>{user.email}</div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          style={{
            padding: '8px 16px',
            background: '#dc3545',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            fontSize: '14px'
          }}
          onMouseOver={(e) => e.currentTarget.style.background = '#c82333'}
          onMouseOut={(e) => e.currentTarget.style.background = '#dc3545'}
        >
          ログアウト
        </button>
      </div>

      <h1 style={{color: '#333', borderBottom: '3px solid #007bff', paddingBottom: '10px'}}>
        SlidePilot - AI スライド生成
      </h1>

      <div style={{marginTop: '30px'}}>
        <h2 style={{color: '#555'}}>トピック入力</h2>
        <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="トピックを入力"
            style={{
              flex: 1,
              padding: '12px',
              fontSize: '16px',
              border: '2px solid #ddd',
              borderRadius: '5px',
              outline: 'none'
            }}
            onFocus={(e) => e.target.style.borderColor = '#007bff'}
            onBlur={(e) => e.target.style.borderColor = '#ddd'}
          />
          <button
            onClick={createThread}
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              background: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
            onMouseOver={(e) => e.currentTarget.style.background = '#0056b3'}
            onMouseOut={(e) => e.currentTarget.style.background = '#007bff'}
          >
            スレッド作成
          </button>
        </div>
        {threadId && (
          <div style={{marginTop: '10px', padding: '10px', background: '#d4edda', borderRadius: '5px', color: '#155724'}}>
            ✅ Thread created: <code style={{background: '#c3e6cb', padding: '2px 6px', borderRadius: '3px'}}>{threadId}</code>
          </div>
        )}
      </div>

      <div style={{marginTop: '30px'}}>
        <button
          onClick={runAgent}
          disabled={!threadId}
          style={{
            padding: '14px 32px',
            fontSize: '18px',
            background: threadId ? '#28a745' : '#ccc',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: threadId ? 'pointer' : 'not-allowed',
            fontWeight: 'bold',
            width: '100%'
          }}
          onMouseOver={(e) => { if (threadId) e.currentTarget.style.background = '#218838'; }}
          onMouseOut={(e) => { if (threadId) e.currentTarget.style.background = '#28a745'; }}
        >
          スライド生成開始
        </button>
      </div>

      {/* Phase 6.1: 進捗表示 */}
      {progress.length > 0 && (
        <div style={{marginTop: '30px'}}>
          <h3 style={{color: '#555'}}>進捗状況</h3>
          <ul style={{
            listStyle: 'none',
            padding: '15px',
            background: '#f8f9fa',
            borderRadius: '5px',
            border: '1px solid #dee2e6'
          }}>
            {progress.map((item, i) => (
              <li key={i} style={{
                padding: '8px 0',
                fontSize: '15px',
                borderBottom: i < progress.length - 1 ? '1px solid #dee2e6' : 'none'
              }}>
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div style={{marginTop: '20px', fontSize: '18px', fontWeight: 'bold', textAlign: 'center'}}>
        {status}
      </div>

      {/* Phase 6.3: ダウンロードボタン */}
      {slideData.slide_path && (
        <div style={{marginTop: '30px', textAlign: 'center'}}>
          <a
            href={`/${slideData.slide_path}`}
            download
            style={{
              display: 'inline-block',
              padding: '14px 32px',
              background: '#007bff',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '5px',
              fontSize: '16px',
              fontWeight: 'bold'
            }}
            onMouseOver={(e) => e.currentTarget.style.background = '#0056b3'}
            onMouseOut={(e) => e.currentTarget.style.background = '#007bff'}
          >
            スライドをダウンロード
          </a>
          {slideData.title && (
            <p style={{marginTop: '10px', color: '#666'}}>
              タイトル: {slideData.title}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
