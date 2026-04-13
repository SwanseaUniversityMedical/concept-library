import { parseAsFieldType, resolveRangeOpts } from '../entityCreator/utils.js';

/**
 * A `number`, or `string`, describing a numeric object.
 * @typedef {(number|string)} NumberLike
 */

/**
 * Age group value object
 * @typedef {Object} AgeValue
 * @property {NumberLike}              value      the maximum value of the age group
 * @property {('between'|'lte'|'gte')} comparator the minimum value of the age group
 */

/**
 * Properties assoc. with age group inputs; used to constrain and/or to compute the value
 * @typedef {Object} AgeProps
 * @property {NumberLike} min  the minimum value of the age group
 * @property {NumberLike} max  the maximum value of the age group
 * @property {NumberLike} step specifies the age group increment
 */

/**
 * Age group initialisation data
 * @typedef {Object} AgeData
 * @property {AgeValue} value      specifies the initial age group component value
 * @property {AgeProps} properties specifies the properties of the age group component, see {@link AgeProps}
 */

/**
 * @desc computes the properties assoc. with an age group component
 * 
 * @param {?AgeData} data an object containing the properties
 * 
 * @returns {AgeData} the computed properties
 */
const computeParams = (data) => {
  const hasData = isObjectType(data)
  data = hasData ? data : { };

  let props = data?.properties;
  if (!isObjectType(props)) {
    props = { min: 0, max: 100, step: 1 };
  }

  let valueStep = typeof props?.step === 'string' ? Number(props?.step) : props.step;
  let hasValidStep = isSafeNumber(valueStep);

  let min = typeof props.min === 'string' ? Number(props.min) : props.min;
  let max = typeof props.max === 'string' ? Number(props.max) : props.max;

  const validMin = isSafeNumber(min);
  const validMax = isSafeNumber(max);

  if (!hasValidStep) {
    if ((validMin || validMax)) {
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
  props.step = valueStep;

  data.props = props;
  data.value = mergeObjects(
    isObjectType(data.value) ? data.value : { },
    { comparator: 'na', value: [min, max] },
    true,
    true
  );

  if (data.value.comparator === 'between' && !Array.isArray(data.value.value)) {
    data.value.value = [min, max];
  } else if (data.value.comparator.includes('te') && !isSafeNumber(data.value.value)) {
    data.value.value = min;
  }

  return data;
}

/**
 * A class that instantiates and manages a age group component to select a single numeric value
 * @class
 * @alias module:AgeGroupSelector
 */
export default class AgeGroupSelector {
  /**
   * @desc describes the HTMLElements = by way of their query selectors - assoc. with this instance
   * @type {Record<string, string>}
   * @static
   * @constant
   */
  static #Composition = {
    container: '#age-container',
    comparator: '#comparator-dropdown',
  };

  /**
   * @desc a Recordset containing a set of assoc. HTML frag templates
   * @type {!Record<string, Record<string, HTMLElement>>}
   * @private
   */
  #templates = null;

  /**
   * @desc an object describing the active interface
   * @type {?object}
   * @private
   */
  #interface = null;

  /**
   * @param {HTMLElement|string}  obj  Either (a) a HTMLElement assoc. with this instance, or (b) a query selector string to locate said element
   * @param {Partial<AgeData>} data Should describe the properties & validation assoc. with this component, see {@link AgeData}
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
     * @desc initialisation data & properties assoc. with this instance 
     * @type {!AgeData}
     * @public
     */
    this.data = computeParams(data);

    /**
     * @desc range assoc. with this component
     * @type {!object}
     * @public
     */
    this.rangeOpts = resolveRangeOpts('int', this.data.properties);

    /**
     * @desc the current numeric value selected by the client
     * @type {!AgeValue}
     * @public
     */
    this.value = data.value;

    /**
     * @desc describes the dirty (changed) state of this instance
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

    this.#initialise();
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
    if (this.value.comparator === 'na') {
      return null;
    }

    return {
      value: this.value.value,
      comparator: this.value.comparator, 
    };
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
   * @desc updates this instance's value
   * 
   * @param {AgeValue} val component value describing the number/numeric value alongside the comparator
   *  
   * @returns {boolean} reflecting whether this instance's value was updating or not
   */
  setValue(val) {
    if (!isObjectType(val)) {
      return false;
    }

    const instVal = this.value;
    const { min, max } = this.data.properties;
    const { comparator, value } = val;

    let changed;
    switch (comparator) {
      case 'between': {
        let [vmin, vmax] = value;
        vmin = parseAsFieldType({ validation: { type: 'int', properties: { min, max } } }, vmin);
        vmax = parseAsFieldType({ validation: { type: 'int', properties: { min, max } } }, vmax);
        if ((!vmin || !vmin?.success) || (!vmax || !vmax?.success)) {
          return false;
        }

        vmin = vmin.value;
        vmax = vmax.value;

        let tmp = Math.max(vmin, vmax);
        vmin = Math.min(vmin, vmax);
        vmax = tmp;

        changed = Array.isArray(instVal.value)
          ? instVal.value[0] !== vmin || instVal.value[1] != vmax
          : true;

        instVal.value = [vmin, vmax];
      } break;

      case 'lte':
      case 'gte': {
        let vx = parseAsFieldType({ validation: { type: 'int', properties: { min, max } } }, value);
        if (!vx || !vx?.success) {
          return false;
        }

        changed = instVal.value != vx.value;
        instVal.value = vx.value;
      } break;
    }

    if (!!changed) {
      this.makeDirty();
    }

    if (!!this.#interface && this.#interface?.setValue) {
      this.#interface?.setValue?.(instVal.value);
    }

    return true;
  }

  /**
   * @desc updates this instance's mode
   * 
   * @param {string}  classType  specify the component mode type
   * @param {string?} [relation] optionally specify the comparator
   *  
   * @returns {boolean} reflecting whether the component was changed
   */
  setMode(classType, relation = 'between') {
    switch (classType) {
      case 'na': {
        relation = 'na';
      } break;

      case 'range': {
        relation = 'between';
      } break;

      case 'bounds': {
        relation = stringHasChars(relation) && ['lte', 'gte'].includes(relation)
          ? relation
          : 'lte';
      } break;

      default:
        return false;
    }

    const val = this.value;
    const hasChanged = relation !== val.comparator;
    if (this.#interface && !hasChanged) {
      return false;
    }

    if (hasChanged) {
      const range = this.rangeOpts.values;
      val.value = relation === 'between'
        ? [range.min, range.max]
        : range.min;

      val.comparator = relation;
      this.makeDirty();
    }

    this.#drawInterface();
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

  #drawInterface() {
    const elements = this.elements;
    const templates = this.#templates;

    const instVal = this.value;
    const { comparator } = instVal;

    const range = this.rangeOpts;
    const fieldValidation = { validation: { type: 'int' } };
    if (!isNullOrUndefined(range.values.min) && !isNullOrUndefined(range.values.max)) {
      fieldValidation.validation.range = [range.values.min, range.values.max];
    }

    switch (comparator) {
      case 'na': {
        clearAllChildren(elements.container);
      } break;

      case 'between': {
        composeTemplate(templates.inputs.range, {
          params: {
            id: 'value-input',
            ref: 'value',
            type: 'int',
            step: range.attr.step,
            label: 'Value',
            btnStep: range.values.step,
            rangemin: range.attr.min,
            rangemax: range.attr.max,
            value_min: instVal.value[0],
            value_max: instVal.value[1],
            placeholder: 'Number value...',
            disabled: '',
            mandatory: true,
          },
          render: (obj) => {
            clearAllChildren(elements.container);

            obj = obj.shift();
            obj = elements.container.appendChild(obj);

            const minInput = obj.querySelector('#min-value');
            const maxInput = obj.querySelector('#max-value');
            const minSlider = obj.querySelector('#min-slider');
            const maxSlider = obj.querySelector('#max-slider');
            const progressBar = obj.querySelector('#progress-bar');

            this.#interface = {
              minInput: minInput,
              maxInput: maxInput,
              minSlider: minSlider,
              maxSlider: maxSlider,
              progressBar: progressBar,
              setValue: (num) => {
                const distance = range.values.max - range.values.min;
                const pos0 = (num[0] / distance) * 100,
                      pos1 = (num[1] / distance) * 100;

                minSlider.value = minInput.value = num[0];
                maxSlider.value = maxInput.value = num[1];

                this.#interface.progressBar.style.background = `
                linear-gradient(
                  to right,
                  var(--color-accent-semi-transparent) ${pos0}%, 
                  var(--color-accent-primary) ${pos0}%, 
                  var(--color-accent-primary) ${pos1}%, 
                  var(--color-accent-semi-transparent) ${pos1}%
                )`;
              },
            };

            const hnd = (e) => {
              let target;
              if (e.type === 'blur') {
                target = e.originalTarget;
              } else {
                target = e.target;
              }

              if (!target || !this.element.contains(target) || !target.matches('input[type="range"], input[type="number"]')) {
                return;
              }

              const dataTarget = target.getAttribute('data-target');
              const num = [...instVal.value];
              num[dataTarget === 'min' ? 0 : 1] = target.value

              this.setValue({ comparator, value: num });
            };

            minInput.addEventListener('change', hnd);
            minSlider.addEventListener('input', hnd);

            maxInput.addEventListener('change', hnd);
            maxSlider.addEventListener('input', hnd);
            this.setValue(instVal);
          },
        });
      } break;

      default: {
        composeTemplate(templates.inputs.bounds, {
          params: {
            id: 'value-input',
            ref: 'value',
            type: 'int',
            step: range.attr.step,
            label: 'Value',
            btnStep: range.values.step,
            rangemin: range.attr.min,
            rangemax: range.attr.max,
            value: instVal.value,
            placeholder: 'Number value...',
            disabled: '',
            mandatory: true,
          },
          render: (obj) => {
            clearAllChildren(elements.container);

            obj = obj.shift();
            obj = elements.container.appendChild(obj);

            const input = obj.querySelector('#value-input');
            const slider = obj.querySelector('#slider-input');
            const progressBar = obj.querySelector('#progress-bar');

            this.#interface = {
              input: input,
              slider: slider,
              progressBar: progressBar,
              setValue: (num) => {
                const distance = range.values.max - range.values.min;
                const position = (num / distance) * 100;

                input.value = num;
                slider.value = num;
                progressBar.style.background = (
                  comparator == 'lte'
                    ? `linear-gradient(
                      to right,
                      var(--color-accent-semi-transparent) 0%, 
                      var(--color-accent-primary) 0%, 
                      var(--color-accent-primary) ${position}%, 
                      var(--color-accent-semi-transparent) ${position}%
                    )`
                    : `linear-gradient(
                      to left,
                      var(--color-accent-semi-transparent) 0%, 
                      var(--color-accent-primary) 0%, 
                      var(--color-accent-primary) ${100 - position}%, 
                      var(--color-accent-semi-transparent) ${100 - position}%
                    )`
                )
              },
            };

            input.addEventListener('change', (e) => {
              let val = parseAsFieldType(fieldValidation, input.value);
              if (!!val && val?.success) {
                val = { comparator, value: val.value };
              } else {
                val = { comparator, value: instVal.value };
              }

              this.setValue(val);
            });

            slider.addEventListener('input', (e) => {
              let trg = e.target;
              let val = parseAsFieldType(fieldValidation, trg.value);
              if (!!val && val?.success) {
                val = { comparator, value: val.value };
              } else {
                val = { comparator, value: instVal.value };
              }

              this.setValue(val);
            });
            this.setValue(instVal);
          },
        });
      } break;
    }
  }

  #initialiseElements() {
    const elem = this.element;
    this.#collectTemplates();

    const tree = { };
    for (const [name, selector] of Object.entries(AgeGroupSelector.#Composition)) {
      const obj = elem.querySelector(selector);
      if (!isHtmlObject(obj)) {
        throw new Error(`Failed to find assoc. Element<name: ${name}, sel: ${selector}> for Obj...\n${String(elem)}`);
      }
      tree[name] = obj;
    }

    return tree;
  }

  #initialise() {
    const val = this.value;
    const tree = this.elements;
    tree.comparator.selectedIndex = [...tree.comparator.options].findIndex(x => val.comparator === x.getAttribute('data-rel'));
    tree.comparator.options[tree.comparator.selectedIndex].selected = true;
    tree.comparator.dispatchEvent(new CustomEvent('change', { bubbles: true }));

    tree.comparator.addEventListener('change', (e) => {
      const target = e.target;
      const selected = target.options[target.selectedIndex];

      const relation = selected.getAttribute('data-rel');
      const classType = selected.getAttribute('data-cls');
      this.setMode(classType, relation);
    });

    this.#drawInterface();
  }
};
