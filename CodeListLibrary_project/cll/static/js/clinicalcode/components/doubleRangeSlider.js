import { parseAsFieldType } from '../forms/entityCreator/utils.js';

/**
 * @class DoubleRangeSlider
 * @desc handler for DoubleRangeSlider components
 * 
 * @param {string/node} obj  The ID of the input element or the input element itself
 * @param {object}      data Should describe the properties & validation assoc. with this component
 * 
 * @return {object} An interface to control the behaviour of the component
 */
export default class DoubleRangeSlider {
  /**
   * @desc describes the types that can be managed by this slider
   * @static
   * @constant
   */
  static AllowedTypes = ['int', 'float', 'decimal', 'numeric', 'percentage'];

  constructor(obj, data) {
    if (typeof obj === 'string') {
      this.id = id;
      this.element = document.getElementById(id);
    } else {
      this.element = obj;
      if (typeof this.element !== 'undefined') {
        this.id = this.element.getAttribute('id');
      }
    }

    this.value = null;
    this.dirty = false;

    this.data = data;
    this.data.properties = DoubleRangeSlider.ComputeProperties(this.data.properties);

    this.#initialise();
  }

  /**
   * @desc attempts to parse, validate, and compute the properties of the range slider 
   * @static
   * 
   * @param {any} props the range properties, if available
   * 
   * @returns {Record<string, string|number>} the resulting range props
   */
  static ComputeProperties(props) {
    let valueType = props?.type;
    let valueStep = typeof props?.step === 'string' ? Number(props?.step) : props.step;

    let hasValueType = false;
    let hasValidStep = typeof valueStep === 'number' && !isNaN(valueStep) && Number.isFinite(valueStep);
    if (!isObjectType(props)) {
      props = { min: 0, max: 100, step: 1, type: 'int' };
    }

    if (stringHasChars(valueType)) {
      valueType = valueType.toLowerCase();
      valueType = DoubleRangeSlider.AllowedTypes.includes(valueType) ? valueType : null;
      hasValueType = typeof valueType === 'string';
    }

    let min = typeof props.min === 'string' ? Number(props.min) : props.min;
    let max = typeof props.max === 'string' ? Number(props.max) : props.max;

    const validMin = typeof min === 'number' && !isNaN(min) && Number.isFinite(min);
    const validMax = typeof max === 'number' && !isNaN(max) && Number.isFinite(max);

    if (!hasValidStep) {
      if (hasValueType) {
        valueStep = valueType === 'int' ? 1 : 0.1;
      } else if (validMin) {
        const precision = String(min).split('.')?.[1]?.length || 0;
        valueStep = Math.pow(10, -precision);
      } else {
        valueStep = 1;
      }
    }

    if (validMin && validMax) {
      let tmp = Math.max(min, max);
      min = Math.min(min, max);
      max = tmp;
    } else if (validMin) {
      max = min + (hasValidStep ? valueStep : 1)*100;
    } else if (validMax) {
      min = max - (hasValidStep ? valueStep : 1)*100;
    } else {
      min = 0;
      max = valueStep*100;
    }
    props.min = min;
    props.max = max;

    if (!hasValueType) {
      let precision = hasValidStep ? step : (isNullOrUndefined(min) ? min : 0);
      precision = String(precision).split('.')?.[1]?.length || 0;
      valueType = precision === 0 ? 'int' : 'float';
    }

    props.type = valueType;
    props.step = valueStep;
    return props;
  }
  
  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/  
  /**
   * getValue
   * @desc gets the current value of the component
   * @returns {any} the value selected via its options data
   */
  getValue() {
    return this.value;
  }

  /**
   * getElement
   * @returns {node} the assoc. element
   */
  getElement() {
    return this.element;
  }

  /**
   * isDirty
   * @returns {bool} returns the dirty state of this component
   */
  isDirty() {
    return this.dirty;
  }

  /*************************************
   *                                   *
   *               Setter              *
   *                                   *
   *************************************/ 
  /**
   * makeDirty
   * @desc informs the top-level parent that we're dirty
   *       and updates our internal dirty state
   * @return {object} return this for chaining
   */
  makeDirty() {
    window.entityForm.makeDirty();
    this.dirty = true;
    return this;
  }

  /**
   * setProgressBar
   * @desc sets the current value of the component
   * @param {any} value the value that should be selected from its list of options
   */
  setProgressBar() {
    const distance = this.data.properties.max - this.data.properties.min;
    const pos0 = (this.value.min / distance) * 100,
          pos1 = (this.value.max / distance) * 100;

    this.elements.progressBar.style.background = `
      linear-gradient(
        to right,
        var(--color-accent-semi-transparent) ${pos0}%, 
        var(--color-accent-primary) ${pos0}%, 
        var(--color-accent-primary) ${pos1}%, 
        var(--color-accent-semi-transparent) ${pos1}%
      )
    `;
  }
  
