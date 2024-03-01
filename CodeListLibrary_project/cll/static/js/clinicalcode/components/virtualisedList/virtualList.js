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
   * findBoundary
   * @desc binary search implementation to derive best index in O(logN) time
   * @param {array} list the array to assess
   * @param {any} value the value to compare with each item in the array
   * @param {function} comparator the comparator function
   * @returns {number} the best index
   * 
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
   * getElement
   * @desc returns the element associated with this instance
   * @returns {node} the associated list element
   *  
   */
  getElement() {
    return this.#element;
  }

  /**
   * getComponents
   * @desc returns the components associated with this instance
   * @returns {object} an object containing the components
   *  
   */
  getComponents() {
    return this.#components;
  }

  /**
   * getRenderables
   * @desc returns the currently rendered items
   * @returns {array} an array containing the rendered item(s)
   *  
   */
  getRenderables() {
    return this.#renderables;
  }

  /**
   * getCount
   * @desc returns the total length of the virtual list
   * @returns {number} the length
   * 
   */
  getCount() {
    return this.count;
  }

  /**
   * getItem
   * @desc returns a node, as rendered by the associated renderer,
   *       for that particular index
   * @param {number} index the list index
   * @returns {node} an unattached node
   * 
   */
  getItem(index) {
    let item = this.#computeRenderable(index, this.sizes[index] || this.height);
    item.dataset.key = index;
    return item;
  }

  /**
   * getVisibleIndices
   * @desc computes the visible indices
   * @param {*} offsetY 
   * @returns {array} an array containing the first and last visible indices
   * 
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

  /**
   * getHeight
   * @desc get the height of an element at the given index,
   *       or return get the default height
   * @param {number|null} index an optional index
   *                            returns the elem height if given, otherwise
   *                            will return the default height
   * 
   * @returns {number} the elem / default height
   * 
   */
  getHeight(index) {
    if (typeof(index) === 'number') {
      return this.sizes?.[index] || this.height;
    }

    return this.height;
  }


  /*************************************
   *                                   *
   *               Setter              *
   *                                   *
   *************************************/

  /**
   * setCount
   * @desc sets the virtual list size
   * @param {number} n the size of the list
   * @returns {object} this instance, for chaining
   * 
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
    return this;
  }

  /**
   * setItemHeight
   * @desc sets the height of the item in the list, and recomputes the list
   * @param {number} index the list index associated with the element
   * @param {number} height the height of the elem, as an integer - will be rounded otherwise
   * @returns {object} this instance, for chaining
   * 
   */
  setItemHeight(index, height) {
    height = typeof(height) === 'number' ? Math.round(height) : this.height;
    if (typeof(index) !== 'number') {
      return;
    }

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
   * resizeItems
   * @desc resizes a group of item(s)
   * @param {array[]} itemSizes an 2d array containing the index and height of each item
   * @returns {object} this instance, for chaining
   * 
   */
  resizeItems(itemSizes) {
    if (!Array.isArray(itemSizes)) {
      return this;
    }

    const container = this.#components.contentContainer;
    for (let i =  0; i < itemSizes.length; ++i) {
      let group = itemSizes[i];
      if (!Array.isArray(group)) {
        continue;
      }

      let [ index, height ] = group;
      if (typeof(index) !== 'number' || typeof(height) !== 'number') {
        continue;
      }

      let item = container.querySelector(`[data-key="${index}"]`);
      if (!isNullOrUndefined(item) && 'height' in item.style) {
        item.style.height = `${height}px`;
      }

      this.sizes[index] = height;
    }

    this.#computeCanvasSizes();
    this.#onScrollChanged();
    return this;
  }

  /**
   * setRenderer
   * @desc sets the renderer for the list elements, and forces recomputation
   * @param {callback} fn the renderer
   * @returns {object} this instance, for chaining
   * 
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
   * scrollToIndex
   * @desc attempts to scroll to an element given its list index
   * @param {number} index the list index of the element
   * @returns {object} this instance, for chaining
   * 
   */
  scrollToIndex(index) {
    if (typeof(index) !== 'number') {
      return;
    }

    this.#components.scrollingFrame.scrollTop = this.computedSizes?.[index] || 0;
    return this;
  }

  /**
   * refresh
   * @desc forces a refresh of the entire virtual list
   * @returns {object} this instance, for chaining
   * 
   */
  refresh() {
    clearAllChildren(this.#components.contentContainer);
    this.#onScrollChanged();
    return this;
  }


  /*************************************
   *                                   *
   *               Private             *
   *                                   *
   *************************************/

  /**
   * initialise
   * @desc attempts to intiialise the list given a set of
   *       options associated with the instantiation of this class
   * 
   * @param {object|any|null} options the optional argument(s), will be merged with the default args
   * 
   */
  #initialise(options) {
    options = (typeof(options) === 'object' && !Array.isArray(options)) ? options : { };
    options = mergeObjects(options, Constants.VL_DEFAULT_OPTS);

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
    this.#renderables = [...components.contentContainer.children];
  }

  /**
   * computeCanvasSizes
   * @desc computes the canvas size by incrementally computing the height
   *       through iteratively summing the height of each element
   * 
   * @returns {array} the incremental, computed sizes of the list and its children
   * 
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
   * buildComponents
   * @desc builds the components associated with this instance
   * @returns {object} containing the associated component(s) of this instance
   * 
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
   * onPaint
   * @desc repaints the canvas and updates the renderables
   *       based ont the current scroll position of the canvas
   * 
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

    this.#renderables = [...contentContainer.children];
  }


  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/

  /**
   * onScrollChanged
   * @desc handles the `scroll` signal received from
   *       this instance's scrolling frame, and
   *       throttle defers both (1) the `scrollend`
   *       event dispatch; and (2) the render method
   * 
   * @param {object<Event>} e the associated event
   * 
   */
  #onScrollChanged(e) {
    if (this.#handle) {
      this.#threadGroup.cancel(this.#handle);
    }

    this.#handle = this.#threadGroup.push(this.repaint);
    this.#debouncedScrollEnd(e);
  }

  /**
   * onScrollEnd
   * @desc dispatches the `scrollend` event to inform
   *       listeners that the scrolling has finished
   * 
   * @param {object<Event>} e the associated event
   * 
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
