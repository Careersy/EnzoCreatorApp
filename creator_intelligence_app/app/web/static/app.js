const tabs = document.querySelectorAll('#tabs button');
const panels = document.querySelectorAll('.tab-panel');

tabs.forEach((btn) => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;
    if (target) switchToTab(target);
  });
});

function switchToTab(tabId) {
  tabs.forEach((b) => b.classList.remove('active'));
  panels.forEach((p) => p.classList.remove('active'));
  const tabBtn = document.querySelector(`#tabs button[data-tab="${tabId}"]`);
  if (tabBtn) tabBtn.classList.add('active');
  const panel = document.getElementById(tabId);
  if (panel) panel.classList.add('active');
}

function esc(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function renderJson(elId, payload) {
  const el = document.getElementById(elId);
  if (el) el.textContent = JSON.stringify(payload, null, 2);
}

function attrEncode(value) {
  return encodeURIComponent(String(value || ''));
}

function attrDecode(value) {
  try {
    return decodeURIComponent(String(value || ''));
  } catch (_err) {
    return String(value || '');
  }
}

function formToObj(form) {
  const fd = new FormData(form);
  const out = {};
  for (const [k, v] of fd.entries()) out[k] = v;
  return out;
}

function parseCreatorWeights(text) {
  const lines = String(text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  const parsed = [];
  for (const line of lines) {
    const [namePart, weightPart] = line.split('=');
    const creator = String(namePart || '').trim();
    const rawWeight = Number(String(weightPart || '').trim());
    if (!creator) continue;
    parsed.push({
      creator,
      weight: Number.isFinite(rawWeight) && rawWeight > 0 ? rawWeight : 1,
    });
  }
  return parsed;
}

function apiHeaders(extra = {}) {
  const token = localStorage.getItem('creator_api_token') || '';
  const headers = { ...extra };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function requestJson(url, options = {}) {
  const res = await fetch(url, options);
  let payload = {};
  try {
    payload = await res.json();
  } catch (_err) {
    payload = { detail: 'Non-JSON response from server' };
  }
  if (!res.ok) {
    return { error: true, status: res.status, ...payload };
  }
  return payload;
}

async function postJson(url, body) {
  return requestJson(url, {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  });
}

async function getJson(url) {
  return requestJson(url, { headers: apiHeaders() });
}

/* ---------- Pretty Rendering ---------- */
function toShortLine(value) {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) return value.map((v) => toShortLine(v)).filter(Boolean).join(' | ');
  if (typeof value === 'object') {
    const keys = Object.keys(value);
    return keys
      .slice(0, 4)
      .map((k) => `${k}: ${toShortLine(value[k])}`)
      .join(' | ');
  }
  return String(value);
}

function proseToHtml(text) {
  const lines = String(text || '')
    .replace(/\r/g, '')
    .split('\n');
  if (!lines.some((l) => l.trim())) return '<p class="muted">No text available.</p>';

  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line) {
      i += 1;
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      const level = Math.min(4, headingMatch[1].length + 1);
      out.push(`<h${level}>${esc(headingMatch[2])}</h${level}>`);
      i += 1;
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
        i += 1;
      }
      out.push(`<ol>${items.map((item) => `<li>${esc(item)}</li>`).join('')}</ol>`);
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ''));
        i += 1;
      }
      out.push(`<ul>${items.map((item) => `<li>${esc(item)}</li>`).join('')}</ul>`);
      continue;
    }

    const block = [];
    while (i < lines.length) {
      const cur = lines[i].trim();
      if (!cur || /^(#{1,6})\s+/.test(cur) || /^\d+\.\s+/.test(cur) || /^[-*]\s+/.test(cur)) break;
      block.push(cur);
      i += 1;
    }
    out.push(`<p>${esc(block.join(' '))}</p>`);
  }
  return out.join('');
}

function listHtml(items, ordered = false) {
  const normalized = Array.isArray(items) ? items.map((x) => toShortLine(x)).filter(Boolean) : [];
  if (!normalized.length) return '<p class="muted">No items</p>';
  const tag = ordered ? 'ol' : 'ul';
  return `<${tag}>${normalized.map((item) => `<li>${esc(item)}</li>`).join('')}</${tag}>`;
}

function scorePills(scores) {
  if (!scores || typeof scores !== 'object') return '';
  const keys = Object.keys(scores);
  if (!keys.length) return '';
  return `<div class="score-pills">${keys
    .map((k) => `<span class="score-pill"><strong>${esc(k)}</strong> ${esc(scores[k])}</span>`)
    .join('')}</div>`;
}

function resultCard(title, bodyHtml, opts = {}) {
  const tone = opts.tone ? ` ${opts.tone}` : '';
  return `<section class="result-card${tone}"><h3>${esc(title)}</h3><div class="prose">${bodyHtml}</div></section>`;
}

function rawJsonDetails(payload) {
  return `<details class="raw-json"><summary>View raw JSON</summary><pre>${esc(JSON.stringify(payload || {}, null, 2))}</pre></details>`;
}

function sentenceCount(text) {
  return String(text || '')
    .split(/[.!?]+/)
    .map((s) => s.trim())
    .filter(Boolean).length;
}

function wordCount(text) {
  return String(text || '')
    .split(/\s+/)
    .map((s) => s.trim())
    .filter(Boolean).length;
}

function firstLine(text) {
  const line = String(text || '')
    .split('\n')
    .find((l) => l.trim());
  return line ? line.trim() : '';
}

function rewriteImprovements(context, payload) {
  const original = String(context?.original_text || '');
  const rewritten = String(payload?.rewritten_version || '');
  const points = [];
  if (original && rewritten) {
    const oldWords = wordCount(original);
    const newWords = wordCount(rewritten);
    if (newWords < oldWords) points.push(`Tighter draft: ${oldWords} -> ${newWords} words.`);
    else if (newWords > oldWords) points.push(`Expanded clarity: ${oldWords} -> ${newWords} words.`);

    const oldSent = sentenceCount(original);
    const newSent = sentenceCount(rewritten);
    points.push(`Sentence pacing adjusted: ${oldSent} -> ${newSent} sentences.`);

    const oldHook = firstLine(original);
    const newHook = firstLine(rewritten);
    if (oldHook && newHook && oldHook !== newHook) {
      points.push(`Hook upgraded from "${oldHook.slice(0, 80)}..." to "${newHook.slice(0, 80)}...".`);
    }
  }
  const rules = payload?.notes?.applied_rules || [];
  for (const rule of rules) points.push(String(rule));
  return points.slice(0, 6);
}

function rewriteHighlightsTable(context, payload) {
  const original = String(context?.original_text || '');
  const rewritten = String(payload?.rewritten_version || '');
  const rows = [
    ['Hook', firstLine(original) || '-', firstLine(rewritten) || '-'],
    ['Word count', wordCount(original), wordCount(rewritten)],
    ['Sentence count', sentenceCount(original), sentenceCount(rewritten)],
    ['CTA signal', String(original).toLowerCase().includes('?') ? 'Present' : 'Weak', String(rewritten).toLowerCase().includes('?') ? 'Present' : 'Weak'],
  ];
  return `<table class="highlight-table">
    <thead><tr><th>Dimension</th><th>Before</th><th>After</th></tr></thead>
    <tbody>${rows
      .map((r) => `<tr><td>${esc(r[0])}</td><td>${esc(r[1])}</td><td>${esc(r[2])}</td></tr>`)
      .join('')}</tbody>
  </table>`;
}

