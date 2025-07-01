/**
 * Class describing a deferred group of threads, similar impl. to requestAnimationFrame
 * @see {@link https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame|RAF}
 * 
 * @class
 * @constructor
 */
export default class DeferredThreadGroup {
  #iHnd = 0;
  #queue = [];
  #delay = 1000 / 60;
  #lastCalled = 0;

  constructor(delay) {
    this.#iHnd = 0;
    this.#delay = (typeof delay === 'number' && !isNaN(delay)) ? Math.max(0, delay) : this.#delay;
  }


  /*************************************
   *                                   *
   *              Public               *
   *                                   *
   *************************************/

  /**
   * push
   * @desc pushes the callback to the deferred task queue,
   *       which will be called after _n_ delay - dependent
   *       on when the task group was last called
   * 
   * @param {function} callback the deferred task callback
   * @returns {number} the handle id associated with this task
   * 
   */
  push(callback) {
    if (this.#queue.length < 1) {
      const now = performance.now();
      const timeout = Math.max(0, this.#delay - (now - this.#lastCalled));
      const lastCalled = timeout + now;
      this.#lastCalled = lastCalled;

      setTimeout(() => {
        const queue = this.#queue.slice(0);
        this.#queue.length = 0;

        for (let i = 0; i < queue.length; ++i) {
          const element = queue[i];
          if (isNullOrUndefined(element) || element.hasOwnProperty('cancelled')) {
            continue;
          }

          try {
            element.callback(lastCalled);
          }
          catch (e) {
            this.#silentlyThrow(e);
          }
        }
      }, Math.round(timeout));
    }

    const id = ++this.#iHnd;
    this.#queue.push({ handle: id, callback: callback });

    return id;
  }

  /**
   * cancel
   * @desc cancels a task given its handle id, as derived by the `::push()` method
   * @param {number} hnd the task group handle to cancel
   * @returns {object} this instance, for chaining
   * 
   */
  cancel(hnd) {
    const handle = this.#queue.find(e => e?.handle == hnd);
    if (!isNullOrUndefined(handle)) {
      handle.cancelled = true;
    }

    return this;
  }

  /**
   * clear
   * @desc clears all queued tasks
   * @returns {object} this instance, for chaining
   * 
   */
  clear() {
    const queue = this.#queue.slice(0);
    const length = queue.length;
    this.#queue.length = 0;

    if (length < 1) {
      return this;
    }

    for (let i = 0; i < length; ++i) {
      queue[i].cancelled = true;
    }

    return this;
  }


  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/

  /**
   * silentlyThrow
   * @desc throws the error outside of the current thread for it to be raised
   *       without blocking the current thread 
   * 
   * @param {object<Error>} e an error that was thrown during task execution
   * @returns {object} this instance, for chaining
   * 
   */
  #silentlyThrow(e) {
    setTimeout(() => {
      throw e;
    }, 0);

    return this;
  }
}
