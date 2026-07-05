import { useState } from "react";
import { ChevronDown, ChevronRight, Pencil, Plus, Trash2 } from "lucide-react";
import { useAddArticle, useArticles, useDeleteArticle, useUpdateArticle } from "../hooks/useApi";
import type { Article } from "../types";
import { Card, CardHeading } from "./ui/Card";
import { Button } from "./ui/Button";
import { IconButton } from "./ui/IconButton";

/** The corpus: source writing samples an active voice was trained on. */
export function ArticlesFolder({ personId }: { personId: string }) {
  const articles = useArticles(personId);
  const addArticle = useAddArticle(personId);
  const [composerOpen, setComposerOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleAdd = async () => {
    if (!title.trim() || !text.trim()) {
      setError("Title and article text are both required");
      return;
    }
    setError(null);
    await addArticle.mutateAsync({ title: title.trim(), text });
    setTitle("");
    setText("");
    setComposerOpen(false);
  };

  const count = (articles.data ?? []).length;

  return (
    <Card className="flex flex-col">
      <CardHeading
        title="Corpus"
        description={`${count} source ${count === 1 ? "sample" : "samples"} used to train this voice`}
        action={
          <Button size="sm" variant="secondary" onClick={() => setComposerOpen((v) => !v)}>
            <Plus size={14} />
            Add source
          </Button>
        }
      />

      {composerOpen ? (
        <div className="grid gap-2 border-b border-border-soft p-3">
          <input
            className="w-full rounded-control border border-border bg-surface px-2.5 py-2 text-[13px] text-text-strong outline-none"
            placeholder="Title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            autoFocus
          />
          <textarea
            className="min-h-[100px] w-full resize-y rounded-control border border-border bg-surface px-2.5 py-2 text-[13px] text-text-strong outline-none"
            placeholder="Paste the writing sample here"
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          {error ? (
            <div className="rounded-control border border-danger/30 bg-danger-soft px-2.5 py-2 text-[12px] text-danger">
              {error}
            </div>
          ) : null}
          <div className="flex gap-2">
            <Button size="sm" onClick={handleAdd} loading={addArticle.isPending}>
              Add to corpus
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setComposerOpen(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : null}

      <div className="grid gap-2 p-3">
        {articles.isLoading ? (
          <div className="text-sm text-text-muted">Loading...</div>
        ) : count === 0 ? (
          <div className="rounded-control border border-dashed border-border px-3 py-6 text-center text-sm text-text-muted">
            No source samples yet. Add at least one to generate a voice.
          </div>
        ) : (
          (articles.data ?? []).map((article) => (
            <ArticleRow key={article.id} personId={personId} article={article} />
          ))
        )}
      </div>
    </Card>
  );
}

function ArticleRow({ personId, article }: { personId: string; article: Article }) {
  const updateArticle = useUpdateArticle(personId);
  const deleteArticle = useDeleteArticle(personId);
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(article.title);
  const [text, setText] = useState(article.text);

  const save = async () => {
    await updateArticle.mutateAsync({ articleId: article.id, title, text });
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="grid gap-2 rounded-control border border-border p-2.5">
        <input
          className="w-full rounded-control border border-border bg-surface px-2.5 py-2 text-[13px] text-text-strong outline-none"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <textarea
          className="min-h-[100px] w-full resize-y rounded-control border border-border bg-surface px-2.5 py-2 text-[13px] text-text-strong outline-none"
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <div className="flex gap-2">
          <Button size="sm" onClick={save} loading={updateArticle.isPending}>
            Save
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setEditing(false)}>
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-control border border-border-soft">
      <div className="flex items-center gap-1.5 px-2.5 py-2">
        <IconButton onClick={() => setExpanded((v) => !v)} title="Toggle preview">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </IconButton>
        <span className="flex-1 truncate text-[13px] font-semibold text-text-strong">{article.title}</span>
        <span className="flex flex-shrink-0 gap-1">
          <IconButton title="Edit" onClick={() => setEditing(true)}>
            <Pencil size={14} />
          </IconButton>
          <IconButton
            tone="danger"
            title="Delete"
            onClick={() => {
              if (confirm(`Delete article "${article.title}"?`)) {
                deleteArticle.mutate(article.id);
              }
            }}
          >
            <Trash2 size={14} />
          </IconButton>
        </span>
      </div>
      {expanded ? (
        <p className="m-0 whitespace-pre-wrap break-words border-t border-border-soft bg-bg px-3 py-2.5 text-[13px] text-text">
          {article.text.length > 600 ? `${article.text.slice(0, 600)}...` : article.text}
        </p>
      ) : null}
    </div>
  );
}
