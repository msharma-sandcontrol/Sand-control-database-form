"""The redesigned ("preview") layout of the intake form.

The preview is generated from the same workbook, markup, and form script as
the current form; this module only adds presentation on top. Instead of one
long page, a tree on the left lists every section and block:

    General Information
    Well Specific Information
    Lateral 1                      (shown as "Well Details" for a normal well)
      Completion Interval 1
        Sand Body 1

and the right side shows only the selected item's own fields, with a
clickable path above and Previous/Next buttons below. Each tree entry shows
how many of its fields still need an answer.

Rules, units, Apply, save and import behave identically in both forms, and a
file saved in one opens in the other. Two constraints keep it that way:

- Unselected blocks are hidden with CSS classes, never an inline
  `display:none`. The form script treats inline-hidden fields as rule-hidden
  (cleared, not saved), so an inline style here would silently drop data.
- Validation is read through `control.validity`, never `checkValidity()`,
  which would fire `invalid` events outside an export.
"""

PREVIEW_CSS = """
body.preview { font-family: "Segoe UI", Arial, Helvetica, sans-serif; background: #eef1f5; }
.preview .preview-note { margin-top: .5rem; display: inline-block; background: #ffffff22; padding: .3rem .6rem; border-radius: 4px; opacity: 1; }
.preview main { max-width: 1440px; display: grid; grid-template-columns: 270px minmax(0, 1fr); gap: 1.25rem; align-items: start; }

/* Tree */
#outline { position: sticky; top: 1rem; max-height: calc(100vh - 7rem); overflow: auto; background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: .75rem .5rem; font-size: .88rem; }
#outline h2 { font-size: .8rem; text-transform: uppercase; letter-spacing: .06em; color: #667; margin: 0 .4rem .5rem; }
#outline-list { list-style: none; margin: 0; padding: 0; }
#outline-list li { margin: 1px 0; }
#outline-list button { width: 100%; display: flex; align-items: center; gap: .45rem; padding: .35rem .5rem; border: none; border-left: 3px solid transparent; border-radius: 0 6px 6px 0; background: transparent; color: var(--ink); font: inherit; text-align: left; cursor: pointer; }
#outline-list button:hover { background: #f2f4f7; }
#outline-list button.current { background: #e4ecf7; border-left-color: var(--header-bg); font-weight: 600; box-shadow: 0 1px 3px #20386433; }
#outline-list .swatch { flex: 0 0 auto; width: .7rem; height: .7rem; border-radius: 3px; border: 1px solid #0000001f; }
#outline-list .label { flex: 1; }
#outline-list .group { margin: .6rem .5rem .2rem; font-size: .72rem; text-transform: uppercase; letter-spacing: .06em; color: #889; }
.badge { flex: 0 0 auto; font-size: .72rem; font-weight: 600; padding: 0 .45rem; border-radius: 9px; line-height: 1.55; }
.badge.todo { background: #fdecea; color: #a1281c; }
.badge.done { background: #e6f4ea; color: #1e6b34; }
#problems { margin: 0 .25rem .75rem; border: 1px solid #f1b8b2; background: #fdf3f2; border-radius: 6px; padding: .5rem .6rem; }
#problems[hidden] { display: none; }
#problems h3 { margin: 0 0 .35rem; font-size: .85rem; color: #a1281c; }
#problems ul { list-style: none; margin: 0; padding: 0; }
#problems button { display: block; width: 100%; text-align: left; background: none; border: none; padding: .2rem 0; cursor: pointer; color: #7a1d14; font: inherit; }
#problems small { display: block; color: #555; }

/* Pane: path, the selected item, Previous/Next */
.pane { min-width: 0; }
#pane-head { position: sticky; top: 0; z-index: 10; background: #eef1f5; padding: .25rem 0 .6rem; font-size: .88rem; }
#pane-crumbs { display: flex; flex-wrap: wrap; align-items: center; gap: .35rem; }
#pane-crumbs button { background: none; border: none; padding: 0; color: var(--header-bg); cursor: pointer; font: inherit; text-decoration: underline; }
#pane-crumbs .sep { color: #99a; }
#pane-crumbs strong { color: var(--ink); }
#pane-foot { display: flex; justify-content: space-between; gap: 1rem; margin: 1rem 0 1.5rem; }
#pane-foot button { background: #fff; border: 1px solid var(--border); border-radius: 6px; padding: .55rem .9rem; cursor: pointer; font: inherit; font-size: .9rem; color: var(--header-bg); }
#pane-foot button:hover { border-color: var(--header-bg); }
#pane-foot button[hidden] { visibility: hidden; display: inline-block; }

/* Show only the selected item. Ancestors of a selected block stay rendered
   (the DOM nests them) but show nothing of their own. */
.preview #well-section > .zone:not(.is-current) { display: none; }
.preview #laterals-container .interval-instance:not(.is-current):not(.on-path) { display: none; }
.preview .interval-instance.on-path { border: none !important; box-shadow: none !important; background: transparent !important; margin: 0 !important; padding: 0 !important; }
.preview .interval-instance.on-path > .interval-banner,
.preview .interval-instance.on-path > .own-fields,
.preview .interval-instance.on-path > .completion-nest > .nest-heading,
.preview .interval-instance.on-path > .sand-body-nest > .nest-heading { display: none !important; }
.preview .interval-instance.on-path > .completion-nest,
.preview .interval-instance.on-path > .sand-body-nest { margin: 0 !important; padding: 0 !important; border: none !important; }
.preview .interval-instance.is-current > .completion-nest,
.preview .interval-instance.is-current > .sand-body-nest { display: none; }
.preview .zone, .preview .interval-instance.is-current { margin-bottom: 0; border-radius: 8px; box-shadow: 0 1px 3px #0000001a; }
.preview #sand-form:not(.multi-lateral) .lateral-instance.is-current > .own-fields { margin-top: 0; }

/* Shorter answer boxes; the comment box stays as in the current form. */
.preview .field-row { grid-template-columns: minmax(220px, 1.3fr) minmax(170px, 300px) 8.5rem 4.75rem minmax(150px, 1fr); }
.preview .field-row:has(.multi-number) { grid-template-columns: minmax(220px, 1.3fr) minmax(300px, 420px) 8.5rem 4.75rem minmax(150px, 1fr); }
.preview .field-name { font-size: .9rem; }
.preview .subcat-title { font-size: .9rem; }

@media (max-width: 900px) {
  .preview main { grid-template-columns: 1fr; }
  #outline { position: static; max-height: none; }
}
"""

