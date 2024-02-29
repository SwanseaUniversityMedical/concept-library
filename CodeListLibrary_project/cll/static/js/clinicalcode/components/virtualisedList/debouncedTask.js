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
   * 
   * @returns 
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
   * 
   * @returns 
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
   * 
   * @returns 
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
   * 
   * @param  {...any} args 
   * @returns 
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
