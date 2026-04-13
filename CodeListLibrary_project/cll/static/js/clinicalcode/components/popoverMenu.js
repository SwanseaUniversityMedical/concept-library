/**
 * @desc closes all popover menus except for the specified target
 * 
 * @param {Array<object>}    managed an array of objects defining a set of popover menu item descriptors
 * @param {HTMLElement|null} target  optionally specify a popover menu to ignore
 */
export const closePopovers = (managed, target) => {
  if (!Array.isArray(managed)) {
    return;
  }

  if (!target) {
    for (let i = 0; i < managed.length; ++i) {
      const group = managed[i];
      group.menu.setAttribute('hidden', false);
      group.menu.setAttribute('aria-live', 'off');
      group.menu.setAttribute('aria-hidden', 'true');
      group.toggleBtn.setAttribute('aria-live', 'off');
    }

    return;
  }

  for (let i = 0; i < managed.length; ++i) {
    const group = managed[i];
    if (group.item === target || group.item.contains(target)) {
      continue;
    }

    group.menu.setAttribute('hidden', false);
    group.menu.setAttribute('aria-live', 'off');
    group.menu.setAttribute('aria-hidden', 'true');
    group.toggleBtn.setAttribute('aria-live', 'off');
  }
};

/**
 * @desc initialises & manages events relating to the `.popover-menu` class
 * 
 * @param {object}        param0                    popover behaviour opts
 * @param {HTMLElement}   param0.parent             optionally a HTMLElement in which to find popover menu item(s); defaults to `document`
 * @param {Function|null} param0.callback           optionally specify a callback to be called when a menu item is clicked; defaults to `null`
 * @param {boolean}       param0.observeMutations   optionally specify whether to observe the addition & removal of popover menu items; defaults to `false`
 * @param {boolean}       param0.observeDescendants optionally specify whether to observe the descendant subtree when observing descendants; defaults to `false`
 * 
 * @returns {Function|null} either (a) a cleanup disposable `function`; or (b) a `null` value if no valid menus were found 
 */
export const managePopoverMenu = ({
  parent = document,
  callback = null,
  observeMutations = false,
  observeDescendants = false,
} = {}) => {
  const managed = [];
  const popoverMenus = parent.querySelectorAll('[data-controlledby="popover-menu"]');
  for (let i = 0; i < popoverMenus.length; ++i) {
    const item = popoverMenus[i];
    const menu = item.querySelector('[data-role="menu"]');
    const toggleBtn = item.querySelector('[data-role="toggle"]');
    if (isNullOrUndefined(menu) || isNullOrUndefined(toggleBtn)) {
      continue;
    }

    managed.push({ item, menu, toggleBtn });
  }

  if (!observeMutations && managed.length < 1) {
    return null;
  }

  // Listen to interaction(s)
  const disposables = [];
  const popoverDisposable = createGlobalListener(
    'popover.toggle:click',
    '[data-controlledby="popover-menu"] [data-role="toggle"]',
    (e) => {
      const group = !!e.target ? managed.find(x => e.target === x.toggleBtn) : null;
      if (!group) {
        return;
      }

      const { menu, toggleBtn } = group;
      const disabled = !toggleBtn.disabled ? toggleBtn.getAttribute('disabled') === 'true' : false;
      if (disabled) {
        return;
      }

      e.preventDefault();

      const state = isVisibleObj(menu);
      if (state) {
        menu.setAttribute('hidden', false);
        menu.setAttribute('aria-live', 'off');
        menu.setAttribute('aria-hidden', 'true');
        toggleBtn.setAttribute('aria-live', 'assertive');
      } else {
        menu.setAttribute('aria-live', 'assertive');
        menu.setAttribute('aria-hidden', 'false');
        toggleBtn.setAttribute('aria-live', 'off');
      }
    }
  );
  disposables.push(popoverDisposable);

  // Initialise menu listener (if applicable)
  if (typeof callback === 'function') {
    const menuDisposable = createGlobalListener(
      'popover.toggle:click',
      '[data-controlledby="popover-menu"] [data-role="menu"] [data-role="button"]',
      (e) => {
        const trg = e.target;
        const group = !!trg ? managed.find(x => x.item.contains(trg)) : null;
        if (!group) {
          return;
        }

        const { toggleBtn } = group;
        const disabled = (
          (trg.disabled || toggleBtn.getAttribute('disabled') === 'true') ||
          (!toggleBtn.disabled ? toggleBtn.getAttribute('disabled') === 'true' : false)
        );

        if (disabled) {
          return;
        }

        callback(e, group, (trg) => closePopovers(managed, trg));
      }
    );
    disposables.push(menuDisposable);
  }

  // Blur / Closure interaction(s)
  const blurHandler = (e) => {
    const type = e.type;
    switch (type) {
      case 'click': {
        const trg = e.target;
        if (managed.some(x => x.item.contains(trg))) {
          return;
        }
  
        closePopovers(managed, null);
      } break;

      case 'focusout': {
        closePopovers(managed, e.relatedTarget);
      } break;

      case 'visibilitychange': {
        closePopovers(managed, null);
      } break;

      default:
        break;
    }
  };

  window.addEventListener('click', blurHandler);
  window.addEventListener('focusout', blurHandler);
  document.addEventListener('visibilitychange', blurHandler);

  disposables.push(() => {
    window.removeEventListener('click', blurHandler);
    window.removeEventListener('focusout', blurHandler);
    document.removeEventListener('visibilitychange', blurHandler);
  });

  // Observe addition & removal of menu item(s)
  if (observeMutations) {
    const observer = new MutationObserver((muts) => {
      for (let i = 0; i < muts.length; ++i) {
        const added = muts[i].addedNodes;
        const removed = muts[i].removedNodes;
        for (let j = 0; j < added.length; ++j) {
          const node = added[j]
          if (!isHtmlObject(node) || !node.matches('[data-controlledby="popover-menu"]')) {
            continue;
          }

          const index = managed.findIndex(x => x.item === node);
          if (index < 0) {
            const menu = node.querySelector('[data-role="menu"]');
            const toggleBtn = node.querySelector('[data-role="toggle"]');
            if (isNullOrUndefined(menu) || isNullOrUndefined(toggleBtn)) {
              continue;
            }

            managed.push({ item: node, menu: menu, toggleBtn: toggleBtn });
          }
        }

        for (let j = 0; j < removed.length; ++j) {
          const node = removed[j]
          if (!node.matches('[data-controlledby="popover-menu"]')) {
            continue;
          }

          const index = managed.findIndex(x => x.item === node);
          if (index >= 0) {
            managed.splice(index, 1);
          }
        }
      }
    });

    observer.observe(parent, { subtree: observeDescendants, childList: true });
    disposables.push(() => observer.disconnect());
  }

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