function generateImprovements(context, payload) {
  const points = [];
  const topic = String(context?.topic || '').trim();
  if (topic) points.push(`Draft built for topic: ${topic}.`);
  const styleNotes = payload?.style_notes || [];
  for (const note of styleNotes) points.push(String(note));
  if (Array.isArray(payload?.alternate_hooks) && payload.alternate_hooks.length) {
    points.push(`Added ${payload.alternate_hooks.length} hook alternatives for testing.`);
  }
  if (Array.isArray(payload?.cta_options) && payload.cta_options.length) {
    points.push(`Included ${payload.cta_options.length} CTA options.`);
  }
  return points.slice(0, 6);
}

function generateHighlightsTable(context, payload) {
  const draft = String(payload?.final_draft || '');
  const briefAudience =
    context?.audience && String(context.audience).toLowerCase() !== 'general' ? context.audience : 'Not specified';
  const briefGoal =
    context?.goal && String(context.goal).toLowerCase() !== 'clarity' ? context.goal : 'Not specified';
  const rows = [
    ['Topic brief', context?.topic || '-', firstLine(draft) || '-'],
    ['Audience', briefAudience, briefAudience],
    ['Goal', briefGoal, briefGoal],
    ['Word count', '-', wordCount(draft)],
    ['Paragraph blocks', '-', String(draft.split(/\n\s*\n/).filter((x) => x.trim()).length)],
  ];
  return `<table class="highlight-table">
    <thead><tr><th>Dimension</th><th>Brief</th><th>Output</th></tr></thead>
    <tbody>${rows
      .map((r) => `<tr><td>${esc(r[0])}</td><td>${esc(r[1])}</td><td>${esc(r[2])}</td></tr>`)
      .join('')}</tbody>
  </table>`;
}

function relationBreakdown(records, fallbackRelation = '') {
  const counts = {};
  for (const row of records || []) {
    const rel = String(row?.relation || fallbackRelation || 'RELATED');
    counts[rel] = (counts[rel] || 0) + 1;
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1]);
}

function graphRecordTable(records, limit = 40) {
  const rows = (records || []).slice(0, limit);
  if (!rows.length) return '<p class="muted">No graph matches found.</p>';
  return `<div class="graph-table-wrap"><table class="graph-table">
    <thead>
      <tr>
        <th>Creator</th>
        <th>Pattern</th>
        <th>Type</th>
        <th>Relation</th>
        <th>Weight/Frequency</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>${rows
      .map((row) => {
        const edge = row?.edge || {};
        const weight = row?.weight ?? edge?.frequency ?? row?.frequency ?? '-';
        const creator = String(row?.creator || '');
        const pattern = String(row?.pattern || '');
        const relation = String(row?.relation || '');
        return `<tr>
          <td>${esc(creator || '-')}</td>
          <td>${esc(pattern || '-')}</td>
          <td>${esc(row?.pattern_type || '-')}</td>
          <td>${esc(relation || '-')}</td>
          <td>${esc(weight)}</td>
          <td>
            <div class="graph-actions">
              <button type="button" class="graph-action-btn graph-copy" data-creator="${attrEncode(creator)}" data-pattern="${attrEncode(pattern)}" data-relation="${attrEncode(relation)}">Copy</button>
              <button type="button" class="graph-action-btn graph-use-generate" data-creator="${attrEncode(creator)}" data-pattern="${attrEncode(pattern)}">Use in Generate</button>
              <button type="button" class="graph-action-btn graph-use-rewrite" data-creator="${attrEncode(creator)}" data-pattern="${attrEncode(pattern)}">Use in Rewrite</button>
            </div>
          </td>
        </tr>`;
      })
      .join('')}</tbody>
  </table></div>`;
}

function graphCreatorGroups(records, limitCreators = 10, perCreator = 8) {
  if (!records || !records.length) return '<p class="muted">No creator group data.</p>';
  const groups = {};
  for (const row of records) {
    const creator = String(row?.creator || 'Unknown');
    groups[creator] = groups[creator] || [];
    groups[creator].push(row);
  }

  const creators = Object.keys(groups)
    .sort((a, b) => groups[b].length - groups[a].length)
    .slice(0, limitCreators);

  return `<div class="graph-groups">${creators
    .map((creator) => {
      const items = groups[creator].slice(0, perCreator);
      return `<details class="graph-group">
        <summary>${esc(creator)} <span class="graph-count">${items.length}</span></summary>
        <ul>${items
          .map(
            (item) =>
              `<li><strong>${esc(item?.pattern || '-')}</strong> <span class="graph-tag">${esc(item?.pattern_type || '-')}</span> <span class="muted">(${esc(item?.relation || '-')})</span></li>`,
          )
          .join('')}</ul>
      </details>`;
    })
    .join('')}</div>`;
}

