export const
  /**
   * VL_DEBOUNCE
   * @desc describes debounce time, in ms, before scroll-related events are fired
   * 
   */
  VL_DEBOUNCE = 200,
  /**
   * VL_RENDER_FREQ
   * @desc describes the render step frequency
   * 
   */
  VL_RENDER_FREQ = 1000 / 60,
  /**
   * VL_DEFAULT_OPTS
   * @desc default arguments used for the virtualised list class
   * 
   */
  VL_DEFAULT_OPTS = {
    count: 0,
    height: 0,
    onPaint: (elem, index, height) => { },
    onRender: (index, height) => { },
    overscanLength: 0,
  },
  /**
   * VL_CLASSES
   * @desc defines the classes for each element used within this component
   * 
   */
  VL_CLASSES = {
    topPadding: 'vl-padding-top',
    bottomPadding: 'vl-padding-bottom',
    scrollingFrame: 'vl-scrolling-frame',
    contentContainer: 'vl-content-container',
  };
