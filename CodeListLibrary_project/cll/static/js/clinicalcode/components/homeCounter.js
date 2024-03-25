/***************************************
 *                                     *
 *                Default              *
 *                                     *
 ***************************************/
const
  /**
   * TCA_ANIM_DURATION
   * @desc default target animation duration
   *       for the `::targetCountupAnimation()` method
   * 
   */
  TCA_ANIM_DURATION = 100,
  /**
   * TCA_FPS
   * @desc default target framerate for
   *       the `::targetCountupAnimation()` method
   * 
   */
  TCA_FPS = 120;

/***************************************
 *                                     *
 *              Analytics              *
 *                                     *
 ***************************************/

/**
 * quintIn
 * @desc polynomial easing function - n^5
 * @param {number} t the alpha value
 * @returns {number} the resulting eased value
 * 
 */
const quintIn = t => t * t * t * t * t;

/**
 * quintInOut
 * @desc accelerated/declerated polynomial easing function
 * @param {number} t the alpha value
 * @returns {number} the resulting eased value
 * 
 */
const quintInOut = t => {
  if (t < 0.5) {
    return quintIn(t * 2) / 2;
  }

  return 1 - quintIn((1 - t) * 2) / 2;
}

/**
 * targetCountupAnimation
 * @desc animates the innerText of an element
 *       such that it counts up from 0 to the
 *       element's given `x-value` attribute
 * 
 * @param {node} elem the node to animation
 * @returns {number} the `intervalID` associated with the
 *                   count animation, can be cancelled if required
 * 
 */
const targetCountupAnimation = (elem) => {
  const final = parseInt(elem.getAttribute('x-value'));
  const duration = parseInt(elem.getAttribute('x-duration') || TCA_ANIM_DURATION);
  const fps = 1000 / parseInt(elem.getAttribute('x-fps') || TCA_FPS);
  const frames = Math.round(duration / fps);

  let frame = 0;
  const counter = setInterval(() => {
    frame++;

    const progress = quintInOut(frame / frames);
    const counted = Math.round(final * progress);
    const current = parseInt(elem.innerText);

    if (current !== counted) {
      elem.innerText = `${counted.toLocaleString()}`;
    }

    if (frame >= frames) {
      clearInterval(counter);
    }
  }, duration);

  return counter;
}

/**
 * handleFeaturesSection
 * @desc handles element fade animations for those
 *       with the `fade-item` id tag
 * 
 */
const handleCounterSection = () => {
  document.querySelectorAll('#entity-counter').forEach(e => {
    const init = e.getAttribute('x-init');

    switch (init) {
      case 'countup': {
        if (isScrolledIntoView(e)) {
          targetCountupAnimation(e);
          break;
        }

        elementScrolledIntoView(e).then(() => targetCountupAnimation(e));
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

/**
 * handleFeaturesSection
 * @desc handles element fade animations for those
 *       with the `fade-item` id tag
 * 
 */
const handleFeaturesSection = () => {
  document.querySelectorAll('#fade-item').forEach((e, k) => {
    if (isScrolledIntoView(e)) {
      console.log(e);
      setTimeout(() => {
        e.classList.add('show');
      }, k * 50)
      return;
    }

    e.classList.remove('show');

    elementScrolledIntoView(e)
      .then(() => setTimeout(() => {
        e.classList.add('show');
      }, k * 50));
  });
}


/***************************************
 *                                     *
 *                 Main                *
 *                                     *
 ***************************************/

/**
 * Main thread
 * @desc initialises the page once the dom is ready
 * 
 */
domReady.finally(() => {
  handleCounterSection();
  handleFeaturesSection();
});
