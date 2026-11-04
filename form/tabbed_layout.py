"""The tabbed layout of the intake form -- the official form since 2026-11-04.

It is generated from the same workbook, markup, and form script as the
classic layout (form/sand_control_form_classic.html, kept for reference); this
module only adds presentation on top. It stays one scrolling page, with three
additions:

- Nested tabs for the repeated blocks. Laterals (multilateral wells only),
  the Completion Intervals of the selected lateral, and the Sand Bodies of
  the selected interval each get a tab strip; only the selected block of each
  level is shown. Every tab shows how many fields are still missing in that
  block and everything under it.
- A "Form sections" tree on the left that follows the scroll position and
  jumps to any section or block (switching tabs as needed).
- Counts on section headings, tabs, and tree entries: red for required
  fields still missing or invalid (green check when none), yellow for shown
  optional fields still blank. Each count jumps to its next such field, as do
  "Next missing field" (Alt+N) and "Next optional field" (Alt+O) in the
  always-visible bottom bar. A jump continues from
  the field you are in, wraps at the end, opens the right tabs, and flashes
  the field.

Rules, units, counters, save and import behave identically in both layouts,
and a file saved in one opens in the other. Constraints that keep it that way:

- Unselected tabs are hidden with a CSS class, never an inline
  `display:none`. The form script treats inline-hidden fields as rule-hidden
  (cleared, not saved), so an inline style here would silently drop data.
- Tab strips are inserted *beside* each block container, never inside it:
  the form script counts a container's children as its blocks.
- Validation is read through `control.validity`, never `checkValidity()`,
  which would fire `invalid` events outside an export.
"""

