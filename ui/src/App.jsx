import { useEffect, useRef, useState } from "react";

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error((await res.text()) || res.statusText);
  return res.json();
}

function StatusBar({ status }) {
  if (!status) return null;
  const item = (ok, label) => (
    <span className={`pill ${ok ? "ok" : "bad"}`}>
      {ok ? "✓" : "✕"} {label}
    </span>
  );
  return (
    <div className="status">
      {item(status.ai_key, `${status.provider === "claude" ? "Claude" : "Gemini"} API key`)}
      {status.images && item(status.pexels_key, "Pexels images")}
      {item(status.blogger_connected, "Blogger connected")}
      {status.blog_url && (
        <a href={status.blog_url} target="_blank" rel="noreferrer">
          {status.blog_url}
        </a>
      )}
    </div>
  );
}

function Generate({ config, onDone, disabled }) {
  const [count, setCount] = useState(1);
  const [niche, setNiche] = useState("");
  const [topic, setTopic] = useState("");
  const [research, setResearch] = useState(true);
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const logRef = useRef(null);

  useEffect(() => {
    if (!job || job.status !== "running") return;
    const t = setInterval(async () => {
      const j = await api(`/api/jobs/${job.id}`);
      setJob(j);
      if (j.status !== "running") onDone();
    }, 2000);
    return () => clearInterval(t);
  }, [job, onDone]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [job]);

  const start = async () => {
    setError("");
    try {
      setJob(await api("/api/generate", { method: "POST", body: JSON.stringify({ count, niche, topic, research }) }));
    } catch (e) {
      setError(e.message);
    }
  };

  const running = job?.status === "running";
  return (
    <section className="card">
      <h2>Write new posts</h2>
      <div className="grid">
        <label>
          How many
          <input type="number" min="1" max="5" value={count} onChange={(e) => setCount(+e.target.value)} />
        </label>
        <label>
          Niche
          <select value={niche} onChange={(e) => setNiche(e.target.value)}>
            <option value="">Random from config</option>
            {config?.niches?.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </label>
        <label className="wide">
          Exact topic (optional)
          <input value={topic} placeholder="e.g. Best AI CRM for real estate agents" onChange={(e) => setTopic(e.target.value)} />
        </label>
        <label className="check">
          <input type="checkbox" checked={research} onChange={(e) => setResearch(e.target.checked)} />
          Pick a trending US topic automatically
        </label>
      </div>
      <button className="primary" disabled={disabled || running} onClick={start}>
        {running ? "Writing…" : "Generate"}
      </button>
      {error && <p className="error">{error}</p>}
      {job && (
        <>
          <p className={`job ${job.status}`}>Job {job.id}: {job.status}</p>
          <pre className="log" ref={logRef}>{job.log.join("\n") || "Starting…"}</pre>
        </>
      )}
    </section>
  );
}

function Posts({ posts, onOpen, onChange }) {
  const [busy, setBusy] = useState("");
  const upload = async (file) => {
    setBusy(file);
    try {
      await api(`/api/posts/${encodeURIComponent(file)}/upload`, { method: "POST" });
      onChange();
    } catch (e) {
      alert(e.message);
    } finally {
      setBusy("");
    }
  };

  return (
    <section className="card">
      <h2>Posts ({posts.length})</h2>
      {posts.length === 0 && <p className="muted">No posts yet. Generate your first one above.</p>}
      <ul className="posts">
        {posts.map((p) => (
          <li key={p.file}>
            <div>
              <button className="link" onClick={() => onOpen(p.file)}>{p.title}</button>
              <div className="muted small">{p.date} · {p.niche}</div>
            </div>
            {p.blogger_id ? (
              <span className="pill ok">Draft on Blogger</span>
            ) : (
              <button disabled={busy === p.file} onClick={() => upload(p.file)}>
                {busy === p.file ? "Uploading…" : "Upload draft"}
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Preview({ file, onClose }) {
  const [post, setPost] = useState(null);
  useEffect(() => {
    api(`/api/posts/${encodeURIComponent(file)}`).then(setPost);
  }, [file]);
  return (
    <div className="overlay" onClick={onClose}>
      <article className="preview" onClick={(e) => e.stopPropagation()}>
        <button className="close" onClick={onClose}>✕</button>
        {!post ? <p>Loading…</p> : (
          <>
            <h1>{post.meta.title}</h1>
            <div className="seo">
              <div><b>Meta description</b> ({(post.meta.meta_description || "").length} chars): {post.meta.meta_description}</div>
              <div><b>Slug</b>: {post.meta.slug}</div>
              <div><b>Keyword</b>: {post.meta.primary_keyword}</div>
              <button onClick={() => navigator.clipboard.writeText(post.meta.meta_description || "")}>Copy meta description</button>
            </div>
            <div className="body" dangerouslySetInnerHTML={{ __html: post.html }} />
          </>
        )}
      </article>
    </div>
  );
}

function ApiKeys({ onSaved }) {
  const [name, setName] = useState("GEMINI_API_KEY");
  const [value, setValue] = useState("");
  const [msg, setMsg] = useState("");
  const save = async () => {
    setMsg("");
    try {
      await api("/api/keys", { method: "POST", body: JSON.stringify({ name, value }) });
      setValue("");
      setMsg(`${name} saved ✓`);
      onSaved();
    } catch (e) {
      setMsg(e.message);
    }
  };
  return (
    <section className="card">
      <h2>API keys</h2>
      <p className="muted small">Keys are saved only in the local .env file on this computer. Never paste them in chat.</p>
      <div className="grid">
        <label>
          Key
          <select value={name} onChange={(e) => setName(e.target.value)}>
            <option value="GEMINI_API_KEY">Gemini (free)</option>
            <option value="PEXELS_API_KEY">Pexels images</option>
            <option value="ANTHROPIC_API_KEY">Claude</option>
          </select>
        </label>
        <label>
          New value
          <input type="password" autoComplete="off" value={value} placeholder="Paste key here" onChange={(e) => setValue(e.target.value)} />
        </label>
      </div>
      <button className="primary" disabled={!value} onClick={save}>Save key</button>
      {msg && <span className="muted"> {msg}</span>}
    </section>
  );
}

function Settings({ config, onSaved }) {
  const [draft, setDraft] = useState(config);
  const [saved, setSaved] = useState(false);
  useEffect(() => setDraft(config), [config]);
  if (!draft) return null;

  const set = (k, v) => { setDraft({ ...draft, [k]: v }); setSaved(false); };
  const save = async () => {
    await api("/api/config", { method: "PUT", body: JSON.stringify(draft) });
    setSaved(true);
    onSaved();
  };

  return (
    <section className="card">
      <h2>Settings</h2>
      <div className="grid">
        <label>Blog name<input value={draft.blog_name} onChange={(e) => set("blog_name", e.target.value)} /></label>
        <label>Author<input value={draft.author} onChange={(e) => set("author", e.target.value)} /></label>
        <label>Words per post<input type="number" value={draft.word_count} onChange={(e) => set("word_count", +e.target.value)} /></label>
        <label>Posts per daily run<input type="number" min="1" max="5" value={draft.posts_per_run} onChange={(e) => set("posts_per_run", +e.target.value)} /></label>
        <label className="wide">Tone<input value={draft.tone} onChange={(e) => set("tone", e.target.value)} /></label>
        <label className="wide">
          Niches (one per line)
          <textarea rows="5" value={draft.niches.join("\n")} onChange={(e) => set("niches", e.target.value.split("\n").filter(Boolean))} />
        </label>
        <label className="check">
          <input type="checkbox" checked={draft.blogger_upload} onChange={(e) => set("blogger_upload", e.target.checked)} />
          Upload to Blogger as draft automatically
        </label>
      </div>
      <button className="primary" onClick={save}>Save settings</button>
      {saved && <span className="muted"> Saved ✓</span>}
    </section>
  );
}

export default function App() {
  const [status, setStatus] = useState(null);
  const [config, setConfig] = useState(null);
  const [posts, setPosts] = useState([]);
  const [open, setOpen] = useState(null);
  const [tab, setTab] = useState("write");

  const refresh = () => {
    api("/api/status").then(setStatus);
    api("/api/posts").then(setPosts);
  };
  useEffect(() => {
    refresh();
    api("/api/config").then(setConfig);
  }, []);

  return (
    <main>
      <header>
        <h1>{config?.blog_name || "Blog"} Dashboard</h1>
        <StatusBar status={status} />
        <nav>
          {["write", "posts", "settings"].map((t) => (
            <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
              {t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
        </nav>
      </header>
      {tab === "write" && <Generate config={config} onDone={refresh} disabled={!status?.ai_key} />}
      {tab === "write" && !status?.ai_key && status && (
        <p className="error">Add GEMINI_API_KEY to the .env file (free key: aistudio.google.com), then restart server.py.</p>
      )}
      {(tab === "posts" || tab === "write") && <Posts posts={posts} onOpen={setOpen} onChange={refresh} />}
      {tab === "settings" && <ApiKeys onSaved={refresh} />}
      {tab === "settings" && <Settings config={config} onSaved={() => api("/api/config").then(setConfig)} />}
      {open && <Preview file={open} onClose={() => setOpen(null)} />}
    </main>
  );
}