function renderModePayload(mode, payload, context = {}) {
  if (payload?.error) {
    return resultCard('Error', `<p>${esc(payload.detail || 'Request failed')}</p>`, { tone: 'danger' });
  }

  if (mode === 'rewrite') {
    const cards = [];
    const modelUsed = payload?.model_used || payload?.llm_meta?.resolved_model || context?.model || 'default';
    const requestedModel = payload?.llm_meta?.requested_model;
    cards.push(
      resultCard(
        'Model Used',
        `<p><strong>${esc(modelUsed)}</strong>${requestedModel && requestedModel !== modelUsed ? ` <span class=\"muted\">(requested: ${esc(requestedModel)})</span>` : ''}</p>`,
      ),
    );
    if (payload?.llm_meta?.fallback_used) {
      cards.push(
        resultCard(
          'Model Warning',
          `<p>Remote model failed. This output is a local fallback preview.</p><p class="muted">${esc(payload?.llm_meta?.error || 'Unknown model/network issue')}</p>`,
          { tone: 'danger' },
        ),
      );
    }
    cards.push(resultCard('Final Publish-Ready Version', proseToHtml(payload.rewritten_version || ''), { tone: 'publish' }));
    cards.push(resultCard('Key Improvements Made', listHtml(rewriteImprovements(context, payload))));
    cards.push(resultCard('Before / After Highlights', rewriteHighlightsTable(context, payload)));
    cards.push(resultCard('Stronger Hooks', listHtml(payload.stronger_hooks || [])));
    cards.push(resultCard('Style Scores', scorePills(payload.scores || {})));
    const notes = payload.notes?.applied_rules || payload.notes?.genericity_notes || [];
    cards.push(resultCard('Applied Rules', listHtml(notes)));
    cards.push(
      `<details class="result-details"><summary>See alternate versions</summary>
        <div class="result-grid-two">
          ${resultCard('More Concise', proseToHtml(payload.more_concise || ''))}
          ${resultCard('More Punchy', proseToHtml(payload.more_punchy || ''))}
        </div>
      </details>`,
    );
    return cards.join('');
  }

  if (mode === 'generate') {
    const cards = [];
    const modelUsed = payload?.model_used || payload?.llm_meta?.resolved_model || context?.model || 'default';
    const requestedModel = payload?.llm_meta?.requested_model;
    cards.push(
      resultCard(
        'Model Used',
        `<p><strong>${esc(modelUsed)}</strong>${requestedModel && requestedModel !== modelUsed ? ` <span class=\"muted\">(requested: ${esc(requestedModel)})</span>` : ''}</p>`,
      ),
    );
    if (payload?.llm_meta?.fallback_used) {
      cards.push(
        resultCard(
          'Model Warning',
          `<p>Remote model failed. This output is a local fallback preview.</p><p class="muted">${esc(payload?.llm_meta?.error || 'Unknown model/network issue')}</p>`,
          { tone: 'danger' },
        ),
      );
    }
    cards.push(resultCard('Final Publish-Ready Version', proseToHtml(payload.final_draft || ''), { tone: 'publish' }));
    cards.push(resultCard('Key Improvements Made', listHtml(generateImprovements(context, payload))));
    cards.push(resultCard('Before / After Highlights', generateHighlightsTable(context, payload)));
    cards.push(resultCard('Hook Options', listHtml(payload.alternate_hooks || [])));
    cards.push(resultCard('CTA Options', listHtml(payload.cta_options || [])));
    cards.push(resultCard('Style Notes', listHtml(payload.style_notes || [])));
    cards.push(resultCard('Scores', scorePills(payload.scores || {})));
    return cards.join('');
  }

  if (mode === 'expand') {
    const cards = [];
    const modelUsed = payload?.model_used || payload?.llm_meta?.resolved_model || context?.model || 'default';
    const requestedModel = payload?.llm_meta?.requested_model;
    cards.push(
      resultCard(
        'Model Used',
        `<p><strong>${esc(modelUsed)}</strong>${requestedModel && requestedModel !== modelUsed ? ` <span class=\"muted\">(requested: ${esc(requestedModel)})</span>` : ''}</p>`,
      ),
    );
    if (payload?.llm_meta?.fallback_used) {
      cards.push(
        resultCard(
          'Model Warning',
          `<p>Remote model failed. This output is a local fallback preview.</p><p class="muted">${esc(payload?.llm_meta?.error || 'Unknown model/network issue')}</p>`,
          { tone: 'danger' },
        ),
      );
    }
    cards.push(resultCard('Final Publish-Ready Version', proseToHtml(payload.full_draft || ''), { tone: 'publish' }));
    cards.push(resultCard('Key Improvements Made', listHtml(['Expanded short-form idea into long-form structure.', 'Added section flow, examples, and transitions.', 'Maintained style constraints while improving depth.'])));
    cards.push(resultCard('Before / After Highlights', `<table class="highlight-table">
      <thead><tr><th>Dimension</th><th>Before</th><th>After</th></tr></thead>
      <tbody>
        <tr><td>Word count</td><td>${esc(wordCount(context?.source_text || ''))}</td><td>${esc(wordCount(payload.full_draft || ''))}</td></tr>
        <tr><td>Sentence count</td><td>${esc(sentenceCount(context?.source_text || ''))}</td><td>${esc(sentenceCount(payload.full_draft || ''))}</td></tr>
        <tr><td>Structure</td><td>Short-form</td><td>${esc(payload.outline?.length || 0)} section outline</td></tr>
      </tbody>
    </table>`));
    cards.push(resultCard('Title Options', listHtml(payload.title_options || [])));
    cards.push(resultCard('Outline', listHtml(payload.outline || [], true)));
    cards.push(resultCard('Style Fidelity', scorePills(payload.style_fidelity_notes || {})));
    cards.push(`<details class="result-details"><summary>Shorter version</summary>${resultCard('Shorter', proseToHtml(payload.shorter_version || ''))}</details>`);
    return cards.join('');
  }

  if (mode === 'plan' || mode === 'calendar') {
    const cards = [];
    cards.push(resultCard('Weekly Themes', listHtml(payload.weekly_themes || [])));
    cards.push(
      resultCard(
        'Content Calendar',
        listHtml((payload.content_calendar || []).map((c) => `${c.date} (${c.weekday}) - ${c.title_seed || c.theme || ''}`)),
      ),
    );
    if (payload.posts) cards.push(resultCard('Draft Seeds', listHtml(payload.posts || [])));
    return cards.join('');
  }

  if (mode === 'topic_map') {
    const cards = [];
    cards.push(resultCard('Topic Pillars', listHtml((payload.topic_map || []).map((p) => p.pillar || toShortLine(p)))));
    cards.push(resultCard('Content Angles', listHtml(payload.content_angles || [])));
    cards.push(resultCard('Hooks', listHtml(payload.hooks || [])));
    cards.push(resultCard('Frameworks', listHtml(payload.frameworks || [])));
    return cards.join('');
  }

  if (mode === 'repurpose') {
    const cards = [];
    cards.push(
      resultCard(
        'Repurposing Pipeline',
        listHtml((payload.pipeline?.targets || []).map((t) => `${t.transform_rule}: ${t.structure} (${t.length_guidance})`)),
      ),
    );
    cards.push(
      resultCard(
        'Draft Variants',
        listHtml((payload.variants || []).map((v) => `${v.target_platform} - ${v.title_seed}`)),
      ),
    );
    return cards.join('');
  }

  if (mode === 'style_mix') {
    const cards = [];
    cards.push(resultCard('Mode', `<p>${esc(payload.mode || 'generate')}</p>`));
    if (payload.final_text) {
      cards.push(resultCard('Final Publish-Ready Version', proseToHtml(payload.final_text), { tone: 'publish' }));
    }
    const mix = payload.creator_mix || {};
    const weights = (mix.creator_weights || []).map((w) => `${w.creator} (${w.weight})`);
    cards.push(resultCard('Creator Weights (Normalized)', listHtml(weights)));
    cards.push(
      resultCard(
        'Mixed Pattern Sample',
        listHtml((mix.records || []).slice(0, 20).map((r) => `${r.creator}: ${r.relation} -> ${r.pattern}`)),
      ),
    );
    cards.push(resultCard('Blueprint Notes', listHtml(payload.output?.style_notes || payload.output?.notes?.applied_rules || [])));
    cards.push(resultCard('Scores', scorePills(payload.output?.scores || {})));
    return cards.join('');
  }

  if (mode === 'performance_ingest') {
    const cards = [];
    cards.push(resultCard('Event Stored', `<p>Event ID: <strong>${esc(payload.event_id || '-')}</strong></p>`));
    cards.push(resultCard('Engagement Score', `<p><strong>${esc(payload.engagement_score || 0)}</strong></p>`));
    cards.push(resultCard('Updated Hook Stats', listHtml(payload.hook_stats || [])));
    cards.push(resultCard('Graph Learning Update', listHtml(payload.graph_update || [])));
    return cards.join('');
  }

  if (mode === 'performance_summary') {
    const cards = [];
    cards.push(
      resultCard(
        'Top Performing Hooks',
        listHtml((payload.top_hooks || []).map((h) => `${h.hook_text} (avg ${h.avg_engagement_score}, n=${h.event_count})`)),
      ),
    );
    cards.push(
      resultCard(
        'Recent Events',
        listHtml((payload.recent_events || []).map((e) => `${e.platform}: ${e.hook_text} -> score ${e.engagement_score}`)),
      ),
    );
    return cards.join('');
  }

  if (mode === 'explorer') {
    const cards = [];
    if (payload.metrics) {
      const m = payload.metrics || {};
      cards.push(
        resultCard(
          'Voice Profile Summary',
          `<ul>
            <li>Samples analyzed: ${esc(m.sample_count || 0)}</li>
            <li>Average sentence words: ${esc(m.avg_sentence_words || 0)}</li>
            <li>Average paragraph sentences: ${esc(m.avg_paragraph_sentences || 0)}</li>
            <li>Formality score: ${esc(m.formality_score || 0)}</li>
          </ul>`,
        ),
      );
      cards.push(resultCard('Top Phrases', listHtml(m.top_phrases || [])));
    }
    if (payload.records || payload.relation || payload.strongest_hooks || payload.connectivity) {
      const records = payload.records || [];
      const creators = new Set(records.map((r) => String(r?.creator || '').trim()).filter(Boolean));
      const patterns = new Set(records.map((r) => String(r?.pattern || '').trim()).filter(Boolean));
      const rels = relationBreakdown(records, payload.relation);
      cards.push(
        resultCard(
          'Graph Query Overview',
          `<div class="graph-kpis">
            <div class="graph-kpi"><span>Relation</span><strong>${esc(payload.relation || '-')}</strong></div>
            <div class="graph-kpi"><span>Topic Hint</span><strong>${esc(payload.topic_hint || 'None')}</strong></div>
            <div class="graph-kpi"><span>Matches</span><strong>${esc(records.length)}</strong></div>
            <div class="graph-kpi"><span>Creators</span><strong>${esc(creators.size)}</strong></div>
            <div class="graph-kpi"><span>Patterns</span><strong>${esc(patterns.size)}</strong></div>
            <div class="graph-kpi"><span>Strong Hooks</span><strong>${esc((payload.strongest_hooks || []).length)}</strong></div>
          </div>`,
        ),
      );
      cards.push(
        resultCard(
          'Relationship Breakdown',
          rels.length
            ? `<div class="graph-chip-list">${rels
                .map(([name, count]) => `<span class="graph-chip">${esc(name)} <strong>${esc(count)}</strong></span>`)
                .join('')}</div>`
            : '<p class="muted">No relationship data available.</p>',
        ),
      );
      cards.push(resultCard('Pattern Matches', graphRecordTable(records, 60)));
      cards.push(resultCard('Creator Groups', graphCreatorGroups(records, 12, 8)));
      cards.push(resultCard('Strongest Hooks', listHtml(payload.strongest_hooks || [])));
      if (payload.connectivity) {
        const c = payload.connectivity || {};
        cards.push(
          resultCard(
            'Graph Connectivity',
            `<div class="graph-kpis">
              <div class="graph-kpi"><span>Status</span><strong>${esc(c.status || 'unknown')}</strong></div>
              <div class="graph-kpi"><span>Neo4j Enabled</span><strong>${esc(c.enabled)}</strong></div>
              <div class="graph-kpi"><span>Source</span><strong>${esc(c.source || '-')}</strong></div>
            </div>`,
          ),
        );
      }
    }
    if (!cards.length) {
      cards.push(resultCard('Response', proseToHtml(toShortLine(payload))));
    }
    return cards.join('');
  }

  return resultCard('Response', proseToHtml(toShortLine(payload)));
}

