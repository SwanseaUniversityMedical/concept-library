import DebouncedTask from './debouncedTask.js';
import DeferredThreadGroup from './deferredThreadGroup.js';
import * as Constants from './constants.js';

/**
 * boundaryComparator
 * @desc default comparator for binary search
 * @param {any} a lhs value to compare
 * @param {any} b rhs value to compare
 * @returns {number} reflecting comparator result
 */
const boundaryComparator = (a, b) => {
  if (a < b) {
    return -1
  } else if (a > b) {
    return 1;
  }

  return 0;
}

/**
 * siblingComparator
 * @desc used to det. closest sibling via binary search
 * @param {number} a lhs value to compare
 * @param {node} b rhs value to compare
 * @returns {number} reflecting comparator result
 */
const siblingComparator = (a, b) => {
  b = b.dataset.key;

  if (a < b) {
    return -1
  } else if (a > b) {
    return 1;
  }

  return 0;
}

/**
 * @class VirtualisedList
 * @desc Class that defines a virtualised list,
 *       used to optimise rendering of large lists
 * 
 *       e.g. as seen in ontology selection list(s) within `./create`
 * 
 */
export default class VirtualisedList extends EventTarget {
  #handle = null;
  #element = null;
  #components = null;
  #threadGroup = null;
  #renderables = [];
  #containerHeight = 0;
  #computeRenderable = (index, height) => { };
  #debouncedScrollEnd = null;

  constructor(element, options) {
    assert(!isNullOrUndefined(element), 'DOM element does not exist')

    super();
    this.#element = element;
    this.#threadGroup = new DeferredThreadGroup(Constants.VL_RENDER_FREQ);
    this.#initialise(options);
  }


  /*************************************
   *                                   *
   *               Static              *
   *                                   *
   *************************************/

  /**
   * 
   * @param {*} list 
   * @param {*} value 
   * @param {*} comparator 
   * @returns 
   */
  static findBoundary(list, value, comparator) {
    comparator = comparator || boundaryComparator;

    let left = 0;
    let right = list.length;
    while (left < right) {
      let index = (left + right) >> 1;
      if (comparator(value, list[index]) > 0) {
        left = index + 1;
        continue;
      }

      right = index;
    }

    return right;
  }


  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/

  /**
   * 
   * @returns 
   */
  getElement() {
    return this.#element;
  }

  /**
   * 
   * @returns 
   */
  getComponents() {
    return this.#components;
  }

  /**
   * 
   * @returns 
   */
  getRenderables() {
    return this.#renderables;
  }

  /**
   * 
   * @returns 
   */
  getCount() {
    return this.count;
  }

  /**
   * 
   * @param {*} index 
   * @returns 
   */
  getItem(index) {
    let item = this.#computeRenderable(index, this.sizes[index] || this.height);
    item.dataset.key = index;
    return item;
  }

