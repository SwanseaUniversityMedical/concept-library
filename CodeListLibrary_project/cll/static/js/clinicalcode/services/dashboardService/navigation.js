/**
 * @desc initialises & manages:
 *  - navigation menu selection;
 *  - events relating to the `.dashboard-nav-toggle` class.
 * 
 * @param {Function|any} callback optionally specify the menu item click handler
 * @param {HTMLElement}  parent   optionally specify the parent `HTMLElement`
 * 
 * @returns {Function} a disposable to clean up the navigation interaction handlers
 */
export const manageNavigation = (callback = (e, ref) => { }, parent = document) => {
  const disposables = [];

  const menuDisposable = createGlobalListener(
    'nav.menu:click',
    '[data-controlledby="navigation"]',
    (e) => {
      const btn = e.target;
      const ref = btn.getAttribute('data-ref');
      if (!stringHasChars(ref)) {
        return;
      }

      callback(e, ref);
    }
  );
  disposables.push(menuDisposable);

  const states = new Map();
  const toggleDisposable = createGlobalListener(
    'nav.toggle:click',
    '[data-controlledby="nav-toggle"] [data-role="toggle"]',
    (e) => {
      const group = tryGetRootElement(e.target, 'dashboard-nav-toggle');
      if (!group) {
        return;
      }

      let state = states.get(group);
      if (typeof state === 'undefined') {
        let toggle = group.getAttribute('data-toggle');
        toggle = stringHasChars(toggle) ? strictSanitiseString(toggle) : null;

        if (!stringHasChars(toggle)) {
          return;
        }

        const relative = parent.querySelector(`[data-ref="${toggle}"]`);
        if (!relative) {
          return;
        }

        state = relative.getAttribute('data-open');
        state = typeof state === 'string'
          ? state.toLowerCase() === 'true'
          : false;

        state = { open: state, relative: relative };
        states.set(group, state);
      }

      state.open = !state.open;
      state.relative.setAttribute('data-open', state.open);
    }
  )
  disposables.push(toggleDisposable);

  return () => {
    let disposable;
    for (let i = disposables.length; i > 0; --i) {
      disposable = disposables.pop();
      if (typeof disposable !== 'function') {
        continue;
      }

      disposable();
    }
  };
};
