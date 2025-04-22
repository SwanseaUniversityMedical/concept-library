import FuzzyQuery from '../../../components/fuzzyQuery.js';

import { Autocomplete } from '../../../components/autocomplete.js';


/**
 * @desc an object specifying templates expected to be defined by the `template` constructor args
 * @type {Record<string, Array<string>}
 * @constant
 */
const EXPECTED_TEMPLATES = {
  form: ['autocomplete', 'selector'],
  OrgAuthority: ['table', 'row'],
};


/**
 * Class to render the `Organisation.brands::OrganisationAuthority` component
 * 
 * @note ideally we would be extending from a parent class but ES6 doesn't support protected members natively
 * 
 * @class
 * @constructor
 */
export class OrgAuthoritySelector {
  /**
   * @desc default constructor props
   * @type {Record<string, any>}
   * @static
   * @constant
   * 
   */
  static #DefaultOpts = {
    field: null,
    value: null,
    options: {
      brand: [],
    },
    element: null,
    templates: null,
  };

  /**
   * @desc
   * @type {HTMLElement}
   * @public
   */
  element = null;

  /**
   * @desc
   * @type {object}
   * @private
   */
  #props = { };

  /**
   * @desc
   * @type {Record<string, HTMLElement>}
   * @private
   */
  #layout = {};

  /**
   * @desc
   * @type {Record<string, Record<string, HTMLElement>}
   * @private
   */
  #templates = { };

  /**
   * @desc
   * @type {Array<Function>}
   * @private
   */
  #disposables = [];

  /**
   * @param {Record<string, any>} [opts] constructor arguments; see {@link OrgAuthoritySelector.#DefaultOpts}
   */
  constructor(opts) {
    opts = isRecordType(opts) ? opts : { };
    opts = mergeObjects(opts, OrgAuthoritySelector.#DefaultOpts, true);
    OrgAuthoritySelector.#ValidateOpts(opts);

    this.#initialise(opts);
  }


  /*************************************
   *                                   *
   *              Static               *
   *                                   *
   *************************************/
  /**
   * @desc validates constructor opts
   * @static
   * @private
   * 
   * @param {Record<string, any>} [opts] constructor arguments; see {@link OrgAuthoritySelector.#DefaultOpts}
   */
  static #ValidateOpts(opts) {
    if (!isRecordType(opts.field)) {
      throw new Error('Expected `field` as valid `Record<string, any>`');
    }

    if (!isRecordType(opts.options)) {
      throw new Error('Expected `options` as valid `Record<string, any>`');
    }

    if (!isHtmlObject(opts.element) && !(typeof opts.element === 'string' && stringHasChars(opts.element))) {
      throw new Error('Expected `element` to specify either (a) a HTMLElement, or (b) a string specifying a query selector');
    }

    if (!isRecordType(opts.templates)) {
      throw new Error('Expected `templates` to specify a `Record<string, string|HTMLElement>` describing the HTML templates used by this component');
    }

    let missing = findMissingComponents(opts.templates, EXPECTED_TEMPLATES);
    if (Array.isArray(missing) && missing.length > 0) {
      missing = missing.join(', ');
      throw new Error(`The specified \`templates\` record does not define the following required templates: ${missing}`);
    }
  }


  /*************************************
   *                                   *
   *              Public               *
   *                                   *
   *************************************/
  getValue() {
    return this.value.map(x => {
      const elem = { ...x };
      delete elem.elements;
      return elem;
    });
  }

  getDataValue() {
    return this.value.map(x => ({ brand_id: x.brand.id, can_post: !!x.can_post, can_moderate: !!x.can_moderate }));
  }

  dispose() {
    let disposable;
    for (let i = this.#disposables.length; i > 0; i--) {
      disposable = this.#disposables.pop();
      if (typeof disposable !== 'function') {
        continue;
      }

      disposable();
    }
  }


  /*************************************
   *                                   *
   *            Renderables            *
   *                                   *
   *************************************/
  #addAuthority(authority) {
    if (!isRecordType(authority)) {
      return false;
    }

    const brand = authority.brand;
    if (!isRecordType(brand) || typeof brand.id !== 'number' || typeof brand.name !== 'string') {
      return false;
    }

    let canPost = authority.can_post;
    if (isNullOrUndefined(canPost)) {
      canPost = false;
      authority.can_post = canPost;
    }

    let canModerate = authority.can_moderate;
    if (isNullOrUndefined(canModerate)) {
      canModerate = false;
      authority.can_moderate = canModerate;
    }

    let authElements;
    composeTemplate(this.#templates.OrgAuthority.row, {
      params: {
        brand: brand.name,
        brandPk: brand.id,
        canPostValue: canPost,
        canModerateValue: canModerate,
      },
      sanitiseTemplate: false,
      parent: this.#layout.tableBody,
      render: (elems) => {
        const row = elems[0];
        const button = row.querySelector('[data-role="brand-delete-btn"]');
        const chkPost = row.querySelector('[data-role="brand-post-checkbox"]');
        const chkModerate = row.querySelector('[data-role="brand-moderate-checkbox"]');
        authElements = { row, button, chkPost, chkModerate };

        chkPost.checked = canPost;
        chkModerate.checked = canModerate;
      }
    });
    authority.elements = authElements;

    const checkboxToggleHnd = this.#checkboxToggleHandle.bind(this);
    const removeAuthorityHnd = this.#removeAuthorityHandle.bind(this);

    const { button, chkPost, chkModerate } = authElements;
    button.addEventListener('click', removeAuthorityHnd);
    chkPost.addEventListener('change', checkboxToggleHnd);
    chkModerate.addEventListener('change', checkboxToggleHnd);

    return true;
  }

  #render() {
    const props = this.#props
    const layout = this.#layout;

    const brandOptions = Array.isArray(props?.options?.brand) ? props.options.brand : [];
    const brandHaystack = brandOptions.map(x => x.name);

    const autocomplete = new Autocomplete({
      rootNode: layout.autocomplete.container,
      inputNode: layout.autocomplete.input,
      resultsNode: layout.autocomplete.results,
      shouldAutoSelect: false,
      searchFn: (input) => {
        if (input.length < 1) {
          return [];
        }
  
        return FuzzyQuery.Search(
          brandHaystack,
          input,
          FuzzyQuery.Results.SORT,
          FuzzyQuery.Transformers.IgnoreCase
        )
          .sort((a, b) => {
            if (a.score === b.score) {
              return 0;
            } else if (a.score > b.score) {
              return 1;
            } else if (a.score < b.score) {
              return -1;
            }
          })
          .map(x => x.item);
      },
    });

    this.#disposables.push(() => autocomplete.dispose());

    if (brandOptions.length > 0) {
      const authAddHnd = this.#addAuthorityHandle.bind(this);
      layout.autocomplete.button.addEventListener('click', authAddHnd);

      this.#disposables.push(() => {
        layout.autocomplete.button.removeEventListener('click', authAddHnd);
      });
    }

    for (let i = 0; i < this.value.length; ++i) {
      const success = this.#addAuthority(this.value[i]);
      if (success) {
        continue;
      }

      console.warn('[OrgSelector] Failed to add authority:', this.value[i]);
      this.value.splice(i, 1);
    }
    this.#toggleContentVisibility();
  }

  #toggleContentVisibility() {
    const { content, empty } = this.#layout;

    const isVisible = this.value.length > 0;
    empty.setAttribute('data-visible', !isVisible);
    content.setAttribute('data-visible', isVisible);
  }


  /*************************************
   *                                   *
   *              Events               *
   *                                   *
   *************************************/
  #addAuthorityHandle(e) {
    e.preventDefault();

    const { input } = this.#layout.autocomplete;
    const brandOptions = this.#props.options.brand;

    let inputValue = input.value;
    input.value = '';

    if (!stringHasChars(inputValue)) {
      return;
    }

    inputValue = brandOptions.find(x => x.name.toLocaleLowerCase() === inputValue.toLocaleLowerCase());
    if (isNullOrUndefined(inputValue)) {
      return;
    }

    if (!!this.value.find(x => x.brand.id === inputValue.pk)) {
      return;
    }

    const authority = { brand: { id: inputValue.pk, name: inputValue.name } };
    const success = this.#addAuthority(authority);
    if (success) {
      this.value.push(authority);
      this.#toggleContentVisibility();
    }
  }

  #checkboxToggleHandle(e) {
    const target = document.activeElement;

    let rowRefPk = target.getAttribute('data-ref');
    rowRefPk = parseInt(rowRefPk);
    if (typeof rowRefPk !== 'number' || isNaN(rowRefPk)) {
      return;
    }

    const index = this.value.findIndex(x => x.brand.id == rowRefPk);
    const authority = index >= 0 ? this.value[index] : null;
    if (!authority) {
      return;
    }

    const column = target.getAttribute('data-column');
    authority[column] = !!target.checked;
  }

  #removeAuthorityHandle(e) {
    const target = document.activeElement;
    e.preventDefault();

    let rowRefPk = target.getAttribute('data-ref');
    rowRefPk = parseInt(rowRefPk);
    if (typeof rowRefPk !== 'number' || isNaN(rowRefPk)) {
      return;
    }

    const index = this.value.findIndex(x => x.brand.id == rowRefPk);
    const authority = index >= 0 ? this.value[index] : null;
    if (!authority) {
      return;
    }
    this.value.splice(index, 1);
    this.#toggleContentVisibility();

    const elements = authority.elements;
    if (!isRecordType(elements)) {
      return;
    }

    for (const key in elements) {
      const elem = elements[key];
      if (!isHtmlObject(elem)) {
        continue;
      }

      elem.remove();
    }
  }


  /*************************************
   *                                   *
   *            Initialiser            *
   *                                   *
   *************************************/
  #initialise(opts) {
    let element = opts.element;
    delete opts.element;

    if (typeof element === 'string') {
      element = document.querySelector(element);
    }

    if (!isHtmlObject(element)) {
      throw new Error(`Failed to resolve ${Object.getPrototypeOf(this).constructor.name} element`);
    }

    const templates = opts.templates;
    this.value = opts.value;
    this.element = element;
    delete opts.value;

    this.#props = opts;
    this.#templates = templates;
    delete opts.templates;

    const field = opts.field;
    const layout = this.#layout;
    composeTemplate(templates.form.selector, {
      params: {
        key: field.key,
        cls: '',
        help: field.help ?? '',
        title: field.label ?? 'Brand Authority',
        owner: 'OrgAuthoritySelector',
        required: field.required ? 'required="true"' : '',
        emptyMessage: 'You haven\'t added any Brands yet.',
      },
      parent: element,
      render: (elems) => {
        const group = elems[0];
        layout.group = group;

        const idents = group.querySelectorAll('[data-identifier]');
        for (let i = 0; i < idents.length; ++i) {
          const elem = idents[i];
          const ident = elem.getAttribute('data-identifier');
          if (!stringHasChars(ident)) {
            continue;
          }

          layout[ident] = elem;
        }
      }
    });

    composeTemplate(templates.OrgAuthority.table, {
      debug: true,
      sanitiseTemplate: false,
      parent: layout.table,
      render: (elems) => {
        const [head, body] = elems;
        layout.tableHead = head;
        layout.tableBody = body;
      }
    });

    composeTemplate(templates.form.autocomplete, {
      params: {
        id: 'brand-auto-selector',
        searchValue: '',
        searchLabel: 'Find Brand to add',
        searchPlaceholder: 'Search Brand...',
        btnId: 'add-authority-btn',
        btnIcon: 'folder-plus',
        btnTitle: 'Add Selected Brand',
        btnContent: 'Add',
      },
      parent: layout.header,
      render: (elems) => {
        const matched = elems[0].parentElement.querySelectorAll('[data-role^="autocomplete-"]');
        const objects = { };
        layout.autocomplete = objects;

        for (let i = 0; i < matched.length; ++i) {
          const obj = matched[i]
          const drole = obj.getAttribute('data-role').split('-').pop();
          objects[drole] = obj;
        }
      }
    });

    if (!Array.isArray(this.value)) {
      this.value = [];
    }
    this.#render();
  }
};