  /**
   * setValue
   * @desc sets the current value of the component
   * @param {any} value the value that should be selected from its list of options
   */
  setValue(value) {
    const { min, max, type, step } = this.data.properties;
    if (this.value) {
      this.dirty = !value || value.min != this.value.min || this.max != this.value.max;
    }

    if (!isObjectType(value)) {
      this.value = { min, max };
      return this;
    }

    let { min: vmin, max: vmax } = value;
    vmin = parseAsFieldType({ validation: { type }}, value.min);
    vmax = parseAsFieldType({ validation: { type }}, value.max);

    vmin = (!isNullOrUndefined(vmin) && !!vmin.success) ? vmin.value : min;
    vmax = (!isNullOrUndefined(vmax) && !!vmax.success) ? vmax.value : max;
    value = { min: vmin, max: vmax };

    vmin = Math.min(value.min, value.max);
    vmax = Math.max(value.min, value.max);

    if (type === 'int') {
      vmin = Math.trunc(vmin);
      vmax = Math.trunc(vmax);
    } else {
      const m = Math.pow(10, String(step).split('.')?.[1]?.length || 0);
      vmin = Math.round(vmin * m) / m;
      vmax = Math.round(vmax * m) / m;
    }

    value.min = Math.min(Math.max(vmin, min), max);
    value.max = Math.min(Math.max(vmax, min), max);
    this.value = value;

    this.elements.inputs.min.value = value.min;
    this.elements.inputs.max.value = value.max;
    this.elements.sliders.min.value = value.min;
    this.elements.sliders.max.value = value.max;

    this.setProgressBar();
    fireChangedEvent(this.element);
    return this;
  }

  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/
  /**
   * initialise
   * @desc private method to initialise & render the component
   */
  #initialise() {
    const progress = this.element.querySelector('#progress-bar');

    const minValueInput = this.element.querySelector('#min-value');
    minValueInput.min = this.data.properties.min;
    minValueInput.max = this.data.properties.max;
    minValueInput.step = this.data.properties.step;
    minValueInput.value = this.data.properties.min;
    minValueInput.addEventListener('blur', this.#onChangeCallback.bind(this));
    minValueInput.addEventListener('change', this.#onChangeCallback.bind(this));

    const maxValueInput = this.element.querySelector('#max-value');
    maxValueInput.min = this.data.properties.min;
    maxValueInput.max = this.data.properties.max;
    maxValueInput.step = this.data.properties.step;
    maxValueInput.value = this.data.properties.max;
    maxValueInput.addEventListener('blur', this.#onChangeCallback.bind(this));
    maxValueInput.addEventListener('change', this.#onChangeCallback.bind(this));

    const minValueSlider = this.element.querySelector('#min-slider');
    minValueSlider.min = this.data.properties.min;
    minValueSlider.max = this.data.properties.max;
    minValueSlider.step = this.data.properties.step;
    minValueSlider.value = this.data.properties.min;
    minValueSlider.addEventListener('input', this.#onChangeCallback.bind(this));

    const maxValueSlider = this.element.querySelector('#max-slider');
    maxValueSlider.min = this.data.properties.min;
    maxValueSlider.max = this.data.properties.max;
    maxValueSlider.step = this.data.properties.step;
    maxValueSlider.value = this.data.properties.max;
    maxValueSlider.addEventListener('input', this.#onChangeCallback.bind(this));

    this.elements = {
      progressBar: progress,
      inputs: { min: minValueInput, max: maxValueInput },
      sliders: { min: minValueSlider, max: maxValueSlider }
    }

    let value = this.data?.value;
    if (!isNullOrUndefined(value) && !isNullOrUndefined(value.min) && !isNullOrUndefined(value.max)) {
      this.setValue(value);
    } else {
      this.setValue(null);
    }
  }

  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/
  /**
   * onChangeCallback
   * @desc handles the change event for all related checkboxes
   * @param {event} e the change event of an element
   */
  #onChangeCallback(e) {
    let target;
    if (e.type === 'blur') {
      target = e.originalTarget;
    } else {
      target = e.target;
    }

    if (!target || !this.element.contains(target) || !target.matches('input[type="range"], input[type="number"]')) {
      return;
    }

    let { type } = this.data.properties || { };
    type = stringHasChars(type) ? type : 'int';

    const dataTarget = target.getAttribute('data-target');
    const currentValue = { min: this.value.min, max: this.value.max };
    if (type === 'int') {
      currentValue[dataTarget] = parseInt(target.value);
    } else {
      currentValue[dataTarget] = parseFloat(target.value);
    }

    this.setValue(currentValue);
  }
}
