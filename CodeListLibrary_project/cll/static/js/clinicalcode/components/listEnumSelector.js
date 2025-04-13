/**
 * @class ListEnum
 * @desc handler for ListEnum components, where:
 *        - Selection of individual values via checkboxes
 * @param {string/node} obj The ID of the input element or the input element itself
 * @param {object} data Should contain both (1) the available options and (2) the available groups
 * @return {object} An interface to control the behaviour of the component
 * 
 */
export default class ListEnum {
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
   * setValue
   * @desc sets the current value of the component
   * @param {any} value the value that should be selected from its list of options
   */
  setValue(value) {
    if (isNullOrUndefined(value)) {
      this.value = [];

      const checked = this.element.querySelectorAll('input:checked')
      for (let i = 0; i < checked.length; ++i) {
        checked[i].checked = false;
      }
      return this;
    }
    this.value = value;

    const inputs = this.element.querySelectorAll('input');
    for (let i = 0; i < inputs.length; ++i) {
      let val = inputs[i].getAttribute('data-value');
      inputs[i].checked = value.includes(val);
    }

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
    // Build renderables
    for (let i = 0; i < this.data?.options.length; ++i) {
      const option = this.data?.options[i];
      const item = this.#createCheckbox(
        `${option.name}-${option.value}`,
        option.name,
        option.value
      );

      // assign changed behaviour
      const checkbox = item.querySelector('input');
      checkbox.addEventListener('change', this.#onChangeCallback.bind(this));
    }

    // Assign default value
    let value = this.data.value;
    if (Array.isArray(value) && value.length > 0) {
      value = value.map(x => x.value)
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
    const checked = this.element.querySelectorAll('input:checked')
    const selected = Array.prototype.slice.call(checked)
      .map(node => {
        return this.data?.options.find(x => x.value == node.getAttribute('data-value'))
      });
      
    let selectedValues = selected.map(x => x?.value);

    let deselectExcept = null;
    let properties = this.data?.properties;
    if (!isNullOrUndefined(properties)) {
      for (let i = 0; i < properties.length; ++i) {
        let group = properties[i];
        if (isNullOrUndefined(group?.when)) {
          continue;
        }

        if (isNullOrUndefined(group?.result)) {
          continue;
        }

        if (group.result == 'deselect') {
          if (this.value[0] === group?.when) {
            this.value = this.value.filter((el) => {
              return el !== group?.when;
            });

            for (let i = 0; i < checked.length; ++i) {
              let checkbox = checked[i];
              let checkboxValue = checkbox.getAttribute('data-value');
              if (checkboxValue === group?.when) {
                checkbox.checked = false;
              }
            }
            continue;
          }

          if (selectedValues.includes(group?.when)) {
            deselectExcept = group?.when;
          }
        }
      }
    }

    if (!isNullOrUndefined(deselectExcept)) {
      for (let i = 0; i < checked.length; ++i) {
        let checkbox = checked[i];
        let checkboxValue = checkbox.getAttribute('data-value');

        checkbox.checked = checkboxValue === deselectExcept;
      }

      this.value = [deselectExcept];
      return;
    }

    const target = e.currentTarget;
    const targetValue = target.getAttribute('data-value');
    if (target.checked) {
      this.value.push(targetValue);
      this.value.sort();
    } else {
      this.value = this.value.filter((el) => {
        return el !== targetValue;
      });
    }
  }

  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/
  /**
   * createCheckbox
   * @desc creates a checkbox element
   * @param {string} id html attr
   * @param {string} title the display title 
   * @param {any} value the value of the input
   * @returns {node} a checkbox element
   */
  #createCheckbox(id, title, value) {
    const html = `<div class="checkbox-item-container min-size">
      <input id="${id}" aria-label="${title}" type="checkbox" class="checkbox-item" data-value="${value}" data-name="${title}"/>
      <label for="${id}">${title}</label>
    </div>`

    const doc = parseHTMLFromString(html, true);
    return this.element.appendChild(doc[0]);
  }
}