function setPrettyOutput(elId, mode, payload, context = {}) {
  const el = document.getElementById(elId);
  if (!el) return;
  const html = renderModePayload(mode, payload, context);
  el.innerHTML = `${html}${rawJsonDetails(payload)}`;
}

/* ---------- LinkedIn Preview ---------- */
let currentPreviewText = '';

function updateLinkedinPreview(text, summary) {
  const body = document.getElementById('linkedinPreviewContent');
  const count = document.getElementById('linkedinCharCount');
  const details = document.getElementById('chatResultSummary');
  currentPreviewText = String(text || '').trim();
  if (body) {
    body.textContent = currentPreviewText || 'Your generated or rewritten post will appear here.';
  }
  if (count) {
    count.textContent = `${currentPreviewText.length} / 3000`;
  }
  if (details) {
    details.textContent = summary || '';
  }
}

function primaryDraftFromResponse(mode, payload) {
  if (!payload || payload.error) return '';
  if (mode === 'rewrite') return payload.rewritten_version || '';
  if (mode === 'generate') return payload.final_draft || '';
  if (mode === 'expand') return payload.full_draft || '';
  if (mode === 'repurpose') return payload.variants?.[0]?.opening_seed || '';
  return '';
}

/* ---------- Chat ---------- */
function appendChatMessage(role, contentHtml, rich = false) {
  const wrap = document.getElementById('chatMessages');
  if (!wrap) return null;
  const block = document.createElement('div');
  block.className = `chat-msg ${role}`;
  const label = role === 'user' ? 'You' : role === 'assistant' ? 'Enzo' : 'System';
  block.innerHTML = `<div class="chat-msg-head">${label}</div>${rich ? `<div class="chat-rich">${contentHtml}</div>` : `<div>${esc(contentHtml).replaceAll('\n', '<br>')}</div>`}`;
  wrap.appendChild(block);
  wrap.scrollTop = wrap.scrollHeight;
  return block;
}

const chatModeEl = document.getElementById('chatMode');
const chatModelEl = document.getElementById('chatModel');
const chatInputEl = document.getElementById('chatInput');
const chatPlusBtnEl = document.getElementById('chatPlusBtn');
const chatPlusMenuEl = document.getElementById('chatPlusMenu');
const chatAttachBtnEl = document.getElementById('chatAttachBtn');
const chatFileInputEl = document.getElementById('chatFileInput');
const chatFileStatusEl = document.getElementById('chatFileStatus');
const CHAT_DEFAULT_CONTEXT = {
  platform: 'LinkedIn',
  audience: 'general',
  goal: 'clarity',
};
const chatBriefState = {
  active: false,
  mode: '',
  baseRequest: '',
  questions: [],
  answers: {},
  index: 0,
  context: null,
};

