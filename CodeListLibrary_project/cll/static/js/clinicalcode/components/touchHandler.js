/**
 * TouchHandler
 * @desc Static methods to derive meaningful information from touch input
 * 
 */
export default class TouchHandler {
  /**
   * @desc SwipeContext enum symbol that describes the type of touch/swipe a user has enacted
   */
  static SwipeContext = {
    SwipeUp: Symbol('Up'),
    SwipeRight: Symbol('Right'),
    SwipeDown: Symbol('Down'),
    SwipeLeft: Symbol('Left'),
    Tap: Symbol('Tap'),
  };

  /**
   * getSwipeContext
   * @param {obj} param a dict that can be destructured to describe the start + end positions of a touch input 
   * @returns {Symbol} the swipe context symbol enum
   */
  static getSwipeContext({ startX, startY, endX, endY }) {
    const dx = endX - startX;
    const dy = endY - startY;
    const ax = Math.abs(dx);
    const ay = Math.abs(dy);

    if (ax > ay) {
      return dx > 0 ? this.SwipeContext.SwipeRight : this.SwipeContext.SwipeLeft;
    }

    if (ax < ay) {
      return dy > 0 ? this.SwipeContext.SwipeDown : this.SwipeContext.SwipeUp;
    }

    return this.SwipeContext.Tap;
  }

  /**
   * forceSwipableBody
   * @desc Overrides swipe behaviour to avoid scrolling if body is overflowed
   * @param {boolean} activeSwipe whether the user is currently interacting with the screen
   */
  static forceSwipableBody(activeSwipe) {
    window.document.body.style.overflow = activeSwipe ? 'hidden' : 'unset';
  }
}
