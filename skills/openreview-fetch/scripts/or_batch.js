// OpenReview bulk reader for a logged-in openreview.net tab.
// Paste the whole file into the page (e.g. Claude in Chrome javascript_tool). It defines helpers and returns 'ready'.
//
//   __orList('ICLR.cc/2027/Conference/Submission', {minReplies: 10})  -> starts listing; poll window.__or
//   __orPull(ids)                                                    -> starts batched discussion pull; poll window.__or
//   __orThreads(window.__or.forums)                                  -> one record per review with its thread
//
// Budget: every request increments window.__or.req. The run stops at cfg.budget or at the first non-200 reply.
// A 429 is never retried; window.__or.error keeps the server message, which states the wait time.

(() => {
  const API = 'https://api2.openreview.net';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const st = window.__or = window.__or || { req: 0 };
  Object.assign(st, { status: 'idle', error: null });

  async function get(path, cfg) {
    if (st.req >= cfg.budget) { st.status = 'budget-reached'; return null; }
    const r = await fetch(API + path, { credentials: 'include' });
    st.req++;
    if (r.status !== 200) {
      st.status = r.status === 429 ? 'rate-limited' : 'error';
      st.error = `HTTP ${r.status}: ` + (await r.text()).replace(/https?:\S+/g, '<url>').slice(0, 240);
      return null;
    }
    return r.json();
  }

  // List submissions with reply counts, 1 request per 1,000 notes.
  window.__orList = (venueid, opts = {}) => {
    const cfg = Object.assign({ budget: 300, gapMs: 800, minReplies: 0, exclude: [] }, opts);
    Object.assign(st, { status: 'listing', list: [], error: null });
    (async () => {
      for (let off = 0; ; off += 1000) {
        const q = `/notes?content.venueid=${encodeURIComponent(venueid)}&limit=1000&offset=${off}` +
                  `&select=id,details&details=replyCount`;
        const j = await get(q, cfg);
        if (!j) return;
        const ns = j.notes || [];
        for (const n of ns) {
          const c = n.details?.replyCount || 0;
          if (c >= cfg.minReplies && !cfg.exclude.includes(n.id)) st.list.push([n.id, c]);
        }
        if (ns.length < 1000) break;
        await sleep(cfg.gapMs);
      }
      st.status = 'listed';
    })();
    return 'listing started';
  };

  // Pull full discussions, 1 request per 50 forums.
  window.__orPull = (ids, opts = {}) => {
    const cfg = Object.assign({ budget: 300, batch: 50, gapMs: 1200 }, opts);
    Object.assign(st, { status: 'pulling', forums: [], error: null, total: ids.length });
    (async () => {
      for (let i = 0; i < ids.length; i += cfg.batch) {
        const j = await get(`/notes?ids=${ids.slice(i, i + cfg.batch).join(',')}&details=replies`, cfg);
        if (!j) return;
        st.forums.push(...(j.notes || []));
        st.done = st.forums.length;
        await sleep(cfg.gapMs);
      }
      st.status = 'pulled';
    })();
    return `pull started: ${ids.length} forums, about ${Math.ceil(ids.length / cfg.batch)} requests`;
  };

  // One record per review: the review content, the reviewer's and the authors' notes in its thread,
  // and the authors' top-level (general) comments on the forum.
  window.__orThreads = (forums) => {
    const signedBy = (n, suffix) => (n.signatures || []).some(s => s.endsWith(suffix));
    const isReview = n => (n.invitations || []).some(i => i.endsWith('Official_Review'));
    const isComment = n => (n.invitations || []).some(i => i.includes('Official_Comment'));
    const out = [];
    for (const f of forums) {
      const fid = f.id, notes = f.details?.replies || [];
      const byId = Object.fromEntries(notes.map(n => [n.id, n]));
      const rootOf = n => { let c = n, g = 0; while (c && c.replyto && c.replyto !== fid && g++ < 80) c = byId[c.replyto]; return c?.id; };
      const general = notes.filter(n => n.replyto === fid && signedBy(n, '/Authors') && isComment(n));
      for (const rv of notes.filter(isReview)) {
        const rid = (rv.signatures?.[0] || '').split('_').pop();
        const thread = notes.filter(n => n.id !== rv.id && rootOf(n) === rv.id).sort((a, b) => a.cdate - b.cdate);
        const text = ns => ns.map(n => n.content?.comment?.value || '').join('\n\n=====\n\n');
        const authors = thread.filter(n => signedBy(n, '/Authors'));
        const reviewer = thread.filter(n => signedBy(n, `Reviewer_${rid}`));
        out.push({
          forum: fid, reviewer: rid, review: Object.fromEntries(Object.entries(rv.content || {}).map(([k, v]) => [k, v?.value])),
          authorPosts: authors.length, authorText: text(authors),
          reviewerPosts: reviewer.length, reviewerText: text(reviewer),
          generalResponses: general.length, generalText: text(general),
        });
      }
    }
    return out;
  };

  return 'ready';
})();
