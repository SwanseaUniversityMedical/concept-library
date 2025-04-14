/**
 * @class ListEnum
 * @desc handler for ListEnum components, where:
 *        - Selection of individual values via checkboxes
 * @param {string/node} obj The ID of the input element or the input element itself
 * @param {object} data Should contain both (1) the available options and (2) the available groups
 * @return {object} An interface to control the behaviour of the component
 * 
 */
export default class DoubleRangeSlider {
  constructor(obj, data, defaultValue) {
    if (typeof obj === 'string') {
      this.id = id;
      this.element = document.getElementById(id);
    } else {
      this.element = obj;
      if (typeof this.element !== 'undefined') {
        this.id = this.element.getAttribute('id');
      }
    }

    this.value = [];
    this.data = data;
    this.#initialise()
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

  /*************************************
   *                                   *
   *               Setter              *
   *                                   *
   *************************************/ 
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
    if (isNullOrUndefined(value)) {
      this.value = { min: this.data.properties.min, max: this.data.properties.max };
      return this;
    }
    this.value = value;

    if (this.value.min >= this.value.max) {
      this.value.min = this.value.max;
    } else if (this.value.max <= this.value.min) {
      this.value.max = this.value.min;
    }

    this.elements.inputs.min.value = this.value.min;
    this.elements.inputs.max.value = this.value.max;
    this.elements.sliders.min.value = this.value.min;
    this.elements.sliders.max.value = this.value.max;

    this.setProgressBar();

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
    minValueInput.value = this.data.properties.min;
    minValueInput.addEventListener('change', this.#onChangeCallback.bind(this));

    const maxValueInput = this.element.querySelector('#max-value');
    maxValueInput.min = this.data.properties.min;
    maxValueInput.max = this.data.properties.max;
    maxValueInput.value = this.data.properties.max;
    maxValueInput.addEventListener('change', this.#onChangeCallback.bind(this));

    const minValueSlider = this.element.querySelector('#min-slider');
    minValueSlider.min = this.data.properties.min;
    minValueSlider.max = this.data.properties.max;
    minValueSlider.value = this.data.properties.min;
    minValueSlider.addEventListener('input', this.#onChangeCallback.bind(this));

    const maxValueSlider = this.element.querySelector('#max-slider');
    maxValueSlider.min = this.data.properties.min;
    maxValueSlider.max = this.data.properties.max;
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
    const currentValue = { min: this.value.min, max: this.value.max };

    const target = e.target;
    const dataTarget = target.getAttribute('data-target');
    currentValue[dataTarget] = parseInt(target.value);

    this.setValue(currentValue);
  }
}
