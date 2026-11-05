"""
MR Film – local server (agent version).
The guide is a small agent. Muse Spark can call two tools to look things up,
then a second check stops any answer that reveals story beyond the current scene.
The API key is read from the environment, never sent to the browser.

Run:
  python -u server.py        (set $env:META_API_KEY first, in the same window)
Then open http://localhost:8000
"""
import base64
import json
import mimetypes
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from openai import OpenAI

PORT = int(os.environ.get("PORT", "8000"))
MODEL = os.environ.get("MUSE_MODEL", "muse-spark-1.3")
BASE_URL = os.environ.get("META_BASE_URL", "https://api.meta.ai/v1")
API_KEY = os.environ.get("META_API_KEY") or os.environ.get("MODEL_API_KEY", "")
MAX_CALLS = int(os.environ.get("MAX_GUIDE_CALLS", "200"))
SEND_FRAME = os.environ.get("SEND_FRAME", "0") == "1"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
calls_made = 0

client = OpenAI(api_key=API_KEY, base_url=BASE_URL) if API_KEY else None

SYSTEM = (
    "You are the in-story guide for the interactive AI film 'The Chini Saga'. "
    "The viewer is standing inside a scene and asking about what they see. "
    "Answer in character as a calm, knowledgeable guide, in 2 to 4 sentences. "
    "Use the tools to look up objects and the current scene's notes before answering. "
    "Use only what the tools and the scene data give you. If the answer is not there, say so "
    "and suggest a nearby object the viewer can ask about. Never invent plot facts. "
    "Describe obstacles as the viewer meets them; do not reveal what happens after them."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "lookup_hotspot",
        "description": "Find an object or obstacle in the film by name or keyword and return its description.",
        "parameters": {"type": "object",
                       "properties": {"name": {"type": "string", "description": "object or keyword to look up"}},
                       "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "get_scene_notes",
        "description": "Return the title, story notes and objects of the scene the viewer is in now.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
]


def frame_part(scene):
    """Return the scene's still frame as an image input, or None."""
    rel = (scene or {}).get("still")
    if not (SEND_FRAME and rel):
        return None
    path = os.path.normpath(os.path.join(BASE_DIR, rel))
    if not path.startswith(BASE_DIR) or not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}


def run_tool(name, args, ctx):
    """Run one tool locally and return its result as data."""
    scenes, current = ctx["scenes"], ctx["current"]
    if name == "lookup_hotspot":
        q = (args.get("name") or "").lower().strip()
        hits = []
        for sid, s in scenes.items():
            for h in s.get("hotspots", []):
                words = [h.get("label", "").lower()] + [k.lower() for k in h.get("keywords", [])]
                if q and any(q == w or q in w for w in words if w):
                    hits.append({"object": h.get("label"), "description": h.get("info"), "scene": s.get("title")})
        return hits[:3] or {"result": "no object matches that name in this film"}
    if name == "get_scene_notes":
        s = scenes.get(current, {})
        return {"title": s.get("title"), "story": s.get("story"),
                "objects": [h.get("label") for h in s.get("hotspots", [])]}
    return {"error": f"unknown tool {name}"}


def ask_agent(question, scene, film, ctx):
    """Let Muse Spark use the tools, then return its answer text."""
    scene_text = json.dumps(scene, ensure_ascii=False)
    text = f"Film: {film}\nCurrent scene id: {ctx['current']}\nScene data: {scene_text}\n\nViewer asks: {question}"
    image = frame_part(scene)
    content = [{"type": "text", "text": text}, image] if image else text
    system = SYSTEM
    if ctx.get("strict"):
        system += (" STRICT MODE: your previous answer revealed too much. Answer using ONLY the current scene's "
                   "story notes. Do not mention anything that happens after the obstacles, or any other scene.")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": content}]

    for _ in range(4):  # at most a few rounds of tool use
        resp = client.chat.completions.create(model=MODEL, max_tokens=4000, messages=messages, tools=TOOLS)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            text = (msg.content or "").strip()
            if not text:
                raise RuntimeError(f"empty reply from Meta (finish_reason={resp.choices[0].finish_reason})")
            return text
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [{"id": tc.id, "type": "function",
                                         "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                                        for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = run_tool(tc.function.name, args, ctx)
            print(f"[agent] tool {tc.function.name} {args}", flush=True)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result, ensure_ascii=False)})
    raise RuntimeError("agent did not finish within its tool rounds")


