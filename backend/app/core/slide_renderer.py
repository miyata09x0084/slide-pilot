"""
SlideRenderer - HTML/CSS + Playwright ベースのスライド画像レンダラー

Slidevの不安定なPNG出力を置き換え、安定した画像生成を実現する。
Cloud Run環境でのLangGraphノードから同期呼び出し可能。
"""

from pathlib import Path
from typing import List, Dict
import html


class SlideRenderer:
    """HTML/CSS + Playwright ベースのスライドレンダラー"""

    VIEWPORT = {'width': 1920, 'height': 1080}

    def __init__(self):
        self.templates = {
            'title': self._title_template,
            'content': self._content_template,
            'conversation': self._conversation_template,
            'summary': self._summary_template,
            'mermaid': self._mermaid_template,
        }

    def render_all(self, slides: List[Dict], output_dir: Path) -> List[Path]:
        """
        全スライドをPNG画像としてレンダリング

        Args:
            slides: スライドデータのリスト
            output_dir: PNG出力先ディレクトリ

        Returns:
            生成されたPNGファイルパスのリスト
        """
        from playwright.sync_api import sync_playwright

        output_dir.mkdir(parents=True, exist_ok=True)
        png_paths = []

        with sync_playwright() as p:
            browser = p.chromium.launch(timeout=60000)  # 60秒（Cloud Run環境対応）
            context = browser.new_context(viewport=self.VIEWPORT)
            context.set_default_timeout(60000)  # ページ操作も60秒
            page = context.new_page()

            for i, slide in enumerate(slides):
                html_content = self._generate_html(slide)
                page.set_content(html_content)
                page.wait_for_load_state('domcontentloaded')

                # mermaidスライドの場合、SVGレンダリング完了を待機
                if slide.get('type') == 'mermaid':
                    try:
                        page.wait_for_function(
                            "() => document.querySelector('.mermaid svg') !== null",
                            timeout=10000
                        )
                        # 少し待ってレンダリングを安定させる
                        page.wait_for_timeout(500)
                    except Exception as e:
                        print(f"[SlideRenderer] WARNING: mermaid rendering timeout: {e}")

                png_path = output_dir / f"{i+1}.png"
                page.screenshot(path=str(png_path))
                png_paths.append(png_path)
                print(f"[SlideRenderer] Generated: {png_path.name}")

            browser.close()

        return png_paths

    def render_single(self, slide: Dict, output_path: Path) -> Path:
        """単一スライドをPNG画像としてレンダリング（デバッグ用）"""
        from playwright.sync_api import sync_playwright

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(timeout=60000)  # 60秒（Cloud Run環境対応）
            context = browser.new_context(viewport=self.VIEWPORT)
            context.set_default_timeout(60000)  # ページ操作も60秒（CDN読み込み対応）
            page = context.new_page()

            html_content = self._generate_html(slide)
            page.set_content(html_content)
            page.wait_for_load_state('networkidle')
            page.screenshot(path=str(output_path))

            browser.close()

        return output_path

    def generate_html(self, slide: Dict) -> str:
        """スライドデータからHTMLを生成（デバッグ用に公開）"""
        return self._generate_html(slide)

    def _generate_html(self, slide: Dict) -> str:
        """スライドデータからHTMLを生成"""
        slide_type = slide.get('type', 'content')
        template_fn = self.templates.get(slide_type, self._content_template)
        return template_fn(slide)

    def _base_style(self) -> str:
        """共通CSSスタイル（CDN依存なし - ローカルフォント使用）"""
        return '''
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            width: 1920px;
            height: 1080px;
            font-family: 'Noto Sans CJK JP', 'Noto Sans JP', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .slide {
            padding: 80px;
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        h1 { font-size: 64px; margin-bottom: 40px; font-weight: 700; }
        h2 { font-size: 48px; margin-bottom: 30px; font-weight: 700; }
        ul { font-size: 36px; line-height: 2; list-style: none; }
        li { margin-bottom: 10px; }
        li::before { content: "- "; color: rgba(255,255,255,0.7); }
        strong, b { font-weight: 700; }
        '''

    def _title_template(self, slide: Dict) -> str:
        """タイトルスライドテンプレート"""
        title = html.escape(slide.get('title', ''))
        subtitle = html.escape(slide.get('subtitle', ''))

        return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>{self._base_style()}
