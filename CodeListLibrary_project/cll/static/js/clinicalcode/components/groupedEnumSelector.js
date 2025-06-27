/**
 * @class GroupedEnum
 * @desc handler for GroupedEnum components, where:
 *        - Selection of individual values via checkboxes
 *        - Selection of another value through a combination of checkboxes
 *        - Emulates radiobutton-like behaviour in all other cases
 * @param {string/node} obj The ID of the input element or the input element itself
 * @param {object} data Should contain both (1) the available options and (2) the available groups
 * @return {object} An interface to control the behaviour of the component
 * 
 */
export default class GroupedEnum {
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

    this.value = null;
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
      this.value = null;

      const checked = this.element.querySelectorAll('input:checked')
      for (let i = 0; i < checked.length; ++i) {
        checked[i].checked = false;
      }

      return this;
    }

    const matchedGroup = this.data?.properties.find(x => x.result === value);
    this.value = value;

    if (!isNullOrUndefined(matchedGroup)) {
      const inputs = this.element.querySelectorAll('input');
      for (let i = 0; i < inputs.length; ++i) {
        let val = inputs[i].getAttribute('data-value');
        if (matchedGroup?.when.includes(val)) {
          inputs[i].checked = true;
          continue
        }
        inputs[i].checked = false;
      }

      return this;
    }

    const inputs = this.element.querySelectorAll('input');
    for (let i = 0; i < inputs.length; ++i) {
      let val = inputs[i].getAttribute('data-value');
      inputs[i].checked = val === value;
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
      const properties = this.data?.properties
      if (!isNullOrUndefined(properties)) {
        const group = properties.find(x => x.result == option.value);   
        if (!isNullOrUndefined(group)) {
          continue
        }
      }

      const item = this.#createCheckbox(
        `${option.name}-${option.value}`,
        option.name,
        option.value
      );

      // Assign changed behaviour
      const checkbox = item.querySelector('input');
      checkbox.addEventListener('change', this.#onChangeCallback.bind(this));
    }

    // Assign default value
    let value = this.data?.value?.[0]?.value;
    if (!isNullOrUndefined(value)) {
      this.setValue(value);
      return this;
    }

    const defaultValue = this.element.getAttribute('data-default');
    if (!isNullOrUndefined(defaultValue)) {
      this.setValue(defaultValue);
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
    const checked = this.element.querySelectorAll('input:checked');
    const selectedValues = Array.prototype.slice.call(checked)
      .reduce((res, node) => {
        const item = this.data?.options?.find?.(x => x.value == node.getAttribute('data-value'));
        if (isNullOrUndefined(item)) {
          node.checked = false;
          return res;
        }

        res.push(item.value);
        return res;
      }, []);

    // Det. groups, if any
    let matchedGroup;
    let selectedGroup;

    const target = e.target;
    const properties = this.data?.properties;
    const singleSelected = selectedValues.length === 1;
    if (!isNullOrUndefined(properties)) {
      for (let i = 0; i < properties.length; ++i) {
        let group = properties[i];
        if (isNullOrUndefined(group?.when)) {
          continue;
        }

        if (isArrayEqual(selectedValues, group?.when)) {
          matchedGroup = group;
          break;
        }

        if (!target.checked) {
          const test = [...selectedValues];
          const indx = target.getAttribute('data-value');
          if (!test.includes(indx)) {
            test.push(indx);
          }

          if (isArrayEqual(test, group.when)) {
            selectedGroup = group;
          }
        }
      }
    }

    // Select a group if a match is found
    if (!isNullOrUndefined(matchedGroup)) {
      for (let i = 0; i < checked.length; ++i) {
        let checkbox = checked[i];
        let value = checkbox.getAttribute('data-value');
        if (matchedGroup?.when.includes(value)) {
          continue;
        }

        checkbox.checked = false;
      }

      this.value = matchedGroup?.result;
      return;
    }

    // None found, clear current selection & apply state of our current checkbox
    let desiredValue;
    if (target.checked) {
      desiredValue = target.getAttribute('data-value');
    } else if (singleSelected && selectedGroup) {
      desiredValue = selectedValues.shift();
    } else {
      desiredValue = null;
    }

    for (let i = 0; i < checked.length; ++i) {
      let checkbox = checked[i];
      if (!isNullOrUndefined(desiredValue) && singleSelected && selectedGroup) {
        if (target !== checkbox && !selectedGroup.when.includes(checkbox.getAttribute('data-value'))) {
          checkbox.checked = false;
        }

        continue;
      }

      if (target === checkbox) {
        continue;
      }

      checkbox.checked = false;
    }
    this.value = desiredValue;
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
