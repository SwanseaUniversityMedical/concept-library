import { parseAsFieldType, resolveRangeOpts } from '../forms/entityCreator/utils.js';

/**
 * A `number`, or `string`, describing a numeric object.
 * @typedef {(number|string)} NumberLike
 */

/**
 * A list of known numeric types that can are managed by the {@link SingleSlider} instance
 * @typedef {'int'|'float'|'decimal'|'numeric'|'percentage'} NumericFormat
 */

/**
 * Properties assoc. with slider inputs; used to constrain and/or to compute the slider value
 * @typedef {Object} SliderProps
 * @property {NumberLike}    min  the minimum value of the slider
 * @property {NumberLike}    max  the maximum value of the slider
 * @property {NumberLike}    step specifies the slider increment
 * @property {NumericFormat} type specifies how the numeric value will be formatted
 */

/**
 * Slider initialisation data
 * @typedef {Object} SliderData
 * @property {NumberLike}  value      specifies the initial slider value
 * @property {SliderProps} properties specifies the properties of the slider, see {@link SliderProps}
 */

/**
 * @desc computes the properties assoc. with a slider
 * 
 * @param {?SliderData}    data           an object containing the properties
 * @param {?Array<string>} [allowedTypes] optionally specify an arr of allowed data types
 * 
 * @returns {SliderData} the computed properties
 */
