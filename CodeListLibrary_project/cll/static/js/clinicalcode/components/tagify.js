import FuzzyQuery from './fuzzyQuery.js';

/**
 * TAGIFY__DELAY
 * @desc Delay for keydown events
 */
const TAGIFY__DELAY = 1;

/**
 * TAGIFY__TIMEOUT
 * @desc Timeout after a tag has been added by pressing enter
 */
const TAGIFY__TIMEOUT = 10;

/**
 * TAGIFY__KEYCODES
 * @desc Keycodes used to navigate through the tag dropdown, and to add/remove tags
 */
const TAGIFY__KEYCODES = {
  // Add tag
  'ENTER': 13,
  // Remove tag
  'BACK': 8,
  // Navigate tag dropdown
  'DOWN': 40,
  'UP': 38,
};

/**
 * TAGIFY__TAG_OPTIONS
 * @desc Available options for the tagify component.
 *       These options are used as defaults and automatically added to the component
 *       if they are not overriden by the options parameter.
 */
const TAGIFY__TAG_OPTIONS = {
  // A predefined list of tags that can be used for autocomplete, or to control the input provided by the user
  'items': [ ],
  // Whether to use the value or the name keys for autocomplete and tag selected components
  'useValue': false,
  // Whether to perform autocomplete from a predefined list of items
  'autocomplete': false,
  // Whether to allow users to input duplicate tags
  'allowDuplicates': false,
  // Determines whether the user is restricted to the items within the predefined items list, or can input their own
  'restricted': false,
  // Determines whether to show tooltips
  //  [!] Note: This option requires tooltipFactory.js as a dependency
  'showTooltips': true,
};

/**
  * @class Tagify
  * @desc A class that transforms an input field into a tag component
  * @param {string/node} obj The ID of the input element or the input element itself.
  * @param {object} options An object that defines any of the optional parameters as described within TAGIFY__TAG_OPTIONS
  * @return {object} An interface to control the behaviour of the tag component.
  * 
  * [!] Note: After the addition or removal of a tag, a custom event is dispatched to
  *           a the Tagify instance's element through the 'TagChanged' hook
  * 
  * e.g.
  ```js
    import Tagify from '../components/tagify.js';

    const tags = [
      {
        name: 'SomeTagName',
        value: 'SomeTagValue',
      },
      {
        name: 'SomeTagName',
        value: 'SomeTagValue',
      }
    ];

    const tagComponent = new Tagify('phenotype-tags', {
      'autocomplete': true,
      'useValue': false,
      'allowDuplicates': false,
      'restricted': true,
      'items': tags,
    });
  ```
  * 
  */
export default class Tagify {
  constructor(obj, options, phenotype) {
    this.uuid = generateUUID();

    if (typeof obj === 'string') {
      this.id = id;
      this.element = document.getElementById(id);
    } else {
      this.element = obj;

      if (!isNullOrUndefined(this.element)) {
        this.id = this.element.getAttribute('id');
      }
    }

    if (!isNullOrUndefined(this.element)) {
      this.fieldName = this.element.getAttribute('data-field');
    }

    this.isBackspace = false;
    this.tags = [ ];
    this.currentFocus = -1;

    this.#initialise(options, phenotype);
  }

  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/  
  /**
   * getActiveTags
   * @desc method to retrieve current tag data
   * @returns {list} a list of objects describing active tags
   */
  getActiveTags() {
    return this.tags;
  }

  /*************************************
   *                                   *
   *               Setter              *
   *                                   *
   *************************************/  
  /**
   * addTag
   * @desc Adds a tag to the current list of tags
   * @param {string} name The name of the tag to add
   * @param {any} value The value of the tag to add
   * @return {object} Returns a tag object
   */
  addTag(name, value) {
    if (!stringHasChars(name)) {
      return false;
    }

    name = strictSanitiseString(name);
    value = typeof value === 'string' ? strictSanitiseString(value) : value;

    if (this.options.restricted) {
      const index = this.options.items.map(e => e.name.toLocaleLowerCase()).indexOf(name.toLocaleLowerCase());
      if (index < 0) {
        return false;
      }

      const data = this.options.items[index];
      name = data.name;
      value = data.value;
    }

    if (!this.options.allowDuplicates) {
      const index = this.tags.map(e => e.name.toLocaleLowerCase()).indexOf(name.toLocaleLowerCase());
      if (index >= 0) {
        const elem = this.tags[index].element;
        if (elem) {
          this.#wobbleElement(elem);
        }
        
        return false;
      }
    }

    const tag = this.#createTag(name, value);
    this.element.dispatchEvent(
      new CustomEvent('TagChanged', {
        detail: {
          controller: this,
          type: 'addition',
        }
      })
    );

    return tag;
  }
  
