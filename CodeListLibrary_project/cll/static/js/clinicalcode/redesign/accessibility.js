/**
 * CL_ACCESSIBILITY_KEYS
 * @desc Keycodes used for accessibility on elements
 *       that are not necessarily meant to be accessible by default
 */
const CL_ACCESSIBILITY_KEYS = {
  // Enter, to activate click elements via accessibility readers
  'ENTER': 13,
}

/**
 * Main thread
 * @desc listens to key events to see if the user has utilised any accessibility keys,
 *       and uses contextual information related to both the element & the keyCode to
 *       determine whether to initialise an interaction with that component
 */
domReady.finally(() => {
  document.addEventListener('keydown', e => {
    const elem = document.activeElement;
    const code = e.keyIdentifier || e.which || e.keyCode;    
    if (code !== CL_ACCESSIBILITY_KEYS.ENTER) {
      return;
    }

    if (elem.matches('[role="button"]')) {
      elem.click();
    } else if (elem.matches('[role="dropdown"]')) {
      const radio = elem.querySelector('input[type="radio"]');
      if (radio) {
        radio.checked = !radio.checked;
      }
    } else if (elem.matches('[type="checkbox"]')) {
      elem.checked = !elem.checked;
    } else if (elem.matches('[role="collapsible"]')) {
      const collapsible = elem.querySelector('input[type="checkbox"]');
      if (collapsible) {
        collapsible.checked = !collapsible.checked;
      }
    }
  });
});
