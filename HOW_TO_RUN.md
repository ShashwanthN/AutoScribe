# Running the Content Production App

This is the end-to-end app (Ideation → Structure → Drafting → Final Content) built on top of
the existing voice-cloning pipeline. It has two parts: a FastAPI backend (`server/`) and a
React frontend (`web/`). The voice pipeline itself (`main.py`, `pipeline/`, `agents/`, `llm/`)
is untouched — the app only reads its output files from `outputs/`.

## Prerequisites

- Python 3.10+ with the project's existing `.env` configured (same env vars used by the voice
  CLI: `LLM_PROVIDER`, `OPENAI_BASE_URL`/`OPENCODE_*`, `MODEL_NAME`, `MAX_TOKENS`, etc.)
- Node.js 18+ and npm

## 1. Install dependencies

```bash
# Python deps (adds fastapi, uvicorn, anyio to the existing requirements)
pip install -r requirements.txt

# Frontend deps
cd web
npm install
cd ..
```

## 2. Start the backend

From the project root:

```bash
python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000
```

Check it's up:

```bash
curl http://127.0.0.1:8000/api/health
# {"status":"ok"}
```

## 3. Start the frontend

In a separate terminal:

```bash
cd web
npm run dev
```

This starts Vite on `http://127.0.0.1:5173` and proxies `/api/*` requests to the backend on
port 8000 (see `web/vite.config.ts`). Open that URL in a browser.

## 4. Using the app

1. **Create a project** in the left sidebar — give it a title, pick a content type
   (LinkedIn post, blog post, case study, use case, or article), and optionally pick a voice
   profile (auto-scanned from `outputs/run_two_stage_*/*_style_prompt.txt`). You can also
   assign a voice later from the project header.
2. **Ideation** — chat to dump raw context, examples, data, and stakes. The `ideation.md`
   state file regenerates after every exchange and is visible/editable in the state panel on
   the right side of the workspace.
3. Click **Move to next phase** to advance to **Structure** — answer one structural question
   at a time, tailored to the chosen content type.
4. Advance to **Drafting** — click **Generate** to produce an exhaustive WHAT-only draft from
   the ideation + structure files. You can edit the draft directly before moving on.
5. Advance to **Final** — click **Generate** to render the draft through the selected voice
   prompt into finished prose.
6. The **Activity** panel (right column) shows every LLM call and file change live as it
   happens, for full transparency into what the system is doing.

All project state lives under `projects/<project_id>/` as flat files (gitignored) — nothing
is stored in a database.

## Notes

- If no voice profiles show up in the dropdown, run the existing voice pipeline first
  (`python main.py --article ... --topic ...`) to produce a `outputs/run_two_stage_*/` folder
  with a `final_style_prompt.txt` or `iter_NN_style_prompt.txt`.
- The backend and frontend are independent processes — restarting one doesn't affect the
  other's state.
- To stop, `Ctrl+C` both terminals.
