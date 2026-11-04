"""The redesigned ("preview") layout of the intake form.

The preview is generated from the same workbook, markup, and form script as
the current form; this module only adds presentation on top:

- PREVIEW_CSS restyles the page (outline column, quieter rows, comments
  behind a button, collapsible blocks) and keeps the existing color system.
- PREVIEW_SETUP_JS runs *before* the form script. It adds a comment button to
  every field row and a collapse button to every block banner, including the
  templates later blocks are cloned from. It never touches values, names, or
  rule attributes.
- PREVIEW_UI_JS runs *after* the form script and drives those buttons, the
  outline, and the "needs attention" list.

Rules, units, Apply, save and import therefore behave identically in both
forms, and a file saved in one opens in the other. Two constraints keep it
that way:

- Collapsing uses a CSS class, never an inline `display:none`. The form
  script treats inline-hidden fields as rule-hidden (cleared, not saved), so
  an inline style here would silently drop data.
- Validation is read through `control.validity`, never `checkValidity()`,
  which would fire `invalid` events outside an export.
"""

PREVIEW_CSS = """
body.preview { font-family: "Segoe UI", Arial, Helvetica, sans-serif; background: #eef1f5; }
.preview .preview-note { margin-top: .5rem; display: inline-block; background: #ffffff22; padding: .3rem .6rem; border-radius: 4px; opacity: 1; }
.preview main { max-width: 1440px; display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: 1.25rem; align-items: start; }

/* Outline */
#outline { position: sticky; top: 1rem; max-height: calc(100vh - 7rem); overflow: auto; background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: .75rem; font-size: .85rem; }
#outline h2 { font-size: .95rem; margin: 0 0 .5rem; }
.outline-actions { display: flex; gap: .4rem; margin-bottom: .6rem; }
.outline-actions button { flex: 1; background: #fff; border: 1px solid var(--border); border-radius: 4px; padding: .25rem; cursor: pointer; font-size: .78rem; }
.outline-actions button:hover { background: #f2f4f7; }
#outline ul { list-style: none; margin: 0; padding: 0; }
#outline li ul { padding-left: .9rem; border-left: 2px solid #e3e6ea; margin-left: .35rem; }
#outline a { display: flex; justify-content: space-between; gap: .5rem; padding: .25rem .4rem; border-radius: 4px; color: var(--ink); text-decoration: none; }
#outline a:hover { background: #f2f4f7; }
.badge { flex: 0 0 auto; font-size: .72rem; padding: 0 .4rem; border-radius: 9px; line-height: 1.5; }
.badge.todo { background: #fdecea; color: #a1281c; }
.badge.done { background: #e6f4ea; color: #1e6b34; }
#problems { margin-bottom: .75rem; border: 1px solid #f1b8b2; background: #fdf3f2; border-radius: 6px; padding: .5rem .6rem; }
#problems[hidden] { display: none; }
#problems h3 { margin: 0 0 .35rem; font-size: .85rem; color: #a1281c; }
#problems li a { display: block; padding: .2rem 0; color: #7a1d14; }
#problems li small { display: block; color: #555; }

/* Blocks */
.preview .zone, .preview .completion-instance, .preview .sand-body-instance,
.preview .lateral-instance > .own-fields { border-radius: 8px; box-shadow: 0 1px 2px #0000000f; }
.preview .interval-instance, .preview .zone { scroll-margin-top: 1rem; }
.preview .interval-banner { gap: .25rem; }
/* The whole banner carries the block color, so the arrow and status sit on it. */
.preview .lateral-instance.interval-odd > .interval-banner { background: var(--lat-odd-header); }
.preview .lateral-instance.interval-even > .interval-banner { background: var(--lat-even-header); }
.preview .completion-instance.interval-odd > .interval-banner { background: var(--odd-header); }
.preview .completion-instance.interval-even > .interval-banner { background: var(--even-header); }
.preview .sand-body-instance.interval-odd > .interval-banner { background: var(--sb-odd-header); }
.preview .sand-body-instance.interval-even > .interval-banner { background: var(--sb-even-header); }
.collapse-toggle { margin-left: .5rem; background: transparent; border: none; cursor: pointer; font-size: 1rem; color: var(--banner-text); width: 1.6rem; height: 1.6rem; border-radius: 4px; }
.collapse-toggle:hover { background: #ffffff66; }
.collapsed .collapse-toggle { transform: rotate(-90deg); }
.block-status { margin-right: 1rem; font-size: .78rem; font-weight: 600; color: var(--banner-text); white-space: nowrap; }
.interval-instance.collapsed > :not(.interval-banner) { display: none; }

/* Field rows: label | answer | unit | Apply | comment button; comment below */
.preview .field-row { grid-template-columns: minmax(220px, 1.15fr) minmax(220px, 1.4fr) 10rem auto 2rem; padding: .45rem 1rem; column-gap: .75rem; row-gap: .35rem; }
.preview .field-row > * { grid-row: 1; }
.preview .field-row > .comment-toggle { grid-column: 5; }
.preview .field-row > .field-comment { display: none; grid-row: 2; grid-column: 2 / -1; }
.preview .field-row.comment-open > .field-comment, .preview .field-row.has-comment > .field-comment { display: block; }
.comment-toggle { width: 2rem; height: 2rem; border: 1px solid transparent; border-radius: 4px; background: transparent; cursor: pointer; color: #8896a6; position: relative; padding: 0; }
.comment-toggle:hover { border-color: var(--border); background: #fff; color: var(--ink); }
.comment-toggle svg { width: 1rem; height: 1rem; vertical-align: middle; }
.has-comment > .comment-toggle { color: var(--header-bg); }
.preview .field-name { font-size: .9rem; }
.preview .subcat-title { font-size: .9rem; letter-spacing: .01em; }
.preview .apply-count-btn { padding: .35rem .8rem; }
.preview .nest-heading { color: #2b3a55; }

@media (max-width: 900px) {
  .preview main { grid-template-columns: 1fr; }
  #outline { position: static; max-height: none; }
  .preview .field-row { grid-template-columns: 1fr 2rem; }
  .preview .field-row > * { grid-row: auto; grid-column: 1; }
  .preview .field-row > .field-name { grid-row: 1; }
  .preview .field-row > .comment-toggle { grid-row: 1; grid-column: 2; }
  .preview .field-row > .field-comment { grid-row: auto; grid-column: 1 / -1; }
}
"""