const computeParams = (data, allowedTypes = null) => {
  if (!Array.isArray(allowedTypes)) {
    allowedTypes = ['int', 'float', 'decimal', 'numeric', 'percentage'];
  }

  const hasData = isObjectType(data)
  data = hasData ? data : { };

  let props = data?.properties;
  if (!isObjectType(props)) {
    props = { min: 0, max: 1, step: 0.1, type: 'float' };
  }

  let valueType = props?.type;
  let hasValueType = stringHasChars(valueType);
  if (hasValueType) {
    valueType = valueType.toLowerCase();
    valueType = allowedTypes.includes(valueType) ? valueType : null;
    hasValueType = typeof valueType === 'string';
  }

  if (!hasValueType) {
    let example = props?.step;
    if (!isSafeNumber(example)) {
      example = [...Object.values(props)].concat([props?.value]).find(x => isSafeNumber(x));
      example = isSafeNumber(example) ? example : 0.1;
    }

    example = tryParseNumber(example)
    valueType = example.type;

    if (!allowedTypes.includes(valueType)) {
      throw new Error('Failed to resolve valid type');
    }
    hasValueType = true;
  }

  let valueStep = typeof props?.step === 'string' ? Number(props?.step) : props.step;
  let hasValidStep = isSafeNumber(valueStep);

  let min = typeof props.min === 'string' ? Number(props.min) : props.min;
  let max = typeof props.max === 'string' ? Number(props.max) : props.max;

  const validMin = isSafeNumber(min);
  const validMax = isSafeNumber(max);

  if (!hasValidStep) {
    if (hasValueType) {
      valueStep = valueType.includes('int') ? 1 : 0.1;
    } else if (validMin || validMax) {
      const precision = String(validMin ? min : max).split('.')?.[1]?.length || 0;
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

  data.props = props;
  data.value = clampNumber(
    isSafeNumber(data?.value) ? data.value : 0,
    props.min,
    props.max
  );

  return data;
}

/**
 * A class that instantiates and manages a slider to select a single numeric value
 * @class
 * @alias module:SingleSlider
 */
export default class SingleSlider {
  /**
   * @desc describes the types that can be managed by this slider
   * @type {Array<NumericFormat>}
   * @static
   * @constant
   * @readonly
   */
  static AllowedTypes = Object.freeze(['int', 'float', 'decimal', 'numeric', 'percentage']);

  /**
   * @desc describes the HTMLElements = by way of their query selectors - assoc. with this instance
   * @type {Record<string, string>}
   * @static
   * @constant
   */
  static #Composition = {
    input: '#value-input',
    slider: '#slider-input',
    progressBar: '#progress-bar',
  };

  /**
   * @desc a Recordset containing a set of assoc. HTML frag templates
   * @type {!Record<string, Record<string, HTMLElement>>}
   * @private
   */
  #templates = null;

  /**
   * @param {HTMLElement|string}  obj  Either (a) a HTMLElement assoc. with this instance, or (b) a query selector string to locate said element
   * @param {Partial<SliderData>} data Should describe the properties & validation assoc. with this component, see {@link SliderData}
   */
  constructor(obj, data) {
    let element;
    if (isHtmlObject(obj)) {
      element = obj;
    } else if (typeof obj === 'string') {
      if (!isValidSelector(obj)) {
        throw new Error(`Query selector of Param<obj: ${obj}> is invalid`);
      }

      element = document.querySelector(obj);
    }

    if (!isHtmlObject(element)) {
      throw new Error(`Failed to locate a valid assoc. HTMLElement with Params<obj: ${String(obj)}>`);
    }

    /**
     * @desc the ID attribute assoc. with this instance's `element` (`HTMLElement`), if applicable
     * @type {?string}
     * @default null
     * @public
     */
    this.id = element.getAttribute('id') ?? null;

    /**
     * @desc the `HTMLElement` assoc. with this instance
     * @type {!HTMLElement}
     * @public
     */
    this.element = element;

    /**
     * @desc 
     * @type {!SliderData}
     * @public
     */
    this.data = computeParams(data, SingleSlider.AllowedTypes);

    /**
     * @desc the current numeric value selected by the client
     * @type {!number}
     * @public
     */
    this.value = this.data.value;

    /**
     * @desc 
     * @type {!boolean}
     * @default false
     * @public
     */
    this.dirty = false;

    /**
     * @desc a Recordset containing the elements assoc. with this instance
     * @type {!Record<string, HTMLElement>}
     * @public
     */
    this.elements = this.#initialiseElements();
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
    const position = (this.value / distance) * 100;

    this.elements.progressBar.style.background = `
      linear-gradient(
        to right,
        var(--color-accent-semi-transparent) 0%, 
        var(--color-accent-primary) 0%, 
        var(--color-accent-primary) ${position}%, 
        var(--color-accent-semi-transparent) ${position}%
      )
    `;
  }

  /**
   * @desc updates this instance's value
   * @note
   *  - will ignore non-safe numbers
   *  - will constrain the number as specified by this instance's props
   * 
   * @param {NumberLike} val some number-like value
   *  
   * @returns {boolean} reflecting whether this instance's value was updating or not
   */
  setValue(val) {
    const { min, max, type } = this.data.properties;
    const parsed = parseAsFieldType({ validation: { type, properties: { min, max } } }, val)
    if (!parsed || !parsed?.success) {
      return false;
    }

    val = parsed.value;
    if (!isSafeNumber(val)) {
      return false;
    }

    const elements = this.elements;
    elements.input.value = val;
    elements.slider.value = val;
    this.value = val;
    this.setProgressBar();

    if (val !== this.value) {
      this.makeDirty();
    }

    return true;
  }


  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/
  #collectTemplates() {
    let templates = this.#templates;
    if (isObjectType(templates)) {
      return templates;
    }

    templates = { }
    this.#templates = templates;

    const elem = this.element.parentElement;
    elem.querySelectorAll('template[data-name]').forEach(v => {
      let name = v.getAttribute('data-name');
      let view = v.getAttribute('data-view');
      if (!stringHasChars(view)) {
        view = 'base';
      }

      let group =  templates?.[view];
      if (!group) {
        group = { };
        templates[view] = group;
      }

      group[name] = v;
    });

    return templates;
  }

  #initialiseElements() {
    const elem = this.element;
    const data = this.data;
    const props = data.properties;

    const value = this.value;
    const range = resolveRangeOpts(props.type, props);

    const fieldValidation = { validation: { type: props.type } };
    if (!isNullOrUndefined(range.values.min) && !isNullOrUndefined(range.values.max)) {
      fieldValidation.validation.range = [range.values.min, range.values.max];
    }

    const templates = this.#collectTemplates();
    composeTemplate(templates.inputs.number, {
      params: {
        id: 'value-input',
        ref: 'value',
        type: props.type,
        step: range.attr.step,
        label: 'Value',
        btnStep: range.values.step,
        rangemin: range.attr.min,
        rangemax: range.attr.max,
        value: value,
        placeholder: 'Number value...',
        disabled: '',
        mandatory: true,
      },
      render: (obj) => {
        obj = obj.shift();
        obj = elem.appendChild(obj);

        const input = obj.querySelector('input');
        input.value = value;

        input.addEventListener('change', (e) => {
          let val = parseAsFieldType(fieldValidation, input.value);
          if (!!val && val?.success) {
            val = val.value;
          } else {
            val = this.value;
          }

          this.setValue(val);
        });
      },
    });

    const tree = { };
    for (const [name, selector] of Object.entries(SingleSlider.#Composition)) {
      const obj = elem.querySelector(selector);
      if (!isHtmlObject(obj)) {
        throw new Error(`Failed to find assoc. Element<name: ${name}, sel: ${selector}> for Obj...\n${String(elem)}`);
      }
      tree[name] = obj;
    }

    tree.slider.min = props.min;
    tree.slider.max = props.max;
    tree.slider.step = props.step;
    tree.slider.value = props.min;

    tree.slider.addEventListener('input', (e) => {
      let trg = e.target;
      let val = parseAsFieldType(fieldValidation, trg.value);
      if (!!val && val?.success) {
        val = val.value;
      } else {
        val = this.value;
      }

      this.setValue(val);
    });

    this.setValue(this.value);
    return tree;
  }
};