PREVIEW_UI_JS = r"""
(function () {
  const form = document.getElementById('sand-form');
  const wellSection = document.getElementById('well-section');
  const tree = document.getElementById('outline-list');
  const problemsBox = document.getElementById('problems');
  const crumbs = document.getElementById('pane-crumbs');
  const prevButton = document.getElementById('prev-item');
  const nextButton = document.getElementById('next-item');
  const pane = document.querySelector('.pane');
  if (!form || !tree) return;
  const multi = () => form.classList.contains('multi-lateral');

  function lateralBlocks() { return Array.from(document.querySelectorAll('#laterals-container > .lateral-instance')); }
  function completionBlocks(lateral) {
    return Array.from(lateral.querySelectorAll(':scope > .completion-nest > .completion-intervals-container > .completion-instance'));
  }
  function sandBodyBlocks(completion) {
    return Array.from(completion.querySelectorAll(':scope > .sand-body-nest > .sand-bodies-container > .sand-body-instance'));
  }
  function itemOf(el) { return el.closest('.interval-instance') || el.closest('.zone'); }
  function parentBlock(el) { return el.parentElement?.closest('.interval-instance') || null; }

  function label(el) {
    if (el.classList.contains('zone')) return el.querySelector('.zone-title').textContent;
    const n = el.dataset.intervalIndex;
    if (el.classList.contains('lateral-instance')) return multi() ? 'Lateral ' + n : 'Well Details';
    if (el.classList.contains('completion-instance')) return 'Completion Interval ' + n;
    return 'Sand Body ' + n;
  }
  // The selectable items in reading order, with their tree depth. A normal
  // well's single lateral is "Well Details" and its intervals sit at the top.
  function items() {
    const list = Array.from(wellSection.querySelectorAll(':scope > .zone')).map((el) => ({ el, depth: 0 }));
    const base = multi() ? 1 : 0;
    list.push({ el: null, group: multi() ? 'Laterals' : 'Wellbore and completion' });
    lateralBlocks().forEach((lateral) => {
      list.push({ el: lateral, depth: 0 });
      completionBlocks(lateral).forEach((completion) => {
        list.push({ el: completion, depth: base });
        sandBodyBlocks(completion).forEach((sandBody) => list.push({ el: sandBody, depth: base + 1 }));
      });
    });
    return list;
  }

  // A row needs attention when one of its enabled controls is invalid
  // (missing required answer, bad format, or an unapplied counter).
  function rowNeedsAttention(row) {
    return Array.from(row.querySelectorAll('input, select, textarea')).some((control) =>
      !control.classList.contains('field-comment') && !control.disabled && !control.validity.valid);
  }
  function openCount(el) {
    return Array.from(el.querySelectorAll('.field-row'))
      .filter((row) => itemOf(row) === el && rowNeedsAttention(row)).length;
  }
  function swatchColor(el) {
    const banner = el.classList.contains('zone') ? el.querySelector('.zone-title') :
      (el.querySelector(':scope > .own-fields .subcat-title') || el.querySelector('.subcat-title'));
    return banner ? getComputedStyle(banner).backgroundColor : 'transparent';
  }

  let current = null, currentParent = null;
  function select(el, scroll) {
    current = el;
    currentParent = el.classList.contains('interval-instance') ? parentBlock(el) : null;
    form.querySelectorAll('.is-current, .on-path').forEach((node) => node.classList.remove('is-current', 'on-path'));
    el.classList.add('is-current');
    for (let node = parentBlock(el); node; node = parentBlock(node)) node.classList.add('on-path');
    render();
    if (scroll !== false && pane.getBoundingClientRect().top < 0) pane.scrollIntoView({ block: 'start' });
  }

  function badge(count) {
    const span = document.createElement('span');
    span.className = 'badge ' + (count ? 'todo' : 'done');
    span.textContent = count ? String(count) : '✓';
    span.title = count ? count + ' field(s) still need an answer or a fix' : 'Nothing missing here';
    return span;
  }
  function renderTree(list) {
    const nodes = list.map((item) => {
      const li = document.createElement('li');
      if (!item.el) {
        li.className = 'group';
        li.textContent = item.group;
        return li;
      }
      const button = document.createElement('button');
      button.type = 'button';
      button.style.paddingLeft = (0.5 + item.depth * 1.1) + 'rem';
      if (item.el === current) { button.classList.add('current'); button.setAttribute('aria-current', 'true'); }
      const swatch = document.createElement('span');
      swatch.className = 'swatch';
      swatch.style.background = swatchColor(item.el);
      const text = document.createElement('span');
      text.className = 'label';
      text.textContent = label(item.el);
      button.append(swatch, text, badge(openCount(item.el)));
      button.addEventListener('click', () => select(item.el));
      li.appendChild(button);
      return li;
    });
    tree.replaceChildren(...nodes);
  }
  function renderCrumbs() {
    const path = [];
    for (let node = current; node; node = node.classList.contains('interval-instance') ? parentBlock(node) : null) {
      // A normal well's lateral is not a level the user thinks in.
      if (!(node.classList.contains('lateral-instance') && !multi() && node !== current)) path.unshift(node);
    }
    const parts = [];
    path.forEach((node, i) => {
      if (i) {
        const sep = document.createElement('span');
        sep.className = 'sep';
        sep.textContent = '›';
        parts.push(sep);
      }
      if (node === current) {
        const strong = document.createElement('strong');
        strong.textContent = label(node);
        parts.push(strong);
      } else {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = label(node);
        button.addEventListener('click', () => select(node));
        parts.push(button);
      }
    });
    crumbs.replaceChildren(...parts);
  }
  function renderSteps(list) {
    const steps = list.filter((item) => item.el);
    const i = steps.findIndex((item) => item.el === current);
    const set = (button, item, previous) => {
      button.hidden = !item;
      if (!item) return;
      button.textContent = previous ? '← ' + label(item.el) : label(item.el) + ' →';
      button.onclick = () => select(item.el);
    };
    set(prevButton, steps[i - 1], true);
    set(nextButton, steps[i + 1], false);
  }
  function render() {
    const list = items();
    renderTree(list);
    renderCrumbs();
    renderSteps(list);
    if (problems.length) renderProblems();
  }

  // Problems from the last completed-export attempt, kept until fixed.
  let collecting = null, problems = [];
  form.addEventListener('invalid', (event) => {
    // The browser can only point at a field it can show: open the first
    // problem's section before it tries.
    if (!collecting || collecting.length === 0) {
      const item = itemOf(event.target);
      if (item && item !== current) select(item, false);
    }
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
      const item = itemOf(row);
      const li = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = row.querySelector('[data-param]').getAttribute('data-param');
      const where = document.createElement('small');
      where.textContent = label(item) + ' — ' + control.validationMessage;
      button.appendChild(where);
      button.addEventListener('click', () => {
        select(item, false);
        row.scrollIntoView({ block: 'center' });
        control.focus();
      });
      li.appendChild(button);
      list.appendChild(li);
    });
    const title = document.createElement('h3');
    title.textContent = rows.length + (rows.length === 1 ? ' field needs' : ' fields need') + ' attention';
    problemsBox.replaceChildren(title, list);
    problemsBox.hidden = false;
  }

  function refresh() {
    if (!current || !current.isConnected) {
      // The selected block was removed (Apply, or the multilateral answer):
      // fall back to its parent, or the first lateral.
      select(currentParent && currentParent.isConnected ? currentParent : lateralBlocks()[0], false);
      return;
    }
    render();
  }
  let scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => { scheduled = false; refresh(); });
  }
  ['input', 'change'].forEach((type) => form.addEventListener(type, schedule));
  form.addEventListener('click', (event) => { if (event.target.closest('.apply-count-btn')) schedule(); });
  // Import, Apply and the multilateral switch add or remove blocks without
  // input events; watch for exactly that. The tree lives outside the form,
  // so rebuilding it does not feed back into this observer.
  new MutationObserver((records) => {
    if (records.some((record) => [...record.addedNodes, ...record.removedNodes]
      .some((node) => node.nodeType === 1 && node.classList.contains('interval-instance')))) schedule();
  }).observe(form, { childList: true, subtree: true });
  document.getElementById('import-file').addEventListener('change', () => setTimeout(schedule, 50));
  select(wellSection.querySelector(':scope > .zone'), false);
})();
"""
