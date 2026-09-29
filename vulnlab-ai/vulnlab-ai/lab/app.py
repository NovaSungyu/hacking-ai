"""로컬 취약점 실습 서버 (의도적으로 취약). 반드시 127.0.0.1 에만 바인딩해서 사용할 것.
같은 기능의 vuln / safe 쌍으로 구성해 '정상 vs 취약' 데이터를 만든다."""
import html
import os
import sqlite3
import traceback

from flask import Flask, Response, jsonify, request

app = Flask(__name__)

_db = sqlite3.connect(":memory:", check_same_thread=False)
_db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
_db.executemany("INSERT INTO users VALUES (?, ?)", [(1, "alice"), (2, "bob"), (3, "carol")])
_db.commit()

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


@app.after_request
def apply_security_headers(resp):
    if not request.path.startswith("/headers/vuln"):  # 이 경로만 의도적으로 누락
        for k, v in SECURITY_HEADERS.items():
            resp.headers[k] = v
    return resp


def page(inner: str, status: int = 200) -> Response:
    return Response(f"<html><body>{inner}</body></html>", status=status, mimetype="text/html")


@app.get("/")
def index():
    return page("<h1>Vuln Lab (local only)</h1>")


# --- XSS (reflected) ---------------------------------------------------------
@app.get("/xss/vuln")
def xss_vuln():
    q = request.args.get("q", "")
    return page(f"<h1>Search</h1><p>Results for: {q}</p>")  # 의도적: 인코딩 없음


@app.get("/xss/safe")
def xss_safe():
    q = request.args.get("q", "")
    return page(f"<h1>Search</h1><p>Results for: {html.escape(q)}</p>")


# --- SQL error leak ------------------------------------------------------------
@app.get("/sqli/vuln")
def sqli_vuln():
    uid = request.args.get("id", "1")
    try:  # 의도적: 문자열 결합 쿼리 + DB 오류 그대로 노출
        rows = _db.execute("SELECT id, name FROM users WHERE id = " + uid).fetchall()
    except sqlite3.Error as e:
        return page(f"<p>Database error: {html.escape(str(e))}</p>", 500)
    return page("".join(f"<p>{r[0]}: {html.escape(r[1])}</p>" for r in rows) or "<p>No user found</p>")


@app.get("/sqli/safe")
def sqli_safe():
    uid = request.args.get("id", "1")
    rows = _db.execute("SELECT id, name FROM users WHERE id = ?", (uid,)).fetchall()
    if not rows:
        return page("<p>No user found</p>", 404)
    return page("".join(f"<p>{r[0]}: {html.escape(r[1])}</p>" for r in rows))


# --- Info disclosure (stack trace) ---------------------------------------------
@app.get("/debug/vuln")
def debug_vuln():
    try:
        n = int(request.args.get("n", "1"))
        return page(f"<p>Result: {100 // max(n, 1)}</p>")
    except Exception:  # 의도적: 스택 트레이스 노출
        return Response(traceback.format_exc(), status=500, mimetype="text/plain")


@app.get("/debug/safe")
def debug_safe():
    try:
        n = int(request.args.get("n", "1"))
        return page(f"<p>Result: {100 // max(n, 1)}</p>")
    except ValueError:
        return page("<p>Invalid request</p>", 400)


# --- Security headers / cookies -------------------------------------------------
@app.get("/headers/vuln")
def headers_vuln():
    resp = page("<h1>Header test</h1>")
    resp.set_cookie("sessionid", "abc123")  # 의도적: 플래그 없음
    return resp


@app.get("/headers/safe")
def headers_safe():
    resp = page("<h1>Header test</h1>")
    resp.set_cookie("sessionid", "abc123", httponly=True, secure=True, samesite="Lax")
    return resp


# --- Normal pages -----------------------------------------------------------------
@app.get("/normal/about")
def about():
    return page("<h1>About</h1><p>This is a normal page.</p>")


@app.get("/normal/api/status")
def status():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host=os.environ.get("LAB_HOST", "127.0.0.1"), port=int(os.environ.get("LAB_PORT", "8080")))