function prettyModelName(modelId) {
  const raw = String(modelId || '').trim();
  if (!raw) return 'Default model';
  const known = {
    'claude-3-5-haiku-latest': 'Claude Haiku 3.5',
    'claude-3-5-sonnet-latest': 'Claude Sonnet 3.5',
    'claude-3-7-sonnet-latest': 'Claude Sonnet 3.7',
    'claude-3-opus-latest': 'Claude Opus 3',
    'claude-opus-4-1': 'Claude Opus 4.1',
    'claude-opus-4-5': 'Claude Opus 4.5',
    'claude-sonnet-4-5': 'Claude Sonnet 4.5',
    'claude-sonnet-4-6': 'Claude Sonnet 4.6',
  };
  if (known[raw]) return known[raw];

  if (raw.startsWith('claude-')) {
    const cleaned = raw.replace(/-latest$/i, '');
    const family = cleaned.includes('opus') ? 'Opus' : cleaned.includes('haiku') ? 'Haiku' : 'Sonnet';
    const versionMatch = cleaned.match(/(\d)-(\d)(?:-(\d))?/);
    if (versionMatch) {
      const major = versionMatch[1];
      const minor = versionMatch[2];
      const patch = versionMatch[3] ? `.${versionMatch[3]}` : '';
      return `Claude ${family} ${major}.${minor}${patch}`;
    }
    return `Claude ${family}`;
  }

  if (raw.startsWith('gpt-')) {
    return raw.toUpperCase().replace('GPT-', 'GPT-');
  }

  return raw;
}

function formatChatModelSelect() {
  if (!chatModelEl) return;
  Array.from(chatModelEl.options).forEach((opt) => {
    const id = String(opt.value || '').trim();
    opt.textContent = prettyModelName(id);
  });
}

function resetChatBriefState() {
  chatBriefState.active = false;
  chatBriefState.mode = '';
  chatBriefState.baseRequest = '';
  chatBriefState.questions = [];
  chatBriefState.answers = {};
  chatBriefState.index = 0;
  chatBriefState.context = null;
}

function normalizedBriefQuestions(items) {
  if (!Array.isArray(items)) return [];
  return items
    .map((item, idx) => {
      if (!item) return null;
      if (typeof item === 'string') {
        return { key: `question_${idx + 1}`, question: item.trim() };
      }
      if (typeof item === 'object') {
        const key = String(item.key || `question_${idx + 1}`)
          .trim()
          .toLowerCase()
          .replace(/[^\w]+/g, '_');
        const question = String(item.question || '').trim();
        return question ? { key, question } : null;
      }
      return null;
    })
    .filter(Boolean);
}

function fallbackGenerateBriefQuestions() {
  return [
    { key: 'audience', question: 'Who exactly is this for?' },
    { key: 'goal', question: 'What should this post achieve?' },
    { key: 'proof', question: 'Any story, example, or proof to include?' },
    { key: 'constraints', question: 'Any constraints (tone, length, phrases to avoid, CTA)?' },
  ];
}

function askNextBriefQuestion() {
  const q = chatBriefState.questions[chatBriefState.index];
  if (!q) return;
  const current = chatBriefState.index + 1;
  const total = chatBriefState.questions.length;
  appendChatMessage('assistant', `Brief question ${current}/${total}: ${q.question}`);
}

async function startBriefingFlow(mode, userRequest, context) {
  const out = await postJson('/api/brief/questions', {
    mode,
    user_request: userRequest,
    platform: context.platform,
    model: context.model,
    max_questions: 4,
  });
  const questions = normalizedBriefQuestions(out?.questions);
  const finalQuestions = questions.length ? questions : fallbackGenerateBriefQuestions();

  chatBriefState.active = true;
  chatBriefState.mode = mode;
  chatBriefState.baseRequest = userRequest;
  chatBriefState.questions = finalQuestions;
  chatBriefState.answers = {};
  chatBriefState.index = 0;
  chatBriefState.context = { ...context };

  appendChatMessage(
    'assistant',
    "Perfect. I’ll ask a few quick brief questions first so the draft is exactly what you want. Reply one answer at a time. Type `/skipbrief` to skip.",
  );
  askNextBriefQuestion();
}

function buildBriefedGenerateInput(baseRequest, answers) {
  const sections = [`Original request: ${baseRequest}`];
  const ordered = [
    ['audience', 'Audience'],
    ['goal', 'Goal'],
    ['proof', 'Proof/Examples'],
    ['constraints', 'Constraints'],
    ['tone', 'Tone'],
    ['cta_goal', 'CTA goal'],
  ];
  ordered.forEach(([key, label]) => {
    const value = String(answers[key] || '').trim();
    if (value) sections.push(`${label}: ${value}`);
  });

  Object.entries(answers).forEach(([k, v]) => {
    if (ordered.find((o) => o[0] === k)) return;
    const text = String(v || '').trim();
    if (text) sections.push(`${k}: ${text}`);
  });

  return sections.join('\n');
}

async function finalizeBriefAndGenerate() {
  const context = { ...(chatBriefState.context || CHAT_DEFAULT_CONTEXT) };
  const answers = chatBriefState.answers || {};
  if (answers.audience) context.audience = String(answers.audience).trim();
  if (answers.goal) context.goal = String(answers.goal).trim();
  if (answers.platform) context.platform = String(answers.platform).trim();
  if (answers.cta_goal) context.cta_goal = String(answers.cta_goal).trim();
  context.reference_content = [answers.proof, answers.constraints, answers.tone].filter(Boolean).join('\n');

  const enrichedInput = buildBriefedGenerateInput(chatBriefState.baseRequest, answers);
  appendChatMessage('system', 'Thanks. Generating draft from your brief...');

  const thinking = appendChatMessage('system', 'Working on it...');
  const payload = await runModeRequest('generate', enrichedInput, context);
  thinking?.remove();

  appendChatMessage(
    'assistant',
    renderModePayload('generate', payload, {
      compact: true,
      original_text: enrichedInput,
      source_text: enrichedInput,
      topic: chatBriefState.baseRequest,
      audience: context.audience,
      goal: context.goal,
      model: context.model,
    }),
    true,
  );
  const draft = primaryDraftFromResponse('generate', payload);
  if (draft) {
    const scoreSummary = payload?.scores ? `Scores: ${JSON.stringify(payload.scores)}` : '';
    updateLinkedinPreview(draft, scoreSummary);
  }

  resetChatBriefState();
}

function setChatPlaceholderByMode(mode) {
  if (!chatInputEl) return;
  const map = {
    generate: 'Describe what you want. Enzo will ask brief questions before drafting.',
    rewrite: 'Paste draft to rewrite in your voice.',
    expand: 'Paste short content to expand into long-form.',
    plan: 'Enter one topic to build a multi-week plan.',
    topic_map: 'Enter one topic to map angles, hooks, and frameworks.',
    calendar: 'Enter one topic to generate date-based schedule.',
    repurpose: 'First line = topic, then paste source content below.',
  };
  chatInputEl.placeholder = map[mode] || map.generate;
}

chatModeEl?.addEventListener('change', () => {
  resetChatBriefState();
  setChatPlaceholderByMode(chatModeEl.value);
});
setChatPlaceholderByMode(chatModeEl?.value || 'generate');
formatChatModelSelect();

chatPlusBtnEl?.addEventListener('click', (e) => {
  e.stopPropagation();
  chatPlusMenuEl?.classList.toggle('hidden');
});

chatAttachBtnEl?.addEventListener('click', () => {
  chatPlusMenuEl?.classList.add('hidden');
  chatFileInputEl?.click();
});

document.addEventListener('click', (e) => {
  if (!(e.target instanceof Element)) return;
  if (e.target.closest('#chatPlusMenu') || e.target.closest('#chatPlusBtn')) return;
  chatPlusMenuEl?.classList.add('hidden');
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') chatPlusMenuEl?.classList.add('hidden');
});

