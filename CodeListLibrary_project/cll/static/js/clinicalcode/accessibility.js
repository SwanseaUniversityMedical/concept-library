/**
 * Main thread
 * @desc listens to key events to see if the user has utilised any accessibility keys,
 *       and uses contextual information related to both the element & the keyCode to
 *       determine whether to initialise an interaction with that component
 */
domReady.finally(() => {
  observeMatchingElements('[data-page]', (elem) => {
    if (isNullOrUndefined(elem)) {
      return;
    }

    if (!elem.getAttribute('target') && !elem.getAttribute('href')) {
      elem.setAttribute('target', '_blank');
      elem.setAttribute('href', '#');
    }
  });

  document.addEventListener('keydown', e => {
    const elem = document.activeElement;
    const code = e.code;
    if (!code.endsWith('Enter') || elem.disabled) {
      return;
    }

    if (elem.matches('[role="button"]') || elem.matches('[data-page]')) {
      elem.click();
    } else if (elem.matches('[role="dropdown"]')) {
      const radio = elem.querySelector('input[type="radio"]');
      if (radio && !radio.disabled) {
        radio.checked = !radio.checked;
      }
    } else if (elem.matches('[type="checkbox"]')) {
      elem.click();
    } else if (elem.matches('[role="collapsible"]')) {
      const collapsible = elem.querySelector('input[type="checkbox"]');
      if (collapsible && !collapsible.disabled) {
        collapsible.checked = !collapsible.checked;
      }
    }
  });
});