PREVIEW_SETUP_JS = r"""
(function () {
  // Adds the preview's buttons to the static markup and to every template,
  // before the form script clones its first blocks.
  const COMMENT_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 21l1.9-5.4A8 8 0 1 1 21 12z"/></svg>';
  function decorate(root) {
    root.querySelectorAll('.field-row').forEach((row) => {
      if (row.querySelector(':scope > .comment-toggle')) return;
      const name = row.querySelector('[data-param]')?.getAttribute('data-param') || 'this field';
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'comment-toggle';
      button.title = 'Comment on ' + name;
      button.setAttribute('aria-label', 'Comment on ' + name);
      button.innerHTML = COMMENT_ICON;
      row.appendChild(button);
    });
    root.querySelectorAll('.interval-banner').forEach((banner) => {
      if (banner.querySelector(':scope > .collapse-toggle')) return;
      const toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'collapse-toggle';
      toggle.setAttribute('aria-expanded', 'true');
      toggle.setAttribute('aria-label', 'Collapse or expand this block');
      toggle.textContent = '▾';
      const status = document.createElement('span');
      status.className = 'block-status';
      banner.prepend(toggle);
      banner.append(status);
    });
    root.querySelectorAll('template').forEach((template) => decorate(template.content));
  }
  decorate(document);
})();
"""

