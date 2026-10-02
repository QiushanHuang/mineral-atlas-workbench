(function (root) {
  'use strict';
  const KEYS = ['model', 'photo', 'parameters', 'delivery'];
  const STORAGE_KEY = 'mineral-atlas-editor-workspace-v1';
  const ALIASES = Object.freeze({
    model: 'model', photo: 'photo', parameters: 'parameters', delivery: 'delivery',
    startSection: 'model', modelStudio: 'model', photoEditor: 'photo',
    axesSection: 'parameters', parameterSection: 'parameters',
    saveArea: 'delivery', reviewSection: 'delivery'
  });

  function resolve(value) {
    if (typeof value !== 'string') return null;
    let key = value.startsWith('#') ? value.slice(1) : value;
    try { key = decodeURIComponent(key); } catch (_) { return null; }
    return Object.prototype.hasOwnProperty.call(ALIASES, key) ? ALIASES[key] : null;
  }

  function mount({document, window, onChange} = {}) {
    if (!document || !window || typeof document.querySelectorAll !== 'function') throw new TypeError('工作区导航需要 document 与 window');
    const tabs = new Map(), panels = new Map();
    function collect(selector, attribute, target) {
      for (const element of document.querySelectorAll(selector)) {
        const key = element.getAttribute(attribute);
        if (!KEYS.includes(key)) continue;
        if (target.has(key)) throw new Error(`工作区 ${key} 的 ${attribute} 重复`);
        target.set(key, element);
      }
    }
    collect('[data-workspace-tab]', 'data-workspace-tab', tabs);
    collect('[data-workspace-panel]', 'data-workspace-panel', panels);
    for (const key of KEYS) if (!tabs.has(key) || !panels.has(key)) throw new Error(`缺少工作区 ${key} 的导航按钮或面板`);

    const hash = () => typeof window.location?.hash === 'string' ? window.location.hash : '';
    const initialHash = hash();
    let preference = null;
    try { preference = resolve(window.localStorage.getItem(STORAGE_KEY)); } catch (_) { /* Storage is optional. */ }
    const initialKey = resolve(initialHash) || preference || 'model';
    let activeKey = null;

    function persist(key) {
      try { window.localStorage.setItem(STORAGE_KEY, key); } catch (_) { /* Private/blocked storage must not block navigation. */ }
    }
    function writeHistory(key) {
      if (resolve(hash()) === key) return;
      try {
        if (typeof window.history?.pushState === 'function') {
          window.history.pushState(null, '', '#' + key);
          return;
        }
      } catch (_) { /* A hash navigation is sufficient if History API is unavailable. */ }
      try { window.location.hash = '#' + key; } catch (_) { /* The mounted panels still work. */ }
    }
    function activate(value, {focus = false, updateHistory = true, source = 'api'} = {}) {
      const key = resolve(value);
      if (!key) return false;
      if (key === activeKey) {
        if (focus === true) tabs.get(key).focus({preventScroll: true});
        return false;
      }
      const previousKey = activeKey;
      activeKey = key;
      // Change visibility/accessibility only: keep the exact forms, canvases,
      // histories and annotation nodes mounted and owned by the editor.
      for (const name of KEYS) {
        const selected = name === key, tab = tabs.get(name), panel = panels.get(name);
        tab.setAttribute('role', 'tab');
        tab.setAttribute('aria-selected', String(selected));
        tab.tabIndex = selected ? 0 : -1;
        panel.hidden = !selected;
      }
      persist(key);
      if (updateHistory) writeHistory(key);
      if (focus === true) tabs.get(key).focus({preventScroll: true});
      if (typeof onChange === 'function') onChange({key, previousKey, source});
      return true;
    }

    for (const [key, tab] of tabs) {
      tab.addEventListener('click', event => {
        if (event.defaultPrevented || (event.button !== undefined && event.button !== 0)) return;
        event.preventDefault();
        activate(key, {focus: true, source: 'tab'});
      });
      tab.addEventListener('keydown', event => {
        if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
        if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
        const index = KEYS.indexOf(key);
        const next = {ArrowRight: KEYS[(index + 1) % KEYS.length], ArrowLeft: KEYS[(index + KEYS.length - 1) % KEYS.length], Home: KEYS[0], End: KEYS[KEYS.length - 1]}[event.key];
        if (!next) return;
        event.preventDefault();
        activate(next, {focus: true, source: 'keyboard'});
      });
    }
    for (const link of document.querySelectorAll('[data-workspace-link]')) {
      link.addEventListener('click', event => {
        if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || (event.button !== undefined && event.button !== 0)) return;
        const key = resolve(link.getAttribute('data-workspace-link')) || resolve(link.getAttribute('href'));
        if (!key) return;
        event.preventDefault();
        activate(key, {focus: true, source: 'link'});
      });
    }
    function restore(event) {
      const currentHash = hash();
      // Returning to the original hashless (or unknown-anchor) history entry must
      // restore its original workspace, not today's most recently saved tab.
      const key = resolve(currentHash) || (currentHash === initialHash ? initialKey : null);
      if (key) activate(key, {updateHistory: false, source: event.type});
    }
    window.addEventListener('hashchange', restore);
    window.addEventListener('popstate', restore);
    activate(initialKey, {updateHistory: false, source: 'initial'});
    return {activate, get activeKey() { return activeKey; }};
  }

  const api = {mount};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AtlasEditorNavigation = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