chatFileInputEl?.addEventListener('change', () => {
  const count = chatFileInputEl.files ? chatFileInputEl.files.length : 0;
  if (chatFileStatusEl) chatFileStatusEl.textContent = count > 0 ? `${count} file(s) ready` : 'No files attached';
});

document.querySelectorAll('.quick-action').forEach((btn) => {
  btn.addEventListener('click', () => {
    resetChatBriefState();
    const mode = btn.getAttribute('data-chat-mode') || 'generate';
    if (chatModeEl) chatModeEl.value = mode;
    setChatPlaceholderByMode(mode);
    chatInputEl?.focus();
  });
});

function normalizeModeFromInput(rawMode, text) {
  const m = String(text || '').trim().match(/^\/([a-z_]+)\s+([\s\S]*)$/i);
  if (!m) return { mode: rawMode, text: String(text || '') };
  const alias = m[1].toLowerCase();
  const modeMap = {
    rewrite: 'rewrite',
    generate: 'generate',
    expand: 'expand',
    plan: 'plan',
    topic: 'topic_map',
    topic_map: 'topic_map',
    calendar: 'calendar',
    repurpose: 'repurpose',
  };
  return { mode: modeMap[alias] || rawMode, text: m[2] || '' };
}

function defaultPromptForMode(mode) {
  const map = {
    generate: 'Create a strong publish-ready draft from my style profile and available sources.',
    rewrite: 'Rewrite my draft so it sounds more like me, with clearer flow and stronger hook.',
    expand: 'Expand this idea into a structured long-form draft with sections and examples.',
    plan: 'Build a practical content series from this topic.',
    topic_map: 'Map key angles and hooks from this topic.',
    calendar: 'Create a weekly publishing plan for this topic.',
    repurpose: 'Repurpose this idea for multiple content formats.',
  };
  return map[mode] || map.generate;
}

async function ingestChatFiles() {
  const files = chatFileInputEl?.files ? Array.from(chatFileInputEl.files) : [];
  if (!files.length) return { uploaded: 0, failed: 0 };
  let uploaded = 0;
  let failed = 0;
  for (const file of files) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('author_type', 'mine');
    fd.append('status', 'draft');
    fd.append('source_type', 'uploaded_file');
    fd.append('platform', CHAT_DEFAULT_CONTEXT.platform);
    fd.append('content_type', 'post');
    fd.append('run_in_background', 'true');
    fd.append('allow_duplicate', 'false');
    const res = await requestJson('/api/ingest/file', { method: 'POST', headers: apiHeaders(), body: fd });
    if (res.error) failed += 1;
    else uploaded += 1;
  }
  return { uploaded, failed };
}

async function runModeRequest(mode, text, context) {
  if (mode === 'rewrite') {
    return postJson('/api/rewrite', {
      content: text,
      platform: context.platform,
      goal: context.goal,
      audience: context.audience,
      sound_more_like_me: 0.9,
      creator_inspiration: '',
      model: context.model,
    });
  }
  if (mode === 'generate') {
    return postJson('/api/generate', {
      topic: text,
      platform: context.platform,
      audience: context.audience,
      goal: context.goal,
      cta_goal: String(context.cta_goal || 'engagement'),
      reference_content: String(context.reference_content || ''),
      model: context.model,
    });
  }
  if (mode === 'expand') {
    return postJson('/api/expand', {
      content: text,
      target_format: 'Newsletter',
      audience: context.audience,
      goal: 'depth',
      model: context.model,
    });
  }
  if (mode === 'plan') {
    return postJson('/api/plan', {
      topic: text,
      platform: context.platform,
      audience: context.audience,
      goal: context.goal,
      weeks: 4,
      posts_per_week: 3,
    });
  }
  if (mode === 'topic_map') {
    return postJson('/api/plan/topic-map', {
      topic: text,
      platform: context.platform,
      audience: context.audience,
      goal: context.goal,
    });
  }
  if (mode === 'calendar') {
    return postJson('/api/plan/calendar', {
      topic: text,
      platform: context.platform,
      audience: context.audience,
      goal: context.goal,
      weeks: 4,
      posts_per_week: 3,
    });
  }
  if (mode === 'repurpose') {
    const lines = String(text || '').split('\n');
    const topic = lines[0] || 'Untitled topic';
    const content = lines.slice(1).join('\n').trim() || text;
    return postJson('/api/repurpose', {
      content,
      topic,
      source_platform: context.platform,
      target_platforms: ['Newsletter', 'Blog', 'Substack'],
      audience: context.audience,
      goal: context.goal,
    });
  }
  return { error: true, detail: `Unsupported mode: ${mode}` };
}

function resetChatComposer(resetFiles = true) {
  if (chatInputEl) chatInputEl.value = '';
  if (resetFiles && chatFileInputEl) chatFileInputEl.value = '';
  if (resetFiles && chatFileStatusEl) chatFileStatusEl.textContent = 'No files attached';
  chatPlusMenuEl?.classList.add('hidden');
}

const chatForm = document.getElementById('chatForm');
chatForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const rawText = chatInputEl?.value || '';
  const hasFiles = !!(chatFileInputEl?.files && chatFileInputEl.files.length > 0);
  const userText = String(rawText || '').trim();
  if (!userText && !hasFiles) return;

  if (chatBriefState.active && chatBriefState.mode === 'generate') {
    const answer = userText;
    if (!answer) return;
    if (/^\/skipbrief$/i.test(answer)) {
      appendChatMessage('user', answer);
      await finalizeBriefAndGenerate();
      resetChatComposer();
      return;
    }

    const current = chatBriefState.questions[chatBriefState.index];
    if (!current) {
      resetChatBriefState();
    } else {
      appendChatMessage('user', answer);
      chatBriefState.answers[current.key] = answer;
      chatBriefState.index += 1;
      resetChatComposer(false);
      if (chatBriefState.index < chatBriefState.questions.length) {
        askNextBriefQuestion();
        return;
      }
      await finalizeBriefAndGenerate();
      return;
    }
  }

  const normalized = normalizeModeFromInput(chatModeEl?.value || 'generate', rawText);
  const mode = normalized.mode;
  const text = normalized.text.trim() || defaultPromptForMode(mode);
  const context = {
    model: String(chatModelEl?.value || ''),
    ...CHAT_DEFAULT_CONTEXT,
  };

  if (chatModeEl) chatModeEl.value = mode;
  appendChatMessage('user', `[${mode} | ${context.model || 'default'}] ${text}`);

  if (chatFileInputEl?.files && chatFileInputEl.files.length > 0) {
    const ingestResult = await ingestChatFiles();
    appendChatMessage('system', `Files ingested: ${ingestResult.uploaded}, failed: ${ingestResult.failed}.`);
  }

  if (mode === 'generate' && !/^\/nobrief\b/i.test(text)) {
    await startBriefingFlow(mode, text, context);
    resetChatComposer();
    return;
  }

  const thinking = appendChatMessage('system', 'Working on it...');
  const payload = await runModeRequest(mode, text, context);
  thinking?.remove();

  appendChatMessage(
    'assistant',
    renderModePayload(mode, payload, {
      compact: true,
      original_text: text,
      source_text: text,
      topic: text,
      audience: context.audience,
      goal: context.goal,
      model: context.model,
    }),
    true,
  );
  const draft = primaryDraftFromResponse(mode, payload);
  if (draft) {
    const scoreSummary = payload?.scores ? `Scores: ${JSON.stringify(payload.scores)}` : '';
    updateLinkedinPreview(draft, scoreSummary);
  }

  resetChatComposer();
});

