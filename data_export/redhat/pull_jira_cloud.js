// Pull of Red Hat's public Jira Cloud (redhat.atlassian.net) for the replication cohort, 14 Nov 2026.
// Run in the browser console on any page of https://redhat.atlassian.net (no login needed; the cloud
// sandbox cannot reach the site). It reproduces the three steps used for the paper:
//   1. screen()   lists public projects, counts sprint issues and story-point coverage, and summarises
//                 each project's closed sprints (used for the rule in SELECTION.md)
//   2. eraGap()   share of issue numbers an anonymous reader cannot see, per selected project
//   3. pull()     every issue that is in a sprint, with its Sprint and Story Points change history
//                 (full change log fetched when the search response truncates it)
// Then save window.__P with download() and convert with
//   python data_export/outside/convert_jira.py redhat_pull.json data/raw/redhat --all-boards KEY="Red Hat KEY" ...
// Field ids on this instance: Sprint = customfield_10020, Story Points = customfield_10028.

const SPRINT = 'customfield_10020', SP = 'customfield_10028';

async function get(u) {
  for (let a = 0; a < 6; a++) {
    try { const r = await fetch(u); if (r.ok) return r.json(); if (r.status === 429) await new Promise(z => setTimeout(z, 10000)); }
    catch (e) { }
    await new Promise(z => setTimeout(z, 2000 * (a + 1)));
  }
  return null;
}
async function count(jql) {
  const r = await fetch('/rest/api/3/search/approximate-count', { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Atlassian-Token': 'no-check' }, body: JSON.stringify({ jql }) });
  return r.ok ? (await r.json()).count : -1;
}
async function* search(jql, fields, expand) {
  let tok = null;
  do {
    const r = await get('/rest/api/3/search/jql?jql=' + encodeURIComponent(jql) + '&maxResults=100&fields=' + fields +
      (expand ? '&expand=' + expand : '') + (tok ? '&nextPageToken=' + encodeURIComponent(tok) : ''));
    if (!r) return;
    for (const is of r.issues) yield is;
    tok = r.nextPageToken;
  } while (tok);
}

async function screen() {
  let projs = [], start = 0, last = false;
  while (!last) { const r = await get('/rest/api/3/project/search?maxResults=100&startAt=' + start); if (!r) break;
    projs = projs.concat(r.values.map(p => p.key)); last = r.isLast; start += r.values.length; if (!r.values.length) break; }
  const cand = [];
  for (const k of projs) { const a = await count(`project="${k}" AND sprint is not EMPTY`);
    if (a >= 300) cand.push([k, a, await count(`project="${k}" AND sprint is not EMPTY AND "Story Points" is not EMPTY`)]); }
  const S = {};
  for (const [k] of cand) for await (const is of search(`project="${k}" AND sprint is not EMPTY ORDER BY key ASC`, SPRINT + ',' + SP))
    for (const s of (is.fields[SPRINT] || [])) {
      const x = S[s.id] || (S[s.id] = { s, proj: {}, n: 0, sp: 0 }); x.proj[k] = (x.proj[k] || 0) + 1; x.n++; }
  const out = {};
  for (const x of Object.values(S)) {
    const { s } = x; if (s.state !== 'closed' || !s.startDate || !s.endDate || !s.completeDate) continue;
    if ((Date.parse(s.endDate) - Date.parse(s.startDate)) / 864e5 > 60) continue;
    const [k, m] = Object.entries(x.proj).sort((a, b) => b[1] - a[1])[0];
    const o = out[k] || (out[k] = { sprints: 0, shared: 0 }); o.sprints++; if (m / x.n < 0.8) o.shared++;
  }
  window.__screen = cand.map(([k, a, b]) => ({ key: k, sprintIssues: a, spShare: b / a, ...(out[k] || {}) }));
  return window.__screen.filter(r => r.sprints >= 100 && r.shared / r.sprints <= 0.2 && r.spShare >= 0.5);
}

async function eraGap(keys) {
  const out = [];
  for (const k of keys) {
    const hi = await get('/rest/api/3/search/jql?jql=' + encodeURIComponent(`project="${k}" ORDER BY key DESC`) + '&maxResults=1&fields=created');
    const lo = await get('/rest/api/3/search/jql?jql=' + encodeURIComponent(`project="${k}" AND sprint is not EMPTY ORDER BY key ASC`) + '&maxResults=1&fields=created');
    const maxn = +hi.issues[0].key.split('-')[1], minn = +lo.issues[0].key.split('-')[1];
    const vis = await count(`project="${k}" AND key >= "${k}-${minn}"`);
    out.push({ key: k, gap: 1 - vis / (maxn - minn + 1) });
  }
  return out;
}

async function pull(projects) {
  const P = { origin: location.origin, pulled: new Date().toISOString(), issues: [], errors: [], scanned: {} };
  const keep = it => /^sprint$/i.test(it.field) || /^story points?$/i.test(it.field) || it.fieldId === SPRINT || it.fieldId === SP;
  const fields = 'issuetype,status,priority,created,resolutiondate,assignee,resolution,timeoriginalestimate,' + SPRINT + ',' + SP;
  for (const k of projects) {
    let total = 0;
    for await (const is of search(`project="${k}" AND sprint is not EMPTY ORDER BY key ASC`, fields, 'changelog')) {
      total++; const f = is.fields; let hist = is.changelog ? is.changelog.histories : [];
      if (is.changelog && is.changelog.total > is.changelog.maxResults) {
        hist = []; let st = 0;
        while (true) { const r = await get(`/rest/api/3/issue/${is.id}/changelog?startAt=${st}&maxResults=100`); if (!r) break;
          hist = hist.concat(r.values); st += r.values.length; if (r.isLast || !r.values.length) break; }
      }
      const ch = []; for (const h of hist) for (const it of h.items) if (keep(it))
        ch.push([h.id, /sprint/i.test(it.field) ? 'Sprint' : 'Story Points', it.from, it.to, it.fromString, it.toString, h.created]);
      P.issues.push({ p: k, id: is.id, k: is.key, t: f.issuetype && f.issuetype.name, s: f.status && f.status.name,
        pr: f.priority && f.priority.name, c: f.created, r: f.resolutiondate, res: f.resolution && f.resolution.name,
        a: f.assignee && f.assignee.accountId, oe: f.timeoriginalestimate, sp: f[SP],
        spr: (f[SPRINT] || []).map(s => ({ id: s.id, name: s.name, state: s.state, boardId: s.boardId,
          startDate: s.startDate, endDate: s.endDate, completeDate: s.completeDate })), ch });
    }
    P.scanned[k] = { total };
  }
  window.__P = P;
  return P.issues.length;
}

async function download(name = 'redhat_pull.json.gz') {
  const gz = await new Response(new Blob([JSON.stringify(window.__P)]).stream().pipeThrough(new CompressionStream('gzip'))).blob();
  const a = document.createElement('a'); a.href = URL.createObjectURL(gz); a.download = name; document.body.appendChild(a); a.click();
}