PREVIEW_UI_JS = r"""
(function () {
  const form = document.getElementById('sand-form');
  const wellSection = document.getElementById('well-section');
  const outlineList = document.getElementById('outline-list');
  const problemsBox = document.getElementById('problems');
  if (!form || !outlineList) return;
  const multi = () => form.classList.contains('multi-lateral');

  function lateralBlocks() { return Array.from(document.querySelectorAll('#laterals-container > .lateral-instance')); }
  function completionBlocks(lateral) {
    return Array.from(lateral.querySelectorAll(':scope > .completion-nest > .completion-intervals-container > .completion-instance'));
  }
  function sandBodyBlocks(completion) {
    return Array.from(completion.querySelectorAll(':scope > .sand-body-nest > .sand-bodies-container > .sand-body-instance'));
  }
  function ownerOf(el) { return el.closest('.interval-instance') || el.closest('.zone'); }

  // A row needs attention when one of its enabled controls is invalid
  // (missing required answer, bad format, or an unapplied counter).
  function rowNeedsAttention(row) {
    return Array.from(row.querySelectorAll('input, select, textarea')).some((control) =>
      !control.classList.contains('field-comment') && !control.disabled && !control.validity.valid);
  }
  function ownRows(block) {
    return Array.from(block.querySelectorAll('.field-row')).filter((row) => ownerOf(row) === block);
  }
  function openCount(block) { return ownRows(block).filter(rowNeedsAttention).length; }

  function setCollapsed(block, collapsed) {
    block.classList.toggle('collapsed', collapsed);
    block.querySelector(':scope > .interval-banner > .collapse-toggle')?.setAttribute('aria-expanded', String(!collapsed));
  }
  function reveal(el) {
    for (let node = el.closest('.interval-instance'); node; node = node.parentElement?.closest('.interval-instance')) {
      setCollapsed(node, false);
    }
  }
  function goTo(target) {
    reveal(target);
    target.scrollIntoView({ block: 'start' });
  }

  function badge(count) {
    const span = document.createElement('span');
    span.className = 'badge ' + (count ? 'todo' : 'done');
    span.textContent = count ? String(count) : '✓';
    span.title = count ? count + ' field(s) still need an answer or a fix' : 'Nothing missing';
    return span;
  }
  function entry(label, target, count, children) {
    const li = document.createElement('li');
    const link = document.createElement('a');
    link.href = '#';
    link.append(document.createTextNode(label), badge(count));
    link.addEventListener('click', (event) => { event.preventDefault(); goTo(target); });
    li.appendChild(link);
    if (children && children.length) {
      const ul = document.createElement('ul');
      ul.append(...children);
      li.appendChild(ul);
    }
    return li;
  }
  function blockLabel(block) {
    const n = block.dataset.intervalIndex;
    if (block.classList.contains('lateral-instance')) return 'Lateral ' + n;
    if (block.classList.contains('completion-instance')) return 'Completion Interval ' + n;
    return 'Sand Body ' + n;
  }
  // "Lateral 2 › Completion Interval 1 › Sand Body 3" for the problems list.
  function pathOf(el) {
    const parts = [];
    for (let node = el.closest('.interval-instance'); node; node = node.parentElement?.closest('.interval-instance')) {
      if (node.classList.contains('lateral-instance') && !multi()) continue;
      parts.unshift(blockLabel(node));
    }
    if (!parts.length) {
      const zone = el.closest('.zone');
      parts.push(zone ? zone.querySelector('.zone-title').textContent : 'Well');
    }
    return parts.join(' › ');
  }

  function updateBlock(block) {
    const status = block.querySelector(':scope > .interval-banner > .block-status');
    if (!status) return;
    // Count this block and everything nested in it, so a collapsed block
    // still says whether something inside it is unfinished.
    const open = Array.from(block.querySelectorAll('.field-row')).filter(rowNeedsAttention).length;
    const text = open ? open + ' to complete' : 'Complete';
    // Writing unchanged text would still count as a DOM change, and the
    // observer below would schedule another refresh -- forever.
    if (status.textContent !== text) status.textContent = text;
  }

  function buildOutline() {
    const items = Array.from(wellSection.querySelectorAll(':scope > .zone')).map((zone) =>
      entry(zone.querySelector('.zone-title').textContent, zone, openCount(zone)));
    lateralBlocks().forEach((lateral) => {
      const own = lateral.querySelector(':scope > .own-fields');
      const intervals = completionBlocks(lateral).map((completion) => entry(blockLabel(completion), completion,
        openCount(completion), sandBodyBlocks(completion).map((sandBody) =>
          entry(blockLabel(sandBody), sandBody, openCount(sandBody)))));
      if (multi()) {
        items.push(entry(blockLabel(lateral), lateral, openCount(lateral), intervals));
      } else {
        items.push(entry('Well Details', own, openCount(lateral)), ...intervals);
      }
    });
    outlineList.replaceChildren(...items);
  }

  // Problems from the last completed-export attempt, kept until fixed.
  let collecting = null, problems = [];
  form.addEventListener('invalid', (event) => {
    reveal(event.target);  // a collapsed block must open so the browser can point at the field
    if (collecting) collecting.push(event.target);
  }, true);
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.file-action-menu[data-mode="complete"] button[data-format]')) return;
    collecting = [];
    setTimeout(() => {
      problems = collecting;
      collecting = null;
      renderProblems();
    }, 0);
  }, true);
  function renderProblems() {
    problems = problems.filter((control) => control.isConnected && !control.disabled && !control.validity.valid);
    const rows = [...new Set(problems.map((control) => control.closest('.field-row')).filter(Boolean))];
    if (!rows.length) { problemsBox.hidden = true; return; }
    const list = document.createElement('ul');
    rows.forEach((row) => {
      const control = problems.find((c) => c.closest('.field-row') === row);
      const li = document.createElement('li');
      const link = document.createElement('a');
      link.href = '#';
      link.textContent = row.querySelector('[data-param]').getAttribute('data-param');
      const where = document.createElement('small');
      where.textContent = pathOf(row) + ' — ' + control.validationMessage;
      link.appendChild(where);
      link.addEventListener('click', (event) => {
        event.preventDefault();
        reveal(row);
        row.scrollIntoView({ block: 'center' });
        control.focus();
      });
      li.appendChild(link);
      list.appendChild(li);
    });
    const title = document.createElement('h3');
    title.textContent = rows.length + (rows.length === 1 ? ' field needs' : ' fields need') + ' attention';
    problemsBox.replaceChildren(title, list);
    problemsBox.hidden = false;
  }

  function refresh() {
    if (!multi()) lateralBlocks().forEach((lateral) => setCollapsed(lateral, false));
    form.querySelectorAll('.field-row').forEach((row) => {
      const comment = row.querySelector('.field-comment');
      row.classList.toggle('has-comment', comment.value !== '');
    });
    form.querySelectorAll('.interval-instance').forEach(updateBlock);
    buildOutline();
    if (problems.length) renderProblems();
  }
  let scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => { scheduled = false; refresh(); });
  }

  form.addEventListener('click', (event) => {
    const commentButton = event.target.closest('.comment-toggle');
    if (commentButton) {
      event.preventDefault();
      const row = commentButton.closest('.field-row');
      const open = !row.classList.contains('comment-open');
      row.classList.toggle('comment-open', open);
      if (open) row.querySelector('.field-comment').focus();
      return;
    }
    const collapseButton = event.target.closest('.collapse-toggle');
    if (collapseButton) {
      event.preventDefault();
      const block = collapseButton.closest('.interval-instance');
      setCollapsed(block, !block.classList.contains('collapsed'));
    }
  });
  document.getElementById('collapse-all').addEventListener('click', () => {
    // A normal well's single lateral has no banner to reopen it from.
    const selector = multi() ? '.interval-instance' : '.completion-instance, .sand-body-instance';
    form.querySelectorAll(selector).forEach((block) => setCollapsed(block, true));
  });
  document.getElementById('expand-all').addEventListener('click', () => {
    form.querySelectorAll('.interval-instance').forEach((block) => setCollapsed(block, false));
  });
  ['input', 'change', 'click'].forEach((type) => form.addEventListener(type, schedule));
  // Import, Apply and the multilateral switch rebuild blocks without input
  // events; watching the DOM keeps the outline current in every case.
  // Only block additions/removals matter; the outline lives outside the form,
  // so rebuilding it does not feed back into this observer.
  new MutationObserver((records) => {
    if (records.some((record) => [...record.addedNodes, ...record.removedNodes]
      .some((node) => node.nodeType === 1 && node.classList.contains('interval-instance')))) schedule();
  }).observe(form, { childList: true, subtree: true });
  document.getElementById('import-file').addEventListener('change', () => setTimeout(schedule, 50));
  refresh();
})();
"""