document.getElementById('copyLinkedinPreview')?.addEventListener('click', async () => {
  if (!currentPreviewText.trim()) return;
  await navigator.clipboard.writeText(currentPreviewText);
  appendChatMessage('system', 'LinkedIn preview copied.');
});

document.getElementById('usePreviewInRewrite')?.addEventListener('click', () => {
  if (!currentPreviewText.trim()) return;
  const field = document.querySelector('#rewriteForm textarea[name="content"]');
  if (field) field.value = currentPreviewText;
  switchToTab('rewrite');
});

appendChatMessage('assistant', 'Choose a mode and prompt. I will return readable cards and update LinkedIn preview.');

/* ---------- Upload / Ingest ---------- */
const fileIngestForm = document.getElementById('fileIngestForm');
fileIngestForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(fileIngestForm);
  if (!fd.get('allow_duplicate')) fd.set('allow_duplicate', 'false');
  if (!fd.get('run_in_background')) fd.set('run_in_background', 'false');
  const res = await requestJson('/api/ingest/file', { method: 'POST', headers: apiHeaders(), body: fd });
  renderJson('sourcesOutput', res);
});

const textIngestForm = document.getElementById('textIngestForm');
textIngestForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(textIngestForm);
  payload.allow_duplicate = payload.allow_duplicate === 'on';
  renderJson('sourcesOutput', await postJson('/api/ingest/text', payload));
});

document.getElementById('refreshSources')?.addEventListener('click', async () => {
  renderJson('sourcesOutput', await getJson('/api/sources'));
});

document.getElementById('refreshJobs')?.addEventListener('click', async () => {
  renderJson('jobsOutput', await getJson('/api/jobs'));
});

document.getElementById('runReindexAll')?.addEventListener('click', async () => {
  renderJson('jobsOutput', await postJson('/api/reindex', { source_id: null }));
});

/* ---------- Explorer ---------- */
const libraryForm = document.getElementById('libraryForm');
libraryForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(libraryForm);
  payload.limit = Number(payload.limit || '200');
  const out = await postJson('/api/query/library', payload);
  setPrettyOutput('explorerOutput', 'explorer', out);
});

const graphQueryForm = document.getElementById('graphQueryForm');
graphQueryForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(graphQueryForm);
  const out = await postJson('/api/query/graph', payload);
  setPrettyOutput('explorerOutput', 'explorer', out);
});

const extractStyleForm = document.getElementById('extractStyleForm');
extractStyleForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(extractStyleForm);
  const out = await postJson('/api/style/extract', payload);
  setPrettyOutput('explorerOutput', 'explorer', out);
});

document.addEventListener('click', async (e) => {
  const target = e.target;
  if (!(target instanceof Element)) return;

  const copyBtn = target.closest('.graph-copy');
  if (copyBtn) {
    const creator = attrDecode(copyBtn.getAttribute('data-creator'));
    const pattern = attrDecode(copyBtn.getAttribute('data-pattern'));
    const relation = attrDecode(copyBtn.getAttribute('data-relation'));
    const line = `${creator} | ${pattern} | ${relation}`;
    await navigator.clipboard.writeText(line);
    appendChatMessage('system', `Copied pattern: ${line}`);
    return;
  }

  const genBtn = target.closest('.graph-use-generate');
  if (genBtn) {
    const creator = attrDecode(genBtn.getAttribute('data-creator'));
    const pattern = attrDecode(genBtn.getAttribute('data-pattern'));
    const topicField = document.querySelector('#generateForm input[name="topic"]');
    const refField = document.querySelector('#generateForm textarea[name="reference_content"]');
    if (topicField && !String(topicField.value || '').trim()) {
      topicField.value = pattern;
    }
    if (refField) {
      refField.value = `Apply ${pattern} style inspired by ${creator}.`;
    }
    switchToTab('generate');
    return;
  }

  const rewriteBtn = target.closest('.graph-use-rewrite');
  if (rewriteBtn) {
    const creator = attrDecode(rewriteBtn.getAttribute('data-creator'));
    const pattern = attrDecode(rewriteBtn.getAttribute('data-pattern'));
    const inspField = document.querySelector('#rewriteForm input[name="creator_inspiration"]');
    if (inspField) {
      inspField.value = `${creator} — ${pattern}`;
    }
    switchToTab('rewrite');
  }
});

/* ---------- Rewrite ---------- */
const rewriteForm = document.getElementById('rewriteForm');
rewriteForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(rewriteForm);
  payload.sound_more_like_me = Number(payload.sound_more_like_me || '0.8');
  const response = await postJson('/api/rewrite', payload);
  setPrettyOutput('rewriteOutput', 'rewrite', response, { original_text: payload.content, model: payload.model });
  if (!response?.error) updateLinkedinPreview(response.rewritten_version || '', `Scores: ${JSON.stringify(response.scores || {})}`);

  const compare = document.getElementById('rewriteCompare');
  if (compare) {
    compare.innerHTML = `
      <div class="card"><h3>Original</h3><pre>${esc(payload.content)}</pre></div>
      <div class="card"><h3>Rewritten</h3><pre>${esc(response.rewritten_version)}</pre></div>
      <div class="card"><h3>Concise</h3><pre>${esc(response.more_concise)}</pre></div>
      <div class="card"><h3>Punchy</h3><pre>${esc(response.more_punchy)}</pre></div>
      <div class="card"><h3>Scores</h3><pre>${esc(JSON.stringify(response.scores || {}, null, 2))}</pre></div>
      <div class="card"><h3>Hooks</h3><pre>${esc(JSON.stringify(response.stronger_hooks || [], null, 2))}</pre></div>
    `;
  }
});

/* ---------- Generate ---------- */
const generateForm = document.getElementById('generateForm');
generateForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(generateForm);
  const out = await postJson('/api/generate', payload);
  setPrettyOutput('generateOutput', 'generate', out, {
    topic: payload.topic,
    audience: payload.audience,
    goal: payload.goal,
    model: payload.model,
  });
  if (!out?.error) updateLinkedinPreview(out.final_draft || '', `Scores: ${JSON.stringify(out.scores || {})}`);
});

/* ---------- Expand ---------- */
const expandForm = document.getElementById('expandForm');
expandForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(expandForm);
  const out = await postJson('/api/expand', payload);
  setPrettyOutput('expandOutput', 'expand', out, { source_text: payload.content, model: payload.model });
});