.slide {{ justify-content: center; align-items: center; text-align: center; }}
h1 {{ font-size: 80px; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
.subtitle {{ font-size: 36px; opacity: 0.9; }}
</style></head>
<body><div class="slide">
    <h1>{title}</h1>
    <div class="subtitle">{subtitle}</div>
</div></body></html>'''

    def _content_template(self, slide: Dict) -> str:
        """コンテンツスライドテンプレート（見出し + 箇条書き）"""
        heading = html.escape(slide.get('heading', ''))
        bullets = slide.get('bullets', [])
        bullets_html = ''.join(f'<li>{html.escape(str(b))}</li>' for b in bullets)

        return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>{self._base_style()}
.header {{ margin-bottom: 40px; }}
h2 {{ border-bottom: 3px solid rgba(255,255,255,0.3); padding-bottom: 20px; }}
ul {{ flex: 1; display: flex; flex-direction: column; justify-content: flex-start; padding-top: 20px; }}
li {{ font-size: 38px; margin-bottom: 25px; }}
</style></head>
<body><div class="slide">
    <div class="header">
        <h2>{heading}</h2>
    </div>
    <ul>{bullets_html}</ul>
</div></body></html>'''

    def _conversation_template(self, slide: Dict) -> str:
        """会話形式スライドテンプレート（先生/生徒）"""
        heading = html.escape(slide.get('heading', '会話'))
        teacher = html.escape(slide.get('teacher', ''))
        student = html.escape(slide.get('student', ''))

        return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>{self._base_style()}
h2 {{ margin-bottom: 30px; }}
.conversation {{ display: flex; flex-direction: column; gap: 30px; flex: 1; justify-content: center; }}
.message {{ padding: 30px 40px; border-radius: 20px; max-width: 85%; }}
.teacher {{ background: rgba(255,255,255,0.2); align-self: flex-start; }}
.student {{ background: rgba(0,0,0,0.2); align-self: flex-end; }}
.role {{ font-weight: bold; margin-bottom: 15px; font-size: 28px; display: flex; align-items: center; gap: 10px; }}
.text {{ font-size: 34px; line-height: 1.6; }}
</style></head>
<body><div class="slide">
    <h2>{heading}</h2>
    <div class="conversation">
        <div class="message teacher">
            <div class="role">先生</div>
            <div class="text">{teacher}</div>
        </div>
        <div class="message student">
            <div class="role">生徒</div>
            <div class="text">{student}</div>
        </div>
    </div>
</div></body></html>'''

    def _summary_template(self, slide: Dict) -> str:
        """まとめスライドテンプレート"""
        heading = html.escape(slide.get('heading', 'まとめ'))
        points = slide.get('points', [])
        points_html = ''.join(
            f'<li><span class="num">{i+1}</span>{html.escape(str(p))}</li>'
            for i, p in enumerate(points)
        )

        return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>{self._base_style()}
h2 {{ text-align: center; margin-bottom: 50px; }}
ul {{ display: flex; flex-direction: column; gap: 25px; max-width: 1400px; margin: 0 auto; }}
li {{ display: flex; align-items: flex-start; gap: 20px; font-size: 36px; }}
li::before {{ content: none; }}
.num {{
    background: rgba(255,255,255,0.3);
    width: 50px; height: 50px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: bold; font-size: 28px;
    flex-shrink: 0;
}}
</style></head>
<body><div class="slide">
    <h2>{heading}</h2>
    <ul>{points_html}</ul>
</div></body></html>'''

    def _mermaid_template(self, slide: Dict) -> str:
        """Mermaid図スライドテンプレート（インラインJS埋め込み - set_content対応）"""
        heading = html.escape(slide.get('heading', '図解'))
        mermaid_code = slide.get('mermaid_code', '')

        # ローカルのmermaid.jsファイルを読み込んでインライン埋め込み
        # Playwrightのset_content()ではfile://プロトコルが使えないため
        static_dir = Path(__file__).parent.parent / 'static'
        mermaid_js_path = static_dir / 'mermaid.min.js'
        mermaid_js_content = mermaid_js_path.read_text(encoding='utf-8') if mermaid_js_path.exists() else ''

        return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<script>{mermaid_js_content}</script>
<style>{self._base_style()}
.slide {{ justify-content: flex-start; padding: 60px; }}
h2 {{ text-align: center; margin-bottom: 20px; font-size: 52px; }}
.mermaid-container {{
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    height: 100%;
}}
.mermaid {{
    background: rgba(255,255,255,0.95);
    border-radius: 24px;
    padding: 50px 60px;
    width: 100%;
    max-width: 1760px;
    min-height: 750px;
    display: flex;
    justify-content: center;
    align-items: center;
}}
.mermaid svg {{
    width: 100% !important;
    height: auto !important;
    min-width: 1200px;
    max-height: 850px;
}}
</style>
</head>
<body>
<div class="slide">
    <h2>{heading}</h2>
    <div class="mermaid-container">
        <pre class="mermaid">
{mermaid_code}
        </pre>
    </div>
</div>
<script>
    mermaid.initialize({{
        startOnLoad: true,
        theme: 'default',
        securityLevel: 'loose',
        flowchart: {{ curve: 'basis' }}
    }});
</script>
</body></html>'''
