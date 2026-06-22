"""
Serves the UI on http://localhost:3000 and proxies ADK routes to port 8000.
"""
import sys, json, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, FileResponse, StreamingResponse, JSONResponse
from starlette.routing import Route

ADK        = "http://localhost:8000"
UI_DIR     = Path(__file__).parent
IMAGES_DIR = UI_DIR.parent.parent / "FrontEndDesignFiles"

PROXY_PREFIXES = ("/apps/", "/run", "/list-apps", "/debug")

CORS_HEADERS = {
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Max-Age": "86400",
}


async def handle(request: Request) -> Response:
    path      = request.path_params.get("path", "")
    full_path = "/" + path

    # Always answer OPTIONS immediately
    if request.method == "OPTIONS":
        return Response(status_code=200, headers=CORS_HEADERS)

    # Product images
    if full_path.startswith("/images/"):
        img_path = IMAGES_DIR / path[len("images/"):]
        if img_path.is_file():
            return FileResponse(img_path)
        return Response("Image not found", status_code=404)

    # Proxy to ADK
    if any(full_path.startswith(p) for p in PROXY_PREFIXES):
        url = f"{ADK}/{path}"
        if request.query_params:
            url += "?" + str(request.query_params)

        body    = await request.body()
        headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in ("host", "content-length",
                                        "origin", "referer")}

        is_sse = "text/event-stream" in request.headers.get("accept", "")

        if is_sse:
            async def stream_gen():
                async with httpx.AsyncClient(timeout=120) as client:
                    async with client.stream(request.method, url,
                                             headers=headers, content=body) as r:
                        async for chunk in r.aiter_bytes():
                            yield chunk
            return StreamingResponse(
                stream_gen(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.request(request.method, url,
                                     headers=headers, content=body)
        resp_headers = {**dict(r.headers), **CORS_HEADERS}
        return StreamingResponse(
            iter([r.content]),
            status_code=r.status_code,
            headers=resp_headers,
        )

    # RAG API
    if full_path.startswith("/api/rag"):
        return await rag_api(request, path)

    # DB explorer API
    if full_path.startswith("/api/db"):
        return await db_api(request, path)

    # Static UI files
    target = UI_DIR / path
    if path and target.is_file():
        return FileResponse(target)
    return FileResponse(UI_DIR / "index.html")


async def db_api(request: Request, path: str) -> Response:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    db_path = os.getenv("DB_PATH", "ecombot.db")

    # resolve relative to project root (one level up from ui/)
    db_file = Path(__file__).parent.parent / db_path
    if not db_file.exists():
        return JSONResponse({"error": f"Database not found at {db_file}"}, status_code=404)

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row

    sub = path[len("api/db"):].strip("/")

    if sub == "tables":
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return JSONResponse({"tables": [r["name"] for r in rows]})

    if sub.startswith("table/"):
        table = sub[len("table/"):]
        # only allow alphanumeric table names to prevent injection
        if not table.replace("_","").isalnum():
            return JSONResponse({"error": "Invalid table name"}, status_code=400)
        q      = request.query_params.get("q", "").strip()
        limit  = min(int(request.query_params.get("limit", 100)), 500)
        offset = int(request.query_params.get("offset", 0))

        try:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            if q:
                like_clauses = " OR ".join(f"CAST({c} AS TEXT) LIKE ?" for c in cols)
                params = [f"%{q}%"] * len(cols)
                rows = conn.execute(
                    f"SELECT * FROM {table} WHERE {like_clauses} LIMIT ? OFFSET ?",
                    params + [limit, offset]
                ).fetchall()
                total = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {like_clauses}", params
                ).fetchone()[0]
            else:
                rows  = conn.execute(f"SELECT * FROM {table} LIMIT ? OFFSET ?", (limit, offset)).fetchall()
                total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

            return JSONResponse({
                "table": table, "columns": cols, "total": total,
                "rows": [dict(r) for r in rows], "offset": offset, "limit": limit
            })
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    if sub == "stats":
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        stats = {}
        for t in tables:
            stats[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        return JSONResponse({"stats": stats})

    return JSONResponse({"error": "Unknown endpoint"}, status_code=404)


async def rag_api(request: Request, path: str) -> Response:
    import time
    sub = path[len("api/rag"):].strip("/")

    if sub == "status":
        try:
            from pathlib import Path as _Path
            import chromadb
            chroma_dir = _Path(__file__).parent.parent / "chroma_db"
            if not chroma_dir.exists():
                return JSONResponse({"ready": False})
            client     = chromadb.PersistentClient(path=str(chroma_dir))
            collection = client.get_collection("ecombot_kb")
            return JSONResponse({"ready": True, "count": collection.count()})
        except Exception as e:
            return JSONResponse({"ready": False, "error": str(e)})

    if sub == "search":
        q      = request.query_params.get("q", "").strip()
        n      = int(request.query_params.get("n", 3))
        filter_ = request.query_params.get("filter", "all")
        if not q:
            return JSONResponse({"error": "Missing query param 'q'"}, status_code=400)
        try:
            from src.rag.retriever import retrieve
            t0      = time.time()
            results = retrieve(q, n_results=max(n * 3, 10))
            elapsed = round((time.time() - t0) * 1000)
            if filter_ != "all":
                results = [r for r in results if r.get("metadata", {}).get("type") == filter_]
            return JSONResponse({"results": results[:n], "elapsed_ms": elapsed})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    if sub == "ingest":
        import tempfile, shutil
        from starlette.datastructures import UploadFile as StarletteUpload
        form   = await request.form()
        upload = form.get("file")
        if not upload:
            return JSONResponse({"error": "No file provided"}, status_code=400)
        if not upload.filename.lower().endswith(".pdf"):
            return JSONResponse({"error": "Only PDF files are supported"}, status_code=400)

        # Save to data/ folder
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        dest = data_dir / upload.filename
        with open(dest, "wb") as f:
            shutil.copyfileobj(upload.file, f)

        # Run ingestor
        try:
            from src.rag.pdf_ingestor import ingest
            ingest(dest)
            # Count chunks added
            import chromadb
            chroma_dir = Path(__file__).parent.parent / "chroma_db"
            client     = chromadb.PersistentClient(path=str(chroma_dir))
            collection = client.get_collection("ecombot_kb")
            return JSONResponse({"filename": upload.filename, "chunks": collection.count()})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    if sub == "catalog":
        try:
            from pathlib import Path as _Path
            import chromadb
            chroma_dir = _Path(__file__).parent.parent / "chroma_db"
            if not chroma_dir.exists():
                return JSONResponse([])
            client     = chromadb.PersistentClient(path=str(chroma_dir))
            collection = client.get_collection("ecombot_kb")
            data       = collection.get(include=["documents", "metadatas"])
            items = []
            for id_, doc, meta in zip(data["ids"], data["documents"], data["metadatas"]):
                items.append({"id": id_, "text": doc,
                              "type": meta.get("type", "?"),
                              "source": meta.get("source", "?")})
            return JSONResponse(items)
        except Exception as e:
            return JSONResponse([])

    return JSONResponse({"error": "Unknown endpoint"}, status_code=404)


# Register every method explicitly including OPTIONS
METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]

app = Starlette(routes=[
    Route("/",            handle, methods=METHODS),
    Route("/{path:path}", handle, methods=METHODS),
])


if __name__ == "__main__":
    import uvicorn
    print("UI  →  http://localhost:3000")
    print("ADK →  http://localhost:8000  (must be running separately)")
    uvicorn.run(app, host="127.0.0.1", port=3000, log_level="info")