TABBED_CSS = """
body.tabbed { font-family: "Segoe UI", Arial, Helvetica, sans-serif; background: #eef1f5; }
.tabbed .tabbed-note { margin-top: .5rem; display: inline-block; background: #ffffff22; padding: .3rem .6rem; border-radius: 4px; opacity: 1; }
.tabbed main { max-width: 1440px; display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 1.25rem; align-items: start; }

/* Form sections tree */
#outline { position: sticky; top: 1rem; max-height: calc(100vh - 7rem); overflow: auto; background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: .75rem .5rem; font-size: .88rem; }
#outline h2 { font-size: .8rem; text-transform: uppercase; letter-spacing: .06em; color: #667; margin: 0 .4rem .5rem; }
#outline-list { list-style: none; margin: 0; padding: 0; }
/* Each entry: name | Required column | Optional column. The columns are fixed,
   so a red count or check is always on the left and yellow always on the right. */
#outline-list li, .outline-cols { display: grid; grid-template-columns: minmax(0, 1fr) 3.4rem 3.4rem; align-items: center; column-gap: .15rem; }
#outline-list li { margin: 1px 0; }
#outline-list .cell { display: flex; justify-content: center; }
.outline-cols { font-size: .7rem; font-weight: 600; color: #889; margin: 0 0 .3rem; }
.outline-cols span { text-align: center; }
.outline-cols span:nth-child(2) { color: #a1281c; }
.outline-cols span:nth-child(3) { color: #7a5a00; }
#outline-list .entry { flex: 1; display: flex; align-items: center; gap: .45rem; padding: .35rem .5rem; border: none; border-left: 3px solid transparent; border-radius: 0 6px 6px 0; background: transparent; color: var(--ink); font: inherit; text-align: left; cursor: pointer; }
#outline-list .entry:hover { background: #f2f4f7; }
#outline-list li.current .entry { background: #e4ecf7; border-left-color: var(--header-bg); font-weight: 600; box-shadow: 0 1px 3px #20386433; }
#outline-list .swatch { flex: 0 0 auto; width: .7rem; height: .7rem; border-radius: 3px; border: 1px solid #0000001f; }
#outline-list .label { flex: 1; }
#outline-list li.group { display: block; margin: .6rem .5rem .2rem; font-size: .72rem; text-transform: uppercase; letter-spacing: .06em; color: #889; }
#problems { margin: 0 .25rem .75rem; border: 1px solid #f1b8b2; background: #fdf3f2; border-radius: 6px; padding: .5rem .6rem; }
#problems[hidden] { display: none; }
#problems h3 { margin: 0 0 .35rem; font-size: .85rem; color: #a1281c; }
#problems ul { list-style: none; margin: 0; padding: 0; }
#problems button { display: block; width: 100%; text-align: left; background: none; border: none; padding: .2rem 0; cursor: pointer; color: #7a1d14; font: inherit; }
#problems small { display: block; color: #555; }

/* Missing-field counts. A count is also a "jump to the next one" button. */
.badge { flex: 0 0 auto; font-size: .72rem; font-weight: 600; padding: 0 .45rem; border-radius: 9px; line-height: 1.55; border: none; font-family: inherit; }
.badge.done { background: #e6f4ea; color: #1e6b34; }
.badge.todo { background: #fdecea; color: #a1281c; cursor: pointer; }
.badge.todo:hover { background: #a1281c; color: #fff; }
.badge.optional { background: #fff1c2; color: #7a5a00; cursor: pointer; }
.badge.optional:hover { background: #b38600; color: #fff; }
.zone-title .badge { margin-left: .6rem; font-size: .75rem; vertical-align: middle; }
.zone-title .badge + .badge { margin-left: .3rem; }
#outline-list .badge { padding: 0 .38rem; }
#outline-list .badge { margin: 0; }

/* Nested tabs */
/* Tabs name the blocks, so the banners go (this beats the current form's
   multilateral rule that shows the lateral banner). */
.tabbed #sand-form .interval-instance > .interval-banner { display: none; }
.tabbed .tab-hidden { display: none !important; }
.tablist { display: flex; flex-wrap: wrap; gap: .3rem; align-items: flex-end; border-bottom: 3px solid var(--tab-line, var(--border)); margin: .5rem 0 0; padding: 0 .25rem; }
.tablist .tablist-label { font-size: .85rem; font-weight: 700; color: #2b3a55; margin: 0 .5rem .45rem 0; white-space: nowrap; }
.tab { display: flex; align-items: center; gap: .45rem; padding: .45rem .85rem; border: 1px solid var(--border); border-bottom: none; border-radius: 7px 7px 0 0; background: #f7f8fa; color: #445; font: inherit; font-size: .88rem; cursor: pointer; border-top: 3px solid var(--tab-color); }
.tab:hover { background: #fff; }
.tab:focus-visible { outline: 2px solid var(--header-bg); outline-offset: 1px; }
.tab[aria-selected="true"] { background: var(--tab-color); color: var(--banner-text); font-weight: 700; padding-bottom: .55rem; }
.tabbed #laterals-container > .lateral-instance, .tabbed .completion-instance, .tabbed .sand-body-instance { border-top-left-radius: 0; border-top-right-radius: 0; margin-top: 0; }
.tabbed #sand-form.multi-lateral .lateral-instance { padding: 0 .75rem .75rem; }
.tabbed .completion-nest > .nest-heading, .tabbed .sand-body-nest > .nest-heading { display: none; }
.tabbed .sand-body-nest { border-left: none; padding: .25rem .75rem .75rem; margin-top: .25rem; }
.tabbed .completion-nest { margin-top: 1rem; }
#sand-form:not(.multi-lateral) > .tablist.for-laterals { display: none; }
#sand-form > .tablist.for-laterals { margin-top: 1.25rem; }

/* A field reached by a jump flashes briefly. */
@keyframes jump-flash { from { box-shadow: inset 0 0 0 3px #e0a100; background: #fff6d5; } to { box-shadow: inset 0 0 0 3px transparent; } }
.tabbed .field-row.jumped { animation: jump-flash 1.6s ease-out; }

/* Next missing / next optional field, at the left of the bottom bar */
#next-missing, #next-optional { display: flex; align-items: center; gap: .5rem; background: #fff !important; color: var(--header-bg) !important; border: 2px solid var(--header-bg) !important; }
#next-optional { margin-right: auto; border-color: #b38600 !important; }
#next-missing:disabled, #next-optional:disabled { opacity: .55; cursor: default; }
#next-missing .badge, #next-optional .badge { font-size: .78rem; }
#next-missing kbd, #next-optional kbd { font-size: .72rem; color: #667; border: 1px solid #ccd; border-radius: 3px; padding: 0 .3rem; background: #f7f8fa; }

/* Shorter answer boxes; the comment box stays as in the current form. */
.tabbed .field-row { grid-template-columns: minmax(220px, 1.3fr) minmax(170px, 300px) 8.5rem 4.75rem minmax(150px, 1fr); }
.tabbed .field-row:has(.multi-number) { grid-template-columns: minmax(220px, 1.3fr) minmax(300px, 420px) 8.5rem 4.75rem minmax(150px, 1fr); }
.tabbed .field-name { font-size: .9rem; }
.tabbed .subcat-title { font-size: .9rem; }
.tabbed .zone, .tabbed .interval-instance { scroll-margin-top: 4rem; }
.tabbed .tablist { scroll-margin-top: 1rem; }

@media (max-width: 900px) {
  .tabbed main { grid-template-columns: 1fr; }
  #outline { position: static; max-height: none; }
}
"""

