/***************************************
 *                                     *
 *                Default              *
 *                                     *
 ***************************************/
const ANIM_DURATION = 100;
const FPS = 120;


/***************************************
 *                                     *
 *              Analytics              *
 *                                     *
 ***************************************/
const quintIn = t => t * t * t * t * t;
const quintInOut = t => {
  if (t < 0.5) {
    return quintIn(t * 2) / 2;
  }

  return 1 - quintIn((1 - t) * 2) / 2;
}

const countup = (elem) => {
  const final = parseInt(elem.getAttribute('x-value'));
  const duration = parseInt(elem.getAttribute('x-duration') || ANIM_DURATION);
  const fps = 1000 / parseInt(elem.getAttribute('x-fps') || FPS);
  const frames = Math.round(duration / fps);
  
  let frame = 0;
  const counter = setInterval(() => {
    frame++;

    const progress = quintInOut(frame / frames);
    const counted = Math.round(final * progress);
    const current = parseInt(elem.innerHTML);

    if (current !== counted) {
      elem.innerHTML = `${counted}+`;
    }

    if (frame >= frames) {
      clearInterval(counter);
    }
  }, duration);
}

const handleAnalyticsSection = () => {
  document.querySelectorAll('#analytics-counter').forEach(e => {
    const init = e.getAttribute('x-init');
    
    switch (init) {
      case 'countup': {
        if (isScrolledIntoView(e)) {
          countup(e);
          break;
        }
        
        elementScrolledIntoView(e).then(() => countup(e));
      } break;

      /* Other effects? */

      default: break;
    }
  });
}


/***************************************
 *                                     *
 *               Features              *
 *                                     *
 ***************************************/
const handleFeaturesSection = () => {
  document.querySelectorAll('#fade-item').forEach((e, k) => {
    if (isScrolledIntoView(e)) {
      setTimeout(() => {
        e.classList.add('show');
      }, k * 50)
      return;
    }

    elementScrolledIntoView(e).then(() => setTimeout(() => {
      e.classList.add('show');
    }, k * 50));
  });
}


/***************************************
 *                                     *
 *                 Main                *
 *                                     *
 ***************************************/
domReady.finally(() => {
  handleAnalyticsSection();
  handleFeaturesSection();
});
