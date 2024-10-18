import TouchHandler from './touchHandler.js';

/**
 * @class ToastNotificationFactory
 * @desc Instantiable toast factory that handles toast notifications for pages
 *       with snackbar/toast element alerts
 * 
 *       The factory is accessible through the window object via window.ToastFactory
 * 
 * e.g.
  ```js
    window.ToastFactory.push({
      type: 'warning',
      message: 'Some warning message',
      duration: 2000, // 2s
    });
  ```
 */
class ToastNotificationFactory {
  constructor() {
    this.#createContainer();
  }

  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/
  /**
   * getElement
   * @returns {node} the container element assoc. with this factory
   */
  getElement() {
    return this.element;
  }

  /**
   * getElementList
   * @desc gets the list child elements
   * @returns {array} the list of toast elements
   */
  getElementList() {
    return this.list.children;
  }

  /*************************************
   *                                   *
   *               Setter              *
   *                                   *
   *************************************/
  /**
   * push
   * @desc Pushes a toast notification to the notification container
   * @param {dict} param a dict that can be destructured to contain a type, message and duration
   *                     of a toast notification 
   * @returns {node} the computed toast node
   */
  push({ type, message, duration }) {
    // Do we want to add handlers for priority and/or num. active toasts?
    return this.#createToast(type, message, duration);
  }

  /**
   * pop
   * @desc Pops a toast notification from the notification container
   * @param {node} toast 
   */
  pop(toast) {
    this.#handleClosure(toast);
  }

  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/
  /**
   * createContainer
   * @desc initialisation method to create the toast notification container
   */
  #createContainer() {
    this.element = createElement('div', {
      className: 'toast-container',
    });

    this.list = createElement('div', {
      className: 'toast-container__list',
    });

    this.element.appendChild(this.list);    
    document.body.prepend(this.element);
  }

  /**
   * createToast
   * @desc creates a toast notification
   * @param {string} type the type of toast notification as defined by its SCSS file
   * @param {string} content the content of the toast message, can be HTML
   * @param {integer} duration the duration of the toast in ms, if < 0 then the toast will not close until
   *                           the user clicks the close button and/or swipes right on the notification
   * @returns {node} the toast notification
   */
  #createToast(type, content, duration) {
    const toast = createElement('div', {
      'className': `toast toast--${type}`,
      'role': 'alert',
      'aria-hidden': false,
      'aria-live': true,
    });

    const element = createElement('div', {
      'className': 'toast__message',
      'innerText': content
    });
    toast.appendChild(element);

    const button = createElement('span', {
      'className': 'toast__close',
      'aria-label': 'Close Notification',
      'role': 'button',
      'tabindex': 0,
    })
    toast.appendChild(button);
    button.addEventListener('click', (e) => this.#handleClosure(toast));

    let progressBar;
    if (!isNullOrUndefined(duration) && duration > 0) {
      progressBar = createElement('div', {
        className: `toast__progress`,
      });
      progressBar.style.setProperty('--toast-duration', `${duration}ms`);
      progressBar.onanimationend = () => this.#handleClosure(toast);
      toast.appendChild(progressBar);
    }
    
    return this.#display(toast);
  }

  /**
   * display
   * @desc initialises the toast's touch handler & appends to the notification centre
   * @param {node} toast the toast node
   * @returns {node} the toast node
   */
  #display(toast) {
    toast.classList.add('toast--active');
    this.list.appendChild(toast);
    this.#handleTouchEvents(toast);

    return toast;
  }

  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/
  /**
   * handleClosure
   * @desc initialises closure of the toast notification, and removes it once its animation completes
   * @param {node} toast the toast node
   */
  #handleClosure(toast) {
    toast.classList.remove('toast--active');
    toast.addEventListener('animationend', e => {
      if (e.target === toast) {
        toast.remove();
      }
    })
  }

  /**
   * handleTouchEvents
   * @desc initialises the touch event handling via TouchHandler for this toast element
   * @param {node} toast the toast node
   */
  #handleTouchEvents(toast) {
    let touch = {
      startX: 0,
      startY: 0,
      endX: 0,
      endY: 0,
    };

    toast.addEventListener('touchstart', (e) => {
      TouchHandler.forceSwipableBody(true);

      const { screenX, screenY } = e.changedTouched[0];
      touch.startX = screenX;
      touch.startY = screenY;
    }, { passive: true });

    toast.addEventListener('touchend', (e) => {
      TouchHandler.forceSwipableBody(false);

      const { screenX, screenY } = e.changedTouched[0];
      touch.endX = screenX;
      touch.endY = screenY;

      if (TouchHandler.getSwipeContext(touch) == TouchHandler.SwipeContext.SwipeRight) {
        this.#handleClosure()
      }
    }, { passive: true });
  }
}

domReady.finally(() => {
  window.ToastFactory = new ToastNotificationFactory();
});