TABBED_JS = r"""
(function () {
  const form = document.getElementById('sand-form');
  const wellSection = document.getElementById('well-section');
  const lateralsContainer = document.getElementById('laterals-container');
  const tree = document.getElementById('outline-list');
  const problemsBox = document.getElementById('problems');
  if (!form || !tree) return;
  const multi = () => form.classList.contains('multi-lateral');
  const zones = Array.from(wellSection.querySelectorAll(':scope > .zone'));
  const zoneNames = new Map(zones.map((zone) => [zone, zone.querySelector('.zone-title').textContent]));

  function lateralBlocks() { return Array.from(lateralsContainer.children); }
  function completionContainer(lateral) { return lateral.querySelector(':scope > .completion-nest > .completion-intervals-container'); }
  function sandBodyContainer(completion) { return completion.querySelector(':scope > .sand-body-nest > .sand-bodies-container'); }
  function completionBlocks(lateral) { return Array.from(completionContainer(lateral).children); }
  function sandBodyBlocks(completion) { return Array.from(sandBodyContainer(completion).children); }
  function parentBlock(el) { return el.parentElement?.closest('.interval-instance') || null; }
  // The tree entry a field row belongs to: a well zone or its own block.
  function entryOf(el) { return el.closest('.interval-instance') || el.closest('.zone'); }
  function ownFields(block) { return block.classList.contains('sand-body-instance') ? block : block.querySelector(':scope > .own-fields'); }

  const LEVEL_NAMES = { 'lateral-instance': 'Lateral', 'completion-instance': 'Completion Interval', 'sand-body-instance': 'Sand Body' };
  function label(el) {
    if (zoneNames.has(el)) return zoneNames.get(el);
    if (el.classList.contains('lateral-instance') && !multi()) return 'Well Details';
    const level = Object.keys(LEVEL_NAMES).find((name) => el.classList.contains(name));
    return LEVEL_NAMES[level] + ' ' + el.dataset.intervalIndex;
  }
  function blockColor(el) {
    const title = zoneNames.has(el) ? el.querySelector('.zone-title') :
      (ownFields(el).querySelector('.subcat-title') || el.querySelector('.subcat-title'));
    return title ? getComputedStyle(title).backgroundColor : '#ccc';
  }

  // ---- what is missing ----
  // A row needs attention when one of its enabled controls is invalid:
  // a missing required answer, a bad format, or an unapplied counter.
  function rowNeedsAttention(row) {
    return Array.from(row.querySelectorAll('input, select, textarea')).some((control) =>
      !control.classList.contains('field-comment') && !control.disabled && !control.validity.valid);
  }
  function missingRows(scope, ownOnly) {
    return Array.from(scope.querySelectorAll('.field-row'))
      .filter((row) => (!ownOnly || entryOf(row) === scope) && rowNeedsAttention(row));
  }
  // An optional question that is shown and still blank. A rule-hidden
  // question has disabled controls and does not count, nor do counters (they
  // are structure), unit choices, or comments. A multi-number field counts as
  // answered once any of its values is filled in.
  function rowOptionalBlank(row) {
    const control = row.querySelector('[data-kind]');
    if (!control || control.matches('[data-counter]')) return false;
    const inputs = control.matches('input, select, textarea') ? [control] : Array.from(control.querySelectorAll('input'));
    if (!inputs.length || inputs.some((input) => input.disabled || input.required)) return false;
    return inputs.every((input) => input.value === '');
  }
  function optionalRows(scope, ownOnly) {
    return Array.from(scope.querySelectorAll('.field-row'))
      .filter((row) => (!ownOnly || entryOf(row) === scope) && rowOptionalBlank(row));
  }
  function badge(rows, title, compact) {
    const count = rows.length;
    const el = document.createElement(count ? 'button' : 'span');
    el.className = 'badge ' + (count ? 'todo' : 'done');
    el.textContent = count ? (compact ? String(count) : count + ' to fill ↓') : '✓';
    el.title = count ? title + ': ' + count + ' field(s) still need an answer or a fix. Click to go to the next one.' :
      title + ': nothing missing';
    if (count) {
      el.type = 'button';
      el.addEventListener('click', (event) => { event.stopPropagation(); event.preventDefault(); jumpTo(rows); });
    }
    return el;
  }
  // The yellow count of blank optional fields; nothing when there are none.
  function optionalBadge(rows, title, compact) {
    if (!rows.length) return null;
    const el = document.createElement('button');
    el.type = 'button';
    el.className = 'badge optional';
    el.textContent = compact ? String(rows.length) : rows.length + ' optional ↓';
    el.title = title + ': ' + rows.length + ' optional field(s) still blank. Click to go to the next one.';
    el.addEventListener('click', (event) => { event.stopPropagation(); event.preventDefault(); jumpTo(rows); });
    return el;
  }
  // Red (or the green check) and, when any, yellow -- for one scope.
  function countBadges(scope, ownOnly, title, compact) {
    return [badge(missingRows(scope, ownOnly), title, compact),
      optionalBadge(optionalRows(scope, ownOnly), title, compact)].filter(Boolean);
  }

  // ---- tabs ----
  const chosen = new Map(); // block container -> its selected block
  function selectedIn(container) {
    let block = chosen.get(container);
    if (!block || block.parentElement !== container) {
      // Nothing chosen yet, or the chosen block was removed: keep the
      // nearest remaining one in view.
      block = container.lastElementChild && chosen.has(container) ? container.lastElementChild : container.firstElementChild;
      chosen.set(container, block);
    }
    return block;
  }
  // Show a block: select it and every block above it.
  function choose(block) {
    for (let node = block; node; node = parentBlock(node)) chosen.set(node.parentElement, node);
    render();
  }
  function tabStripFor(container, cssClass) {
    let strip = container.previousElementSibling;
    if (!strip || !strip.classList.contains('tablist')) {
      strip = document.createElement('div');
      strip.className = 'tablist ' + cssClass;
      strip.setAttribute('role', 'tablist');
      container.before(strip); // beside the container, never inside it
    }
    return strip;
  }
  // `captionText` names whose blocks these are ("Lateral 2 ›"), so the strip
  // reads as a path into its tabs; `ariaLabel` says the same for screen readers.
  function renderTabs(container, cssClass, captionText, ariaLabel) {
    const strip = tabStripFor(container, cssClass);
    strip.setAttribute('aria-label', ariaLabel);
    const current = selectedIn(container);
    const caption = document.createElement('span');
    caption.className = 'tablist-label';
    caption.textContent = captionText;
    const tabs = Array.from(container.children).map((block) => {
      block.classList.toggle('tab-hidden', block !== current);
      // A focusable element, not a <button>: the tab holds a count button,
      // and a button inside a button is invalid HTML.
      const tab = document.createElement('div');
      tab.className = 'tab';
      tab.tabIndex = 0;
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-selected', String(block === current));
      tab.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(block); }
      });
      tab.style.setProperty('--tab-color', blockColor(block));
      tab.append(document.createTextNode(label(block)), ...countBadges(block, false, label(block)));
      tab.addEventListener('click', () => choose(block));
      return tab;
    });
    strip.style.setProperty('--tab-line', blockColor(current));
    strip.replaceChildren(caption, ...tabs);
    return current;
  }
  // Captions: "Laterals"; then "Lateral 2 ›" over its intervals ("Well ›"
  // for a normal well, which has no laterals to tell apart); then "Lateral 2 ›
  // Completion Interval 1 ›" over its sand bodies (no lateral for a normal well).
  function renderAllTabs() {
    renderTabs(lateralsContainer, 'for-laterals', 'Laterals', 'Laterals');
    lateralBlocks().forEach((lateral) => {
      const owner = multi() ? 'Lateral ' + lateral.dataset.intervalIndex : 'Well';
      renderTabs(completionContainer(lateral), 'for-intervals', owner + ' ›', 'Completion Intervals of ' + owner);
      completionBlocks(lateral).forEach((ci) => {
        const path = (multi() ? owner + ' › ' : '') + 'Completion Interval ' + ci.dataset.intervalIndex;
        renderTabs(sandBodyContainer(ci), 'for-sand-bodies', path + ' ›', 'Sand Bodies of ' + path);
      });
    });
  }

  // ---- form sections tree ----
  function treeItems() {
    const list = zones.map((el) => ({ el, depth: 0 }));
    const base = multi() ? 1 : 0;
    list.push({ group: multi() ? 'Laterals' : 'Wellbore and completion' });
    lateralBlocks().forEach((lateral) => {
      list.push({ el: lateral, depth: 0 });
      completionBlocks(lateral).forEach((completion) => {
        list.push({ el: completion, depth: base });
        sandBodyBlocks(completion).forEach((sandBody) => list.push({ el: sandBody, depth: base + 1 }));
      });
    });
    return list;
  }
  let spied = null;
  function renderTree() {
    tree.replaceChildren(...treeItems().map((item) => {
      const li = document.createElement('li');
      if (!item.el) { li.className = 'group'; li.textContent = item.group; return li; }
      if (item.el === spied) li.className = 'current';
      const entry = document.createElement('button');
      entry.type = 'button';
      entry.className = 'entry';
      entry.style.paddingLeft = (0.5 + item.depth * 1.1) + 'rem';
      const swatch = document.createElement('span');
      swatch.className = 'swatch';
      swatch.style.background = blockColor(item.el);
      const text = document.createElement('span');
      text.className = 'label';
      text.textContent = label(item.el);
      entry.append(swatch, text);
      entry.addEventListener('click', () => goToEntry(item.el));
      // Fixed cells: required (red count or check) left, optional (yellow
      // count, or empty when none) right.
      const required = document.createElement('span');
      required.className = 'cell required';
      required.appendChild(badge(missingRows(item.el, true), label(item.el), true));
      const optional = document.createElement('span');
      optional.className = 'cell optional';
      const yellow = optionalBadge(optionalRows(item.el, true), label(item.el), true);
      if (yellow) optional.appendChild(yellow);
      li.append(entry, required, optional);
      return li;
    }));
  }
  function goToEntry(el) {
    if (el.classList.contains('interval-instance')) {
      choose(el);
      // Land on the tab strip so the selected tab is in view with its block.
      const target = el.classList.contains('lateral-instance') && !multi() ? ownFields(el) : el.parentElement.previousElementSibling;
      target.scrollIntoView({ block: 'start', behavior: 'smooth' });
    } else {
      el.scrollIntoView({ block: 'start', behavior: 'smooth' });
    }
  }

  // Scroll spy: the tree highlights the last section whose top has passed
  // the upper part of the window.
  function spy() {
    const candidates = zones.slice();
    lateralBlocks().forEach((lateral) => {
      if (lateral.classList.contains('tab-hidden')) return;
      candidates.push(lateral);
      completionBlocks(lateral).forEach((ci) => {
        if (ci.classList.contains('tab-hidden')) return;
        candidates.push(ci);
        sandBodyBlocks(ci).forEach((sb) => { if (!sb.classList.contains('tab-hidden')) candidates.push(sb); });
      });
    });
    const line = Math.min(160, window.innerHeight * 0.3);
    let found = candidates[0];
    candidates.forEach((el) => {
      const box = (el.classList.contains('interval-instance') ? ownFields(el) : el).getBoundingClientRect();
      if (box.top <= line) found = el;
    });
    if (found !== spied) {
      spied = found;
      tree.querySelectorAll('li.current').forEach((li) => li.classList.remove('current'));
      renderTree();
      tree.querySelector('li.current')?.scrollIntoView({ block: 'nearest' });
    }
  }

  // ---- jumping to missing fields ----
  // Jumps continue from the last field you were in. It is tracked on focus
  // rather than read from document.activeElement, because clicking a jump
  // button would otherwise move focus to the button first.
  let lastRow = null;
  form.addEventListener('focusin', (event) => {
    const row = event.target.closest('.field-row');
    if (row) lastRow = row;
  });
  // Go to the first of `rows` after the last field you were in, wrapping to
  // the first one; with no field yet, start from the top.
  function jumpTo(rows) {
    if (!rows.length) return;
    const here = lastRow && lastRow.isConnected ? lastRow : null;
    const next = here && rows.find((row) => row !== here &&
      (here.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING));
    goToRow(next || rows[0]);
  }
  function goToRow(row) {
    const block = row.closest('.interval-instance');
    if (block) choose(block);
    row.scrollIntoView({ block: 'center' });
    // An invalid control if there is one (missing or wrong), otherwise the
    // field's first answer box (a blank optional field).
    const controls = Array.from(row.querySelectorAll('input, select, textarea'))
      .filter((c) => !c.classList.contains('field-comment') && !c.classList.contains('unit-select') && !c.disabled);
    (controls.find((c) => !c.validity.valid) || controls[0])?.focus({ preventScroll: true });
    lastRow = row;
    row.classList.remove('jumped');
    void row.offsetWidth; // restart the flash if the same row is reached again
    row.classList.add('jumped');
  }
  function jumpButton(id, title) {
    const button = document.createElement('button');
    button.type = 'button';
    button.id = id;
    button.title = title;
    return button;
  }
  const nextButton = jumpButton('next-missing', 'Go to the next required field still missing or invalid (Alt+N)');
  const nextOptionalButton = jumpButton('next-optional', 'Go to the next optional field still blank (Alt+O)');
  nextButton.addEventListener('click', () => jumpTo(missingRows(form, false)));
  nextOptionalButton.addEventListener('click', () => jumpTo(optionalRows(form, false)));
  document.querySelector('.export-bar').prepend(nextButton, nextOptionalButton);
  document.addEventListener('keydown', (event) => {
    if (!event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.code === 'KeyN') { event.preventDefault(); jumpTo(missingRows(form, false)); }
    if (event.code === 'KeyO') { event.preventDefault(); jumpTo(optionalRows(form, false)); }
  });
  function fillJumpButton(button, count, cssClass, label, doneLabel, keys) {
    const kbd = document.createElement('kbd');
    kbd.textContent = keys;
    const counter = document.createElement('span');
    counter.className = 'badge ' + (count ? cssClass : 'done');
    counter.textContent = count ? String(count) : '✓';
    button.replaceChildren(document.createTextNode(count ? label : doneLabel), counter, kbd);
    button.disabled = !count;
  }
  function renderNextButton() {
    fillJumpButton(nextButton, missingRows(form, false).length, 'todo', 'Next missing field', 'All required fields filled', 'Alt+N');
    fillJumpButton(nextOptionalButton, optionalRows(form, false).length, 'optional', 'Next optional field', 'No optional fields left', 'Alt+O');
  }

  // Each well section heading shows its own count, which also jumps.
  function renderZoneBadges() {
    zones.forEach((zone) => {
      const title = zone.querySelector('.zone-title');
      title.querySelectorAll('.badge').forEach((el) => el.remove());
      title.append(...countBadges(zone, true, zoneNames.get(zone)));
    });
  }

  // ---- export problems ----
  let collecting = null, problems = [];
  form.addEventListener('invalid', (event) => {
    // The browser can only point at a field it can show: open the tabs of
    // the first problem before it tries.
    if (!collecting || collecting.length === 0) {
      const block = event.target.closest('.interval-instance');
      if (block && block.closest('.tab-hidden')) choose(block);
    }
    if (collecting) collecting.push(event.target);
  }, true);
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.file-action-menu[data-mode="complete"] button[data-format]')) return;
    collecting = [];
    setTimeout(() => { problems = collecting; collecting = null; renderProblems(); }, 0);
  }, true);
  function renderProblems() {
    problems = problems.filter((control) => control.isConnected && !control.disabled && !control.validity.valid);
    const rows = [...new Set(problems.map((control) => control.closest('.field-row')).filter(Boolean))];
    if (!rows.length) { problemsBox.hidden = true; return; }
    const list = document.createElement('ul');
    rows.forEach((row) => {
      const control = problems.find((c) => c.closest('.field-row') === row);
      const li = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = row.querySelector('[data-param]').getAttribute('data-param');
      const where = document.createElement('small');
      const path = [];
      for (let node = entryOf(row); node; node = node.classList.contains('interval-instance') ? parentBlock(node) : null) {
        if (!(node.classList.contains('lateral-instance') && !multi() && path.length)) path.unshift(label(node));
      }
      where.textContent = path.join(' › ') + ' — ' + control.validationMessage;
      button.appendChild(where);
      button.addEventListener('click', () => goToRow(row));
      li.appendChild(button);
      list.appendChild(li);
    });
    const title = document.createElement('h3');
    title.textContent = rows.length + (rows.length === 1 ? ' field needs' : ' fields need') + ' attention';
    problemsBox.replaceChildren(title, list);
    problemsBox.hidden = false;
  }

  // ---- refresh ----
  function render() {
    renderAllTabs();
    renderZoneBadges();
    renderTree();
    renderNextButton();
    if (problems.length) renderProblems();
  }
  let scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => { scheduled = false; render(); spy(); });
  }
  ['input', 'change'].forEach((type) => form.addEventListener(type, schedule));
  // Import, counters and the multilateral switch add or remove blocks without
  // input events; watch for exactly that. Rebuilding tabs adds buttons, not
  // blocks, so it does not feed back into this observer.
  new MutationObserver((records) => {
    if (records.some((record) => [...record.addedNodes, ...record.removedNodes]
      .some((node) => node.nodeType === 1 && node.classList.contains('interval-instance')))) schedule();
  }).observe(form, { childList: true, subtree: true });
  document.getElementById('import-file').addEventListener('change', () => setTimeout(schedule, 50));
  let spyQueued = false;
  window.addEventListener('scroll', () => {
    if (spyQueued) return;
    spyQueued = true;
    requestAnimationFrame(() => { spyQueued = false; spy(); });
  }, { passive: true });
  render();
  spy();
})();
"""
