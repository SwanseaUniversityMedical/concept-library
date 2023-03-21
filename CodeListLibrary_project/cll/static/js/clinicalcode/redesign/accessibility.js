/**
 * CL_ACCESSIBILITY_KEYS
 * @desc Keycodes used for accessibility on elements
 *       that are not necessarily meant to be accessible by default
 */
const CL_ACCESSIBILITY_KEYS = {
  // Enter, to activate click elements via accessibility readers
  'ENTER': 13,
}

domReady.finally(() => {
  document.addEventListener('keydown', e => {
    const elem = document.activeElement;
    const code = e.keyIdentifier || e.which || e.keyCode;    
    if (code !== CL_ACCESSIBILITY_KEYS.ENTER) {
      return;
    }

    if (elem.matches('[role="button"]')) {
      elem.click();
    } else if (elem.matches('[type="checkbox"]')) {
      elem.checked = !elem.checked;
    } else if (elem.matches('[role="collapsible"]')) {
      const collapsible = elem.querySelector('input[type="checkbox"]');
      console.log(collapsible);
      if (collapsible) {
        collapsible.checked = !collapsible.checked;
      }
    }
  });
});