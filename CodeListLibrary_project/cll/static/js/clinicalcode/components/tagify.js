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
 * TAGIFY__TAG_OPTIONS
 * @desc Available options for the tagify component.
 *       These options are used as defaults and automatically added to the component
 *       if they are not overriden by the options parameter.
 */
const TAGIFY__TAG_OPTIONS = {
  // A predefined list of tags that can be used for autocomplete, or to control the input provided by the user
  items: [ ],
  // Whether to use the value or the name keys for autocomplete and tag selected components
  useValue: false,
  // Whether to perform autocomplete from a predefined list of items
  autocomplete: false,
  // Whether to allow users to input duplicate tags
  allowDuplicates: false,
  // Determines whether to show tooltips
  //  [!] Note: This option requires tooltipFactory.js as a dependency
  showTooltips: true,
  // Component behaviour
  behaviour: {
    // Determines whether the user is restricted to the items within the predefined items list, or can input their own
    freeform: false,
    // Describes how to format the tag when displaying it
    format: {
      component: '{name}',
    },
  },
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
  * @example
  * import Tagify from '../components/tagify.js';
  * 
  * const tags = [
  *   {
  *     name: 'SomeTagName',
  *     value: 'SomeTagValue',
  *   },
  *   {
  *     name: 'SomeTagName',
  *     value: 'SomeTagValue',
  *   }
  * ];
  * 
  * const tagComponent = new Tagify('phenotype-tags', {
  *   items: tags,
  *   useValue: false,
  *   restricted: true,
  *   autocomplete: true,
  *   allowDuplicates: false,
  * });
  * 
  */
export default class Tagify {
  /**
   * @desc
   * @type {Array<Function>}
   * @private
   */
  #disposables = [];

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

    this.tags = [];
    this.currentFocus = -1;
    this.isBackspaceState = false;

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
   * @returns {Array<Object>} a list of objects describing active tags
   */
  getActiveTags() {
    return this.tags;
  }

  /**
   * getDataValue
   * @desc method to retrieve current tag data array
   * @returns {Array} a list of data value(s)
   */
  getDataValue() {
    if (!this.options?.behaviour?.freeform) {
      return this.tags.reduce((res, x) => {
        if (!isNullOrUndefined(x?.value)) {
          res.push(x.value);
        }

        return res;
      }, []);
    }

    return this.tags.reduce((res, x) => {
      res.push({ name: x?.name, value: typeof x?.value === 'number' ? x.value : null });
      return res;
    }, []);
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

    if (!this.options?.behaviour?.freeform) {
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
   * dispose
   * @desc disposes events & objs assoc. with this cls
   */
  dispose() {
    let disposable;
    for (let i = this.#disposables.length; i > 0; i--) {
      disposable = this.#disposables.pop();
      if (typeof disposable !== 'function') {
        continue;
      }

      disposable();
    }

    this.destroy();
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
    const trg = document.activeElement;
    if (isNullOrUndefined(this.container) || isNullOrUndefined(trg) || !this.container.contains(trg)) {
      return;
    }
    e.preventDefault();

    if (trg.className == 'tag__remove') {
      this.removeTag(tryGetRootElement(trg, '.tag'));
    }
    this.field.focus();
  }

  /**
   * onFocusIn
   * @desc when the input box is focused by the client
   * 
   * @param {event} e the associated event
   */
  #onFocusIn(e) {
    this.#deselectHighlighted();

    if (this.options.autocomplete) {
      this.#tryPopulateAutocomplete();
    }
  }

  /**
   * onFocusLost
   * @desc when the input box loses focus
   * @param {event} e the associated event
   */
  #onFocusLost(e) {
    this.#deselectHighlighted();

    const { relatedTarget } = e;
    if (!!relatedTarget && this.autocomplete.contains(relatedTarget) && relatedTarget.classList.contains('autocomplete-item')) {
      const name = relatedTarget.getAttribute('data-name');
      this.addTag(name);
    }
    this.field.value = '';
    this.#clearAutocomplete();
    this.autocomplete.classList.remove('show');
  }

  /**
   * onKeyDown
   * @desc handles events assoc. with the input box receiving a key down event
   * 
   * @param {event} e the associated event
   */
  #onKeyDown(e) {
    setTimeout(() => {
      const target = e.target;
      if (e.target.id == this.uuid) {
        let name = target.value.trim();

        const code = e.code;
        switch (code) {
          case 'Enter':
          case 'NumpadEnter': {
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

          case 'Backspace': {
            if (name === '') {
              this.#clearAutocomplete(true);

              if (!this.isBackspaceState) {
                this.#popTag();
              }

              break;
            }

            if (this.options.autocomplete) {
              this.#tryPopulateAutocomplete(name);
            }
          } break;

          case 'ArrowUp':
          case 'ArrowDown': {
            if (this.autocomplete.classList.contains('show')) {
              e.preventDefault();
              this.currentFocus += (code === 'ArrowUp' ? -1 : 1);
              this.#focusAutocompleteElement();
            }
          } break;

          case 'Tab':
            this.#deselectHighlighted();
            this.#clearAutocomplete(true);
            if (!e.shiftKey) {
              focusNextElement(this.field, 'next');
            }
            break;

          default: {
            this.#deselectHighlighted();

            if (this.options.autocomplete) {
              this.#tryPopulateAutocomplete(name);
            }
          } break;
        }
      }

      this.isBackspaceState = false;
    }, TAGIFY__DELAY)
  }

  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/
  /**
   * initialise
   * @desc responsible for the main initialisation & render of this component
   * 
   * @param {dict} options the option parameter 
   * @param {dict|*} phenotype optional initialisation template
   */
  async #initialise(options, phenotype) {
    this.container = createElement('div', {
      className: 'tags-root-container',
    });

    this.tagbox = createElement('div', {
      className: 'tags-container',
    });

    this.autocomplete = createElement('div', {
      className: 'tags-autocomplete-container filter-scrollbar',
    });

    this.field = createElement('input', {
      id: this.uuid,
      type: 'text',
      className: 'tags-input-field',
      placeholder: this.element.placeholder || '',
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
    if (this.isBackspaceState) {
      return;
    }

    this.isBackspaceState = true;
    if (this.tags.length <= 0) {
      return;
    }

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
    this.field.addEventListener('focusin', this.#onFocusIn.bind(this), false);
    this.tagbox.addEventListener('focusout', this.#onFocusLost.bind(this), false);
    this.tagbox.addEventListener('keydown', this.#onKeyDown.bind(this), false);

    const clickHnd = this.#onClick.bind(this);
    document.addEventListener('click', clickHnd);

    this.#disposables.push(() => {
      document.removeEventListener('click', clickHnd)
    });
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
    options = isRecordType(options) ? options : { };
    this.options = mergeObjects(options, TAGIFY__TAG_OPTIONS, true, true);

    const hasFieldName = !isStringEmpty(this.fieldName);
    const needsInitialiser = !isNullOrUndefined(phenotype) && (isNullOrUndefined(options?.items) || options?.items.length < 1);
    if (needsInitialiser && hasFieldName) {
      const parameters = new URLSearchParams({
        parameter: this.fieldName,
        template: phenotype.template.id,
      });

      let hasWarnedClient = false;
      const response = await fetchWithCtrl(
        `${getCurrentURL()}?` + parameters,
        {
          method: 'GET',
          headers: {
            'X-Target': 'get_options',
            'X-Requested-With': 'XMLHttpRequest',
            'Cache-Control': 'max-age=300',
            'Pragma': 'max-age=300',
          },
        },
        {
          retries: 5,
          backoff: 100,
          onRetry: (retryCount, remainingTries) => {
            if (!hasWarnedClient && retryCount >= 2) {
              hasWarnedClient = true;
              window.ToastFactory.push({
                type: 'danger',
                message: `We're struggling to connect to the server, if this persists you might not be able to save the form.`,
                duration: 3500,
              });
            }
          },
          onError: (_err, _retryCount, remainingTries) => {
            if (hasWarnedClient && remainingTries < 1) {
              window.ToastFactory.push({
                type: 'danger',
                message: `We've not been able to connect to the server, please refresh the page and try again.`,
                duration: 7000,
              });
            }

            return true;
          },
          beforeAccept: (response, _retryCount, _remainingTries) => response.ok,
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to retrieve tag box entities with Err<code: ${response.status}> and message:\n${String(response)}`);
      }

      const dataset = await response.json();
      if (!(dataset instanceof Object) || Array.isArray(dataset) || !Array.isArray(dataset?.result)) {
        throw new Error(`Expected tagify init data to be an object with a result array, got ${dataset}`);
      }

      if (hasWarnedClient) {
        window.ToastFactory.push({
          type: 'success',
          message: `We have reestablished a connection with the server.`,
          duration: 2000,
        });
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

  /**
   * tryFmtName
   * @desc attempts to format the tag item per the template field info
   * 
   * @param {string|object} data the data assoc. with the tag
   * 
   * @return {string} element name
   */
  #tryFmtName(data) {
    let format = this.options?.behaviour?.format;
    format = isRecordType(format) && stringHasChars(format?.component)
      ? format.component
      : '{name}';

    let params;
    if (isRecordType(data)) {
      params = data;
    } else {
      params = { name: data };
    }

    let res;
    try {
      res = pyFormat(format, params);
    } catch (e) {
      res = stringHasChars(params?.name) ? params.name : 'TAG';
    }

    return res;
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
    let label = this.options.items.find(x => x.name.toLocaleLowerCase() === name.toLocaleLowerCase());
    if (!isNullOrUndefined(label)) {
      label = this.#tryFmtName(label);
    } else {
      label = name;
    }

    const tag = createElement('div', {
      data: { value: value },
      className: 'tag',
      innerHTML: {
        src: `<span class="tag__name">${label}</span><button class="tag__remove" aria-label="Remove Item">&times;</button>`,
        noSanitise: true,
      },
    });

    this.tagbox.insertBefore(tag, this.field);
    this.tags.push({
      name: name,
      value: value,
      element: tag,
    });

    if (this.options.showTooltips) {
      window.TooltipFactory.addElement(tag.querySelector('button'), 'Remove Item', 'up');
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
    if (typeof method === 'undefined') {
      return;
    }

    elem.addEventListener(method, (e) => elem.classList.remove('tag__wobble'), { once: true });
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

      if (!isScrolledIntoView(element, this.autocomplete, element.offsetHeight*0.5)) {
        this.autocomplete.scrollTop = element.offsetTop;
      }
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
      createElement('a', {
        class: 'autocomplete-item',
        href: '#',
        dataset: {
          name: data.name,
          value: data.value,
        },
        childNodes: [
          createElement('span', {
            className: 'autocomplete-item__title',
            innerText: this.#tryFmtName(data),
          })
        ],
        parent: this.autocomplete
      });
    }
  }

  /**
   * tryPopulateAutocomplete
   * @desc tries to determine which elements need to be rendered through fuzzymatching,
   *       and then renders the autocomplete elements
   * 
   * @param {string} [value=''] the search term to consider
   * 
   * @returns 
   */
  #tryPopulateAutocomplete(value = '') {
    if (this.options.items.length < 1) {
      this.#clearAutocomplete(true);
      return;
    }

    let results;
    if (stringHasChars(value)) {
      if (!this.haystack) {
        this.haystack = this.options.items.map(e => e.name);
      }

      results = FuzzyQuery.Search(this.haystack, value, FuzzyQuery.Results.SORT, FuzzyQuery.Transformers.IgnoreCase);
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
    } else {
      results = this.options.items.slice(0, this.options.items.length);
    }

    if (results.length > 0) {
      this.#clearAutocomplete(false);
      this.autocomplete.classList.add('show');
      this.#generateAutocompleteElements(results);
      return;
    }

    this.#clearAutocomplete(true);
  }
}