/* ---------- Planner ---------- */
const planForm = document.getElementById('planForm');
planForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(planForm);
  payload.weeks = Number(payload.weeks || '4');
  payload.posts_per_week = Number(payload.posts_per_week || '3');
  const out = await postJson('/api/plan', payload);
  setPrettyOutput('planOutput', 'plan', out);
});

const topicMapForm = document.getElementById('topicMapForm');
topicMapForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(topicMapForm);
  const out = await postJson('/api/plan/topic-map', payload);
  setPrettyOutput('planOutput', 'topic_map', out);
});

const calendarForm = document.getElementById('calendarForm');
calendarForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(calendarForm);
  payload.weeks = Number(payload.weeks || '4');
  payload.posts_per_week = Number(payload.posts_per_week || '3');
  const out = await postJson('/api/plan/calendar', payload);
  setPrettyOutput('planOutput', 'calendar', out);
});

const repurposeForm = document.getElementById('repurposeForm');
repurposeForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(repurposeForm);
  payload.target_platforms = String(payload.target_platforms || '')
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean);
  const out = await postJson('/api/repurpose', payload);
  setPrettyOutput('planOutput', 'repurpose', out);
});

const styleMixForm = document.getElementById('styleMixForm');
const loadCreatorsBtn = document.getElementById('loadCreatorsBtn');
const creatorListHint = document.getElementById('creatorListHint');

loadCreatorsBtn?.addEventListener('click', async () => {
  const out = await getJson('/api/creators');
  const creators = Array.isArray(out?.creators) ? out.creators : [];
  if (creatorListHint) {
    creatorListHint.textContent = creators.length
      ? `Available creators: ${creators.join(', ')}`
      : 'No creators found in current graph.';
  }
  if (!styleMixForm || !creators.length) return;
  const field = styleMixForm.querySelector('textarea[name="creator_weights_text"]');
  if (field && !String(field.value || '').trim()) {
    if (creators.length === 1) field.value = `${creators[0]}=100`;
    else field.value = `${creators[0]}=70\n${creators[1]}=30`;
  }
});

styleMixForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(styleMixForm);
  const creatorWeights = parseCreatorWeights(payload.creator_weights_text || '');
  const out = await postJson('/api/style/mix', {
    topic: payload.topic,
    platform: payload.platform || 'LinkedIn',
    audience: payload.audience || 'general',
    goal: payload.goal || 'authority',
    mode: payload.mode || 'generate',
    content: payload.content || '',
    model: payload.model || '',
    creator_weights: creatorWeights,
  });
  setPrettyOutput('planOutput', 'style_mix', out, { topic: payload.topic, model: payload.model });
  const draft = out?.final_text || '';
  if (draft) {
    const scoreSummary = out?.output?.scores ? `Scores: ${JSON.stringify(out.output.scores)}` : 'Creator style mix applied';
    updateLinkedinPreview(draft, scoreSummary);
  }
});

const performanceIngestForm = document.getElementById('performanceIngestForm');
performanceIngestForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(performanceIngestForm);
  let metadata = {};
  try {
    metadata = payload.metadata_json ? JSON.parse(payload.metadata_json) : {};
  } catch (_err) {
    metadata = { parse_error: true, raw: payload.metadata_json };
  }
  const out = await postJson('/api/performance/ingest', {
    platform: payload.platform || 'LinkedIn',
    hook_text: payload.hook_text,
    views: Number(payload.views || 0),
    likes: Number(payload.likes || 0),
    comments: Number(payload.comments || 0),
    shares: Number(payload.shares || 0),
    topic: payload.topic || null,
    creator_name: payload.creator_name || null,
    metadata,
  });
  setPrettyOutput('planOutput', 'performance_ingest', out);
});

const performanceSummaryForm = document.getElementById('performanceSummaryForm');
performanceSummaryForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(performanceSummaryForm);
  const out = await postJson('/api/performance/summary', {
    platform: payload.platform || null,
    limit: Number(payload.limit || 10),
  });
  setPrettyOutput('planOutput', 'performance_summary', out);
});

/* ---------- Settings ---------- */
const phraseRuleForm = document.getElementById('phraseRuleForm');
phraseRuleForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(phraseRuleForm);
  payload.weight = Number(payload.weight || '1.0');
  renderJson('settingsOutput', await postJson('/api/phrase-rules', payload));
});

const saveSettingsForm = document.getElementById('saveSettingsForm');
saveSettingsForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(saveSettingsForm);
  payload.value = JSON.parse(payload.value || '{}');
  renderJson('settingsOutput', await postJson('/api/settings', payload));
});

const authTokenForm = document.getElementById('authTokenForm');
if (authTokenForm) {
  const tokenInput = authTokenForm.querySelector('input[name="api_token"]');
  if (tokenInput && localStorage.getItem('creator_api_token')) tokenInput.value = localStorage.getItem('creator_api_token');
}
authTokenForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(authTokenForm);
  const token = String(payload.api_token || '').trim();
  if (token) {
    localStorage.setItem('creator_api_token', token);
    renderJson('settingsOutput', { saved: true, auth_token: 'stored in browser localStorage' });
  } else {
    localStorage.removeItem('creator_api_token');
    renderJson('settingsOutput', { saved: true, auth_token: 'cleared' });
  }
});

const styleControlsForm = document.getElementById('styleControlsForm');
styleControlsForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(styleControlsForm);
  const u = Number(payload.user_voice || 65);
  const c = Number(payload.creator_patterns || 25);
  const p = Number(payload.platform_rules || 10);
  const total = Math.max(1, u + c + p);
  const styleWeighting = {
    user_voice: Number((u / total).toFixed(3)),
    creator_patterns: Number((c / total).toFixed(3)),
    platform_rules: Number((p / total).toFixed(3)),
  };
  const a = await postJson('/api/settings', { key: 'style_weighting', value: styleWeighting });
  const b = await postJson('/api/settings', { key: 'blueprint_preset', value: { name: payload.blueprint_preset } });
  renderJson('settingsOutput', { style_weighting: a, blueprint_preset: b, normalized_weights: styleWeighting });
});

const modelStatusForm = document.getElementById('modelStatusForm');
modelStatusForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  renderJson('settingsOutput', await getJson('/api/model/status'));
});

const notionSyncForm = document.getElementById('notionSyncForm');
notionSyncForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(notionSyncForm);
  renderJson(
    'settingsOutput',
    await postJson('/api/integrations/notion/sync', { payload: JSON.parse(payload.payload || '{}') }),
  );
});

const githubExportForm = document.getElementById('githubExportForm');
githubExportForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = formToObj(githubExportForm);
  renderJson(
    'settingsOutput',
    await postJson('/api/integrations/github/export', { payload: JSON.parse(payload.payload || '{}') }),
  );
});

const neo4jImportForm = document.getElementById('neo4jImportForm');
neo4jImportForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(neo4jImportForm);
  renderJson(
    'settingsOutput',
    await postJson('/api/neo4j/import', {
      clear_existing: !!fd.get('clear_existing'),
      dry_run: !!fd.get('dry_run'),
      force: !!fd.get('force'),
      batch_size: Number(fd.get('batch_size') || 50),
    }),
  );
});