def reveals_too_much(answer, scene):
    """Second check: does the answer reveal story beyond the current scene? Returns True to block."""
    allowed = (scene or {}).get("story") or "(no story notes for this scene)"
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=1000,
        messages=[
            {"role": "system", "content": "You check answers for spoilers. Reply with only YES or NO."},
            {"role": "user", "content": (f"The viewer may know only this story:\n{allowed}\n\n"
                                          f"Answer to check:\n{answer}\n\n"
                                          "Does the answer reveal anything beyond that story, such as what happens after "
                                          "an obstacle or details from other scenes? Reply YES or NO.")}],
    )
    verdict = (resp.choices[0].message.content or "").strip().upper()
    print(f"[check] verdict: {verdict[:20] or '(empty)'}", flush=True)
    return verdict.startswith("YES")


def answer_question(question, scene, film, ctx):
    answer = ask_agent(question, scene, film, ctx)
    if answer and reveals_too_much(answer, scene):
        # One safe retry: answer again, strictly from the current scene notes only.
        ctx["strict"] = True
        answer = ask_agent(question, scene, film, ctx)
        if reveals_too_much(answer, scene):
            answer = ("I can only tell you about what is in front of you now. "
                      + (scene.get("summary") or "Ask about one of the objects in this scene."))
    if not answer:
        raise RuntimeError("empty reply from Meta")
    return answer


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def do_GET(self):
        rng = self.headers.get("Range")
        path = self.translate_path(self.path.split("?", 1)[0])
        m = re.match(r"bytes=(\d*)-(\d*)$", rng or "")
        if not (m and os.path.isfile(path)):
            return super().do_GET()
        size = os.path.getsize(path)
        start_s, end_s = m.groups()
        if start_s == "" and end_s == "":
            return super().do_GET()
        if start_s == "":                       # suffix range: last N bytes
            start, end = max(size - int(end_s), 0), size - 1
        else:
            start = int(start_s)
            end = min(int(end_s), size - 1) if end_s else size - 1
        if start >= size or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return
        self.send_response(206)
        self.send_header("Content-Type", mimetypes.guess_type(path)[0] or "application/octet-stream")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        try:
            with open(path, "rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(65536, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass  # browser closed the connection (normal when seeking/looping)

    def do_POST(self):
        if self.path != "/api/guide":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "bad json"})

        question = (body.get("question") or "").strip()[:500]
        if not question:
            return self._json(400, {"error": "empty question"})
        if client is None:
            return self._json(503, {"error": "no META_API_KEY / MODEL_API_KEY set"})

        global calls_made
        if calls_made >= MAX_CALLS:
            return self._json(429, {"error": "call limit reached for this run"})

        scene = body.get("scene", {})
        ctx = {"scenes": body.get("scenes") or {scene.get("title", "scene"): scene},
               "current": body.get("sceneId") or next(iter(body.get("scenes") or {}), "scene"),
               "strict": False}
        try:
            calls_made += 1
            answer = answer_question(question, scene, body.get("film", ""), ctx)
            print(f"[guide] call {calls_made}/{MAX_CALLS}", flush=True)
            self._json(200, {"answer": answer})
        except Exception as e:
            print(f"[guide] Meta call failed: {type(e).__name__}: {str(e)[:500]}", flush=True)
            self._json(502, {"error": str(e)[:200]})

    def _json(self, status, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"MR Film running on http://localhost:{PORT}  (agent, model: {MODEL}, max guide calls: {MAX_CALLS}, send frame: {SEND_FRAME})")
    if not API_KEY:
        print("No META_API_KEY / MODEL_API_KEY set: the guide will use local answers only.")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
