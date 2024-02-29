/**
 * @class DeferredThreadGroup
 * @desc Deferred group of threads, similar impl. to requestAnimationFrame
 * 
 *       See ref @ https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame
 * 
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
   * 
   * @param {*} callback 
   * @returns 
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
      }, Math.round(timeout))
    }

    const id = ++this.#iHnd;
    this.#queue.push({ handle: id, callback: callback });

    return id
  }

  /**
   * 
   * @param {*} hnd 
   * @returns 
   */
  cancel(hnd) {
    const handle = this.#queue.find(e => e?.handle == hnd);
    if (!isNullOrUndefined(handle)) {
      handle.cancelled = true;
    }

    return this;
  }


  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/

  /**
   * 
   * @param {*} e 
   * @returns 
   */
  #silentlyThrow(e) {
    setTimeout(() => {
      throw e;
    }, 0);

    return this;
  }
}