  /**
   * removeTag
   * @desc removes a tag from the current list of tags
   * @param {object} tag the tag to remove
   */
  removeTag(tag) {
    const name = tag.querySelector('.tag__name');
    if (this.options.showTooltips) {
      window.TooltipFactory.clearTooltips(tag.querySelector('button'));
    }
    this.tagbox.removeChild(tag);

    const index = this.tags.map(e => e.name).indexOf(name.textContent.trim());
    this.tags.splice(index, 1);

    this.#updateElement();
    this.element.dispatchEvent(
      new CustomEvent('TagChanged', {
        detail: {
          controller: this,
          type: 'removal',
        }
      })
    );
  }

  /**
   * destroy
   * @desc
   * Destroys the tagify component, but not the element itself 
   */
  destroy() {
    if (this.tagbox) {
      this.tagbox.parentNode.removeChild(this.tagbox);
    }

    delete this;
  }

  /**
   * getElement
   * @desc returns this instance's target element, which can be used to determine whether a tag
   *       has been removed/added at runtime through the 'TagChanged' hook
   * @returns {node} this instance's target element
   */
  getElement() {
    return this.element;
  }

  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/
  /**
   * onClick
   * @desc handles removing of elements through the remove button click event
   * @param {event} e the associated event
   */
  #onClick(e) {
    e.preventDefault();

    if (e.target.className == 'tag__remove') {
      this.removeTag(tryGetRootElement(e.target, 'tag'));
    }

