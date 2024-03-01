/**
 * @class DebouncedTask
 * @desc Extensible fn to throttle / debounce method calls
 * 
 */
export default class DebouncedTask extends Function {
  #task = () => { };
  #delay = 100;
  #handle = null;
  #result = null;
  #params = { ctx: undefined, args: undefined };
  #lastCalled = 0;

  constructor(task, delay) {
    assert(typeof(task) === 'function', `Expected fn for task but got "${typeof(task)}"`);

    super();
    this.#task = task;
    this.#delay = (typeof(delay) === 'number' && !isNaN(delay)) ? Math.max(0, delay) : this.#delay;

    return Object.setPrototypeOf(task, new.target.prototype);
  }


  /*************************************
   *                                   *
   *              Public               *
   *                                   *
   *************************************/

  /**
   * flush
   * @desc flushes the current task list and attempts to call
   *       the associated task with the current context and varargs
   * 
   * @returns {object} this instance, for chaining
   * 
   */
  flush() {
    const hnd = this.#handle;
    if (isNullOrUndefined(hnd)) {
      return;
    }

    const { ctx, args } = this.#params;
    this.#params.ctx = undefined;
    this.#params.args = undefined;

    this.#result = this.#task.apply(ctx, args);

    return this.clear();
  }

  /**
   * clear
   * @desc clears the current task queue
   * @returns {object} this instance, for chaining
   * 
   */
  clear() {
    const hnd = this.#handle;
    if (isNullOrUndefined(hnd)) {
      return;
    }

    clearTimeout(hnd);

    this.#handle = null;
    return this;
  }


  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/

  /**
   * deferredCall
   * @desc handles the deferred method call of the associated task
   * 
   */
  #deferredCall() {
    const delay = this.#delay
    const elapsed = performance.now() - this.#lastCalled;
    if (elapsed < delay && elapsed > 0) {
      this.#handle = setTimeout(later, delay - elapsed);
      return;
    }

    this.#handle = null;

    const { ctx, args } = this.#params;
    this.#params.ctx = undefined;
    this.#params.args = undefined;
    this.#result = this.#task.apply(ctx, args);
  }


  /*************************************
   *                                   *
   *             Prototype             *
   *                                   *
   *************************************/

  /**
   * __call__
   * @prototype DebouncedTask.prototype.call
   * @desc defines the __call__ prototype for this class,
   *       allowing its instances to be called in a similar
   *       manner to method(s)
   * 
   * @param  {...any} args variadic arguments relating to the inner task
   * @returns the last result (if any)
   *  
   */
  __call__(...args) {
    console.log('CALL');
    const { ctx } = this.#params;
    if (ctx && this !== ctx) {
      throw new Error('huh?');
    }

    this.#params.ctx = this;
    this.#params.args = args;

    if (isNullOrUndefined(this.#handle)) {
      this.#handle = setTimeout(this.#deferredCall.bind(this), this.#delay);
    }

    return this.#result;
  }
}
