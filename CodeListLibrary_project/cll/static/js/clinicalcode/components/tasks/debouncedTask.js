/**
 * Extensible fn class to throttle / debounce method calls
 * 
 * @class
 * @constructor
 */
export default class DebouncedTask extends Function {
  handle = null;

  task = () => { };
  delay = 100;
  result = null;
  params = { ctx: undefined, args: undefined };
  lastCalled = 0;
  resetSubsequent = false;

  /**
   * @param {Function} task                    some function to be called after the specified delay
   * @param {number}   [delay=100]             optionally specify the debounce duration, i.e. the delay time, in milliseconds, before calling the fn
   * @param {boolean}  [resetSubsequent=false] optionally specify whether to reset the timeout after each subsequent call, otherwise the call time is dependent on when the initial call was made; defaults to `false`
   */
  constructor(task, delay = 100, resetSubsequent = false) {
    assert(typeof(task) === 'function', `Expected fn for task but got "${typeof(task)}"`);

    super();

    this.task = task;
    this.delay = (typeof(delay) === 'number' && !isNaN(delay)) ? Math.max(0, delay) : this.delay;
    this.resetSubsequent = !!resetSubsequent;

    const res = new Proxy(this, {
      get: (target, key) => {
        if (target?.[key]) {
          return target[key];
        } else {
          return target.__inherit__[key];
        }
      },
      apply: (target, thisArg, args) => {
        return target?.__calL__.apply(target, args);
      }
    });
    res.__inherit__ = DebouncedTask;

    return res;
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
    const hnd = this.handle;
    if (isNullOrUndefined(hnd)) {
      return;
    }

    const now = performance.now();
    const { ctx, args = undefined } = this.params;
    this.params.ctx = undefined;
    this.params.args = undefined;

    this.result = this.task.apply(ctx, args);
    this.lastCalled = now;

    return this.clear();
  }

  /**
   * clear
   * @desc clears the current task queue
   * @returns {object} this instance, for chaining
   * 
   */
  clear() {
    const hnd = this.handle;
    if (isNullOrUndefined(hnd)) {
      return;
    }
    this.handle = null;
    clearTimeout(hnd);

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
  deferredCall() {
    const now = performance.now();
    const delay = this.delay;
    const elapsed = now - this.lastCalled;

    let hnd = this?.handle;
    if (!!hnd) {
      this.handle = null;
      clearTimeout(hnd);
    }

    if (elapsed < delay && elapsed > 0) {
      this.handle = setTimeout(() => { this.deferredCall(true) }, elapsed - delay);
      return;
    }


    const { ctx, args = undefined } = this.params;
    this.params.ctx = undefined;
    this.params.args = undefined;
    this.result = this.task.apply(ctx, args);
    if (!this.resetSubsequent) {
      this.lastCalled = now;
    }
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
  __calL__(...args) {
    const { ctx } = this.params;
    if (ctx && this !== ctx) {
      throw new Error('[DebouncedTask] Context mismatch');
    }

    this.params.ctx = this;
    this.params.args = args;

    const now = performance.now();
    if (this.resetSubsequent) {
      this.clear();
      this.lastCalled = now;
    }

    if (isNullOrUndefined(this.handle)) {
      this.handle = setTimeout(() => {
        this.deferredCall.bind(this)();
      }, this.delay);
    }

    return this.result;
  }
}