    this.field.focus();
  }

  /**
   * onFocusLost
   * @desc when the input box loses focus
   * @param {event} e the associated event
   */
  #onFocusLost(e) {
    this.#deselectHighlighted();

    const target = e.relatedTarget;
    if (target && target.classList.contains('autocomplete-item')) {
      const name = target.getAttribute('data-name');
      this.addTag(name);
    }
    this.field.value = '';

    this.#clearAutocomplete();
    this.autocomplete.classList.remove('show');
  }

  /**
   * onKeyDown
   * @desc handles events assoc. with the input box receiving a key down event
   * @param {event} e the associated event
   */
  #onKeyDown(e) {
    setTimeout(() => {
      const target = e.target;
      if (e.target.id == this.uuid) {
        let name = target.value.trim();
        const code = e.which || e.keyCode;
        switch (code) {
          case TAGIFY__KEYCODES.ENTER: {
            e.preventDefault();
            e.stopPropagation();

            if (this.currentFocus >= 0) {
              name = this.#getFocusedName();
            }
            
            if (name === '') {
              this.#deselectHighlighted();
              break;
            }
            
            target.blur();
            target.value = '';
  
            this.addTag(name);
            this.#clearAutocomplete(true);
  
            if (this.timer)
              clearTimeout(this.timer);
            
            this.timer = setTimeout(() => {
              target.focus();
            }, TAGIFY__TIMEOUT);
          } break;
  
          case TAGIFY__KEYCODES.BACK: {
            if (name === '') {
              this.#clearAutocomplete(true);
  
              if (!this.isBackspace) {
                this.#popTag();
              }
            } else {
              if (this.options.autocomplete) {
                this.#tryPopulateAutocomplete(name);
              }
            }
          } break;
  
          case TAGIFY__KEYCODES.UP:
          case TAGIFY__KEYCODES.DOWN: {
            if (this.autocomplete.classList.contains('show')) {
              e.preventDefault();
              this.currentFocus += (code == TAGIFY__KEYCODES.UP ? -1 : 1);
              this.#focusAutocompleteElement();
            }
          } break;
  
          default: {
            this.#deselectHighlighted();
  
            if (this.options.autocomplete) {
              this.#tryPopulateAutocomplete(name);
            }
  
          } break;
        }
      }

      this.isBackspace = false;
    }, TAGIFY__DELAY)
  }

  /**
   * onKeyUp
   * @desc handles events assoc. with the input box receiving a key up event
   * @param {event} e the associated event
   */
  #onKeyUp(e) {

  }

  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/
  /**
   * initialise
   * @desc responsible for the main initialisation & render of this component
   * @param {dict} options the option parameter 
   * @param {dict|*} phenotype optional initialisation template
   */
  async #initialise(options, phenotype) {
    this.container = createElement('div', {
      'className': 'tags-root-container',
    });

    this.tagbox = createElement('div', {
      'className': 'tags-container',
    });

    this.autocomplete = createElement('div', {
      'className': 'tags-autocomplete-container filter-scrollbar',
    });

    this.field = createElement('input', {
      'type': 'text',
      'className': 'tags-input-field',
      'id': this.uuid,
      'placeholder': this.element.placeholder || '',
    });

    this.tagbox.appendChild(this.field);
    this.container.appendChild(this.tagbox);
    this.container.appendChild(this.autocomplete);
    this.element.type = 'hidden';
    this.element.parentNode.insertBefore(this.container, this.element.nextSibling);

    this.#buildOptions(options || { }, phenotype)
      .catch(e => console.error(e))
      .finally(() => {
        let callback;
        if (this.options?.onLoad && this.options.onLoad instanceof Function) {
          callback = this.options.onLoad(this);
        }

        this.#bindEvents();

        if (typeof callback === 'function') {
          callback(this);
        }
      });
  }

  /**
   * popTag
   * @desc responsible for popping the tag & rerendering when the user attempts to delete a tag
   *       through the input box using the backspace key
   */
  #popTag() {
    if (this.isBackspace)
      return;
    
    this.isBackspace = true;
    if (this.tags.length <= 0)
      return;
    
    const index = this.tags.length - 1;
    const tag = this.tags[index];
    if (!tag.element.classList.contains('tag__highlighted')) {
      tag.element.classList.add('tag__highlighted');
      return;
    }

    this.tags.splice(index, 1);
    this.tagbox.removeChild(tag.element);
  }

  /**
   * bindEvents
   * @desc binds the associated events to the rendered components
   */
  #bindEvents() {
    this.container.addEventListener('click', this.#onClick.bind(this), false);
    this.tagbox.addEventListener('focusout', this.#onFocusLost.bind(this), false);
    this.tagbox.addEventListener('keydown', this.#onKeyDown.bind(this), false);
    this.tagbox.addEventListener('keyup', this.#onKeyUp.bind(this), false);
  }

  /**
   * updateElement
   * @desc updates the element's value to maintain consistent relationship with class data
   */
  #updateElement() {
    const target = this.options.useValue ? 'value' : 'name';
    this.element.value = this.tags.map(e => e[target]).join(',');
  }

  /**
   * buildOptions
   * @desc private method to merge the expected options with the passed options - passed takes priority
   * @param {dict} options the option parameter 
   * @param {dict} phenotype the initialisation template
   */
  async #buildOptions(options, phenotype) {
    this.options = mergeObjects(options, TAGIFY__TAG_OPTIONS);

    const hasFieldName = !isStringEmpty(this.fieldName);
    const needsInitialiser = !isNullOrUndefined(phenotype) && (isNullOrUndefined(options?.items) || options?.items.length < 1);
    if (needsInitialiser && hasFieldName) {
      const parameters = new URLSearchParams({
        parameter: this.fieldName,
        template: phenotype.template.id,
      });
  
      const response = await fetch(
        `${getCurrentURL()}?` + parameters,
        {
          method: 'GET',
          headers: {
            'X-Target': 'get_options',
            'X-Requested-With': 'XMLHttpRequest',
            'Cache-Control': 'max-age=28800',
            'Pragma': 'max-age=28800',
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to retrieve tag box entities with Err<code: ${response.status}> and message:\n${String(response)}`);
      }

      const dataset = await response.json();
      if (!(dataset instanceof Object) || Array.isArray(dataset) || !Array.isArray(dataset?.result)) {
        throw new Error(`Expected tagify init data to be an object with a result array, got ${dataset}`);
      }

      this.options.items = dataset.result;
    }

    return;
  }

  /**
   * getFocusedName
   * @desc gets the name of the currently focused element
   * @return {string} focused element name
   */
  #getFocusedName() {
    const children = this.autocomplete.children;
    if (this.currentFocus < children.length) {
      return children[this.currentFocus].getAttribute('data-name');
    }

    return '';
  }

  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/
  /**
   * createTag
   * @desc creates a renderable tag component
   * @param {string} name 
   * @param {*} value 
   * @returns {node} the tag
   */
  #createTag(name, value) {
    const tag = createElement('div', {
      'className': 'tag',
      'data-value': value,
      'innerHTML': {
        src: `<span class="tag__name">${name}</span><button class="tag__remove" aria-label="Remove Tag ${name}">&times;</button>`,
        noSanitise: true,
      }
    });

    this.tagbox.insertBefore(tag, this.field);
    this.tags.push({
      'element': tag,
      'name': name,
      'value': value,
    });

    if (this.options.showTooltips) {
      window.TooltipFactory.addElement(tag.querySelector('button'), 'Remove Tag', 'up');
    }

    this.#updateElement();
    
    return tag;
  }

  /**
   * deselectHighlighted
   * @desc deselects the currently selected autocomplete item
   */
  #deselectHighlighted() {
    if (this.field.previousSibling) {
      this.field.previousSibling.classList.remove('tag__highlighted');
    }
  }

  /**
   * wobbleElement
   * @desc used to enact a wobble animation on a tag if it has been previously entered
   *       and the user is trying to add another instance of it
   * @param {node} elem the element to wobble
   */
  #wobbleElement(elem) {
    const method = getTransitionMethod();
    if (typeof method === 'undefined')
      return;
    
    elem.addEventListener(method, function handle(e) {
      elem.classList.remove('tag__wobble');
      elem.removeEventListener(e.type, handle, false);
    }, false);

    elem.classList.add('tag__wobble');
  }

  /**
   * clearAutocomplete
   * @desc clears the autocomplete list
   * @param {boolean} hide whether to hide the autocomplete box
   */
  #clearAutocomplete(hide) {
    this.currentFocus = -1;

    while (this.autocomplete.lastElementChild) {
      this.autocomplete.removeChild(this.autocomplete.lastElementChild);
    }

    if (hide) {
      this.autocomplete.classList.remove('show');
    }
  }

  /**
   * popFocusedElement
   * @desc pops the currently focused element by removing all __highlighted classes from each element
   */
  #popFocusedElement() {
    const children = this.autocomplete.children;
    for (let i = 0; i < children.length; ++i) {
      children[i].classList.remove('autocomplete-item__highlighted');
    }
  }
  
  /**
   * focusAutoCompleteElement
   * @desc focuses an element in the autocomplete list by selecting the element by its index (based on sel id)
   */
  #focusAutocompleteElement() {
    this.#popFocusedElement();
    
    const children = this.autocomplete.children;
    const childLength = children.length;
    this.currentFocus = this.currentFocus < 0 ? (childLength - 1) : (this.currentFocus >= childLength ? 0 : this.currentFocus);

    if (this.currentFocus < childLength) {
      const element = children[this.currentFocus];
      element.classList.add('autocomplete-item__highlighted');

      this.autocomplete.scrollTop = element.offsetTop;
    }
  }

  /**
   * generateAutocompleteElements
   * @desc generates all elements within the autocomplete container
   * @param {array} results the results to render
   */
  #generateAutocompleteElements(results) {
    for (let i = 0; i < results.length; ++i) {
      const data = results[i];
      const item = createElement('button', {
        'className': 'autocomplete-item',
        'data-value': data.value,
        'data-name': data.name,
      });

      const text = createElement('span', {
        'className': 'autocomplete-item__title',
        'innerText': data.name,
      });

      item.appendChild(text);
      this.autocomplete.appendChild(item);
    }
  }

  /**
   * tryPopulateAutocomplete
   * @desc tries to determine which elements need to be rendered through fuzzymatching,
   *       and then renders the autocomplete elements
   * @param {string} value the search term to consider
   * @returns 
   */
  #tryPopulateAutocomplete(value) {
    if (value === '' || this.options.items.length <= 0) {
      this.#clearAutocomplete(true);
      return;
    }

    if (!this.haystack) {
      this.haystack = this.options.items.map(e => e.name);
    }
    
    let results = FuzzyQuery.Search(this.haystack, value, FuzzyQuery.Results.SORT, FuzzyQuery.Transformers.IgnoreCase);
    results.sort((a, b) => {
      if (a.score === b.score) {
        return 0;
      } else if (a.score > b.score) {
        return 1;
      } else if (a.score < b.score) {
        return -1;
      }
    });

    results = results.map((e) => {
      const item = this.options.items.find(x => x.name.toLocaleLowerCase() === e.item.toLocaleLowerCase());
      return item;
    });
    
    if (results.length > 0) {
      this.#clearAutocomplete(false);
      this.autocomplete.classList.add('show');
      this.#generateAutocompleteElements(results);

      return;
    }

    this.#clearAutocomplete(true);
  }
}
