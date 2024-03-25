/**
 * updateTrackerStyle
 * @desc updates the progress-percentage property of a
 *       progress-item dependent on scroll position
 * 
 * @param {node} navbar the navbar node
 * @param {list} trackers the list of tracker elements to update
 * @param {int} headerOffset the offset of the <header/> element, incl. navigation
 * 
 */
const updateTrackerStyle = (navbar, trackers, headerOffset) => {
  for (let i = 0; i < trackers.length; i++) {
    const tracker = trackers[i];
    const offset = tracker.getBoundingClientRect().y - navbar.getBoundingClientRect().y + headerOffset;
    const size = tracker.offsetHeight;

    let progress = 0;
    if (offset < 0) {
      progress = Math.min((Math.abs(offset) / (size - (size/1.5))) * 100, 100);
    }
    tracker.style.setProperty('--progress-percentage', `${progress}%`);
  }
}

/**
 * resolveWizardStepsArea
 * @desc resolve the wizard step area location
 * @param {node} aside the aside wizard area
 * @param {node} content the content area
 * 
 */
const resolveWizardStepsArea = (aside, content) => {
  const asideRect = aside.getBoundingClientRect();
  const contentRect = content.getBoundingClientRect();
  aside.style.left = `${contentRect.left - asideRect.width * 1.05}px`;
}

/**
 * initStepsWizard
 * @desc initialises the wizard steps form
 * 
 */
const initStepsWizard = () => {
  document.querySelectorAll('.steps-wizard__item').forEach(elem => {
    const trg = elem.getAttribute('data-target');
    const node = document.querySelector(`[id='${trg}']`);
    if (isNullOrUndefined(node)) {
      elem.remove()
      return;
    }

    elem.addEventListener('click', e => {
      if (node) {
        window.scrollTo({ top: node.offsetTop, left: 0, behavior: 'smooth' });
      }
    });
  });

  const elems = Array.from(document.querySelectorAll('.steps-wizard__item'));
  elems.sort((a, b) => {
    a = parseInt(a.getAttribute('data-value')) || Infinity;
    b = parseInt(b.getAttribute('data-value')) || Infinity;

    return a - b;
  });
  elems.forEach((elem, index) => {
    elem.setAttribute('data-value', index + 1);
  });

  const navbar = document.querySelector('.page-navigation');
  const header = document.querySelector('.main-header');
  const trackers = document.querySelectorAll('.phenotype-progress__item');
  document.addEventListener('scroll', e => {
    updateTrackerStyle(navbar, trackers, header ? header.getBoundingClientRect().y / 2 : 0);
  });
  updateTrackerStyle(navbar, trackers, header ? header.getBoundingClientRect().y / 2 : 0);

  const aside = document.querySelector('#steps-wizard-area');
  const content = document.querySelector('#main-wizard');
  if (content) {
    window.addEventListener('resize', () => {
      resolveWizardStepsArea(aside, content);
    });
    resolveWizardStepsArea(aside, content);
  }
}

/**
 * Main thread
 * @desc initialises the component once the dom is ready
 * 
 */
domReady.finally(() => {
  initStepsWizard();
});
