"""slide_workflow のルーティング関数（評価ループ／保存後分岐）の単体テスト。

目的: 上流ノードのエラーを握りつぶさない修正に伴い、評価ループが
エラー時に無限リトライへ陥らず、保存パスを経て END へ抜けることを固定する。
（generate_toc / write_slides_slidev の `"error": ""` 上書き削除 + route 早期分岐）
"""
from langgraph.graph import END

from app.agents.slide_workflow import (
    route_after_eval_slidev,
    route_after_save,
    MAX_ATTEMPTS,
)


# --- route_after_eval_slidev ---

def test_route_after_eval_halts_on_error():
    """上流エラー保持時はリトライせず保存パス("ok")へ。無限リトライ防止の要。"""
    state = {"error": "collect_info_error: boom", "passed": False, "attempts": 0}
    assert route_after_eval_slidev(state) == "ok"


def test_route_after_eval_passed_goes_ok():
    assert route_after_eval_slidev({"passed": True, "attempts": 0}) == "ok"


def test_route_after_eval_not_passed_retries():
    assert route_after_eval_slidev({"passed": False, "attempts": 0}) == "retry"


def test_route_after_eval_max_attempts_stops_retrying():
    state = {"passed": False, "attempts": MAX_ATTEMPTS}
    assert route_after_eval_slidev(state) == "ok"


# --- route_after_save ---

def test_route_after_save_ends_on_error():
    assert route_after_save({"error": "boom"}) == END


def test_route_after_save_proceeds_to_narration():
    assert route_after_save({}) == "generate_narration"