  /**
   * 
   * @param {*} offsetY 
   * @returns 
   */
  getVisibleIndices(offsetY) {
    offsetY = (typeof offsetY === 'number' && !isNaN(offsetY)) ? Math.max(0, offsetY) : 0;

    const count = this.count;
    const canvasSizes = this.computedSizes;
    const overscanLength = this.overscanLength;

    const firstIndex = Math.max(0, VirtualisedList.findBoundary(canvasSizes, offsetY));
    const lastIndex = Math.min(count - 1, firstIndex + (Math.ceil(this.#containerHeight / this.height) - 1));

    return [
      Math.max(0, firstIndex - overscanLength),
      Math.min(count - 1, lastIndex + overscanLength),
    ]
  }


  /*************************************
   *                                   *
   *               Setter              *
   *                                   *
   *************************************/

  /**
   * 
   * @param {*} n 
   */
  setCount(n) {
    n = Math.max(0, n);

    const sizes = this.sizes;
    this.count = n;

    let delta = sizes.length - n;
    while (delta-- > 0) {
      sizes.pop();
    }

    while (delta++ < 0) {
      sizes.push(this.height);
    }

    if (n < 1) {
      clearAllChildren(this.#components.contentContainer);
    }

    this.#computeCanvasSizes();
    this.#onScrollChanged();
  }

  /**
   * 
   * @param {*} index 
   * @param {*} height 
   * @returns 
   */
  setItemHeight(index, height) {
    const item = this.#components.contentContainer.querySelector(`[data-key="${index}"]`);
    if (!isNullOrUndefined(item) && 'height' in item.style) {
      item.style.height = `${height}px`;
    }

    this.sizes[index] = height;
    this.#computeCanvasSizes();
    this.#onScrollChanged();
    return this;
  }

  /**
   * 
   * @param {*} fn 
   * @returns 
   */
  setRenderer(fn) {
    this.#computeRenderable = fn;
    this.#computeCanvasSizes();
    this.#onScrollChanged();
    return this;
  }


  /*************************************
   *                                   *
   *               Public              *
   *                                   *
   *************************************/

  /**
   * 
   * @param {*} index 
   * @returns 
   */
  scrollToIndex(index) {
    this.#components.scrollingFrame.scrollTop = this.computedSizes[index] || 0;
    return this;
  }

  /**
   * 
   * @returns
   */
  refresh() {
    clearAllChildren(this.#components.contentContainer);
    this.#onScrollChanged();
  }


  /*************************************
   *                                   *
   *               Private             *
   *                                   *
   *************************************/

  /**
   * 
   * @param {*} options 
   */
  #initialise(options) {
    options = mergeObjects(options || { }, Constants.VL_DEFAULT_OPTS);

    this.count = options.count;
    this.sizes = new Array(this.count).fill(options.height);
    this.height = options.height;
    this.repaint = this.#onPaint.bind(this);
    this.overscanLength = options.overscanLength;

    this.#computeRenderable = options.onRender;
    this.#debouncedScrollEnd = new DebouncedTask(this.#onScrollEnd.bind(this), Constants.VL_DEBOUNCE);

    const components = this.#buildComponent();
    this.#components = components;
    this.#element.appendChild(components.scrollingFrame);
  }

  /**
   * 
   * @returns 
   */
  #computeCanvasSizes() {
    const length = this.count;
    const sizes = this.sizes;
    const computedSizes = this.computedSizes || new Array(length);

    let len = computedSizes.length;
    if (len !== length) {
      len = len - length;
      while (len-- > 0) {
        computedSizes.pop();
      }

      while (len++ < 0) {
        computedSizes.push(0);
      }
    }

    let height = 0;
    for (let i = 0; i <= length; ++i) {
      height += (sizes[i] || 0);
      computedSizes[i] = height;
    }

    if (!this.computedSizes) {
      this.computedSizes = computedSizes;
    }

    return computedSizes;
  }


  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/

  /**
   * 
   * @returns 
   */
  #buildComponent() {
    const element = this.#element;
    const containerHeight = element.offsetHeight;
    this.#containerHeight = containerHeight;

    const resizeObserver = new ResizeObserver(() => {
      this.#containerHeight = element.offsetHeight;
      this.#onScrollChanged();
    });
    resizeObserver.observe(element);
    
    onElementRemoved(element)
      .then(() => {
        resizeObserver.disconnect();
      })
      .catch(console.error);

    const canvasSizes = this.#computeCanvasSizes();
    const canvasHeight = canvasSizes[canvasSizes.length - 1];
    const [ firstIndex, lastIndex ] = this.getVisibleIndices();

    const scrollingFrame = document.createElement('div');
    scrollingFrame.classList.add(Constants.VL_CLASSES.scrollingFrame);
    scrollingFrame.setAttribute('style', 'max-height: 100%; overflow-y: auto; overflow-x: hidden; transform: translateZ(0);');
    scrollingFrame.addEventListener('scroll', this.#onScrollChanged.bind(this));

    const topPadding = document.createElement('div');
    topPadding.classList.add(Constants.VL_CLASSES.topPadding);
    topPadding.setAttribute('style', 'height: 0px !important;');

    const bottomPadding = document.createElement('div');
    bottomPadding.classList.add(Constants.VL_CLASSES.bottomPadding);
    bottomPadding.setAttribute('style', `height: ${canvasHeight}px !important;`);

    const contentContainer = document.createElement('div')
    contentContainer.classList.add(Constants.VL_CLASSES.contentContainer);

    for (let i = firstIndex; i <= lastIndex; ++i) {
      let child = this.getItem(i);
      if (isNullOrUndefined(child)) {
        continue;
      }

      contentContainer.appendChild(child);
    }
    scrollingFrame.append(topPadding, contentContainer, bottomPadding);

    return {
      topPadding: topPadding,
      bottomPadding: bottomPadding,
      scrollingFrame: scrollingFrame,
      contentContainer: contentContainer,
    }
  }

  /**
   * 
   * @returns 
   */
  #onPaint() {
    const {
      scrollingFrame, topPadding,
      bottomPadding, contentContainer
    } = this.#components;

    const offsetY = scrollingFrame.scrollTop;
    const canvasSizes = this.computedSizes;
    const absoluteSize = canvasSizes[canvasSizes.length - 1];

    if (offsetY > absoluteSize) {
      scrollingFrame.scrollTop = absoluteSize - scrollingFrame.clientHeight;
      return;
    }

    const [ firstIndex, lastIndex ] = this.getVisibleIndices(offsetY);
    if (firstIndex > lastIndex) {
      return;
    }

    let height = canvasSizes[firstIndex - 1] || 0;
    topPadding.setAttribute('style', `height: ${height}px !important;`);

    height = absoluteSize - canvasSizes[lastIndex];
    bottomPadding.setAttribute('style', `height: ${height}px !important;`);

    let renderable = { };
    for (let i = firstIndex; i <= lastIndex; ++i) {
      renderable[String(i)] = i;
    }

    let elements = contentContainer.children;
    for (let i = 0; i < elements.length; ++i) {
      let element = elements[i];
      let key = element.dataset.key;
      if (!(key in renderable)) {
        contentContainer.removeChild(element);
        continue;
      }

      delete renderable[key];
    }

    renderable = Object.values(renderable);
    for (let i = 0; i < renderable.length; ++i) {
      elements = contentContainer.children;

      let index = renderable[i];
      let anchor = VirtualisedList.findBoundary(elements, index, siblingComparator);
      anchor = !isNullOrUndefined(anchor) ? elements[anchor] : null;

      if (isNullOrUndefined(anchor)) {
        contentContainer.appendChild(this.getItem(index));
      } else if (index != anchor?.dataset?.key) {
        contentContainer.insertBefore(this.getItem(index), anchor);
      }
    }
    scrollingFrame.scrollTop = offsetY;
  }


  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/

  /**
   * 
   * @param {*} e 
   */
  #onScrollChanged(e) {
    if (this.#handle) {
      this.#threadGroup.cancel(this.#handle);
    }

    this.#handle = this.#threadGroup.push(this.repaint);
    this.#debouncedScrollEnd(e);
  }

  /**
   * 
   * @param {*} e 
   */
  #onScrollEnd(e) {
    this.dispatchEvent(
      new CustomEvent('scrollend', {
        detail: {
          controller: this,
          event: e,
        }
      })
    );
  }
};
