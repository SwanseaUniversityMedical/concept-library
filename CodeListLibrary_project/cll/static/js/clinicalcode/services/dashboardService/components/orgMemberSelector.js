import FuzzyQuery from '../../../components/fuzzyQuery.js';

import { Autocomplete } from '../../../components/autocomplete.js';


/**
 * @desc an object specifying templates expected to be defined by the `template` constructor args
 * @type {Record<string, Array<string>}
 * @constant
 */
const EXPECTED_TEMPLATES = {
  form: ['autocomplete', 'selector'],
  OrgMember: ['table', 'row'],
};


/**
 * Class to render the `Organisation.members::OrganisationMember` component
 * 
 * @note ideally we would be extending from a parent class but ES6 doesn't support protected members natively
 * 
 * @class
 * @constructor
 */
export class OrgMemberSelector {
  /**
   * @desc default constructor props
   * @type {Record<string, any>}
   * @static
   * @constant
   * 
   */
  static #DefaultOpts = {
    field: null,
    value: [],
    options: {
      user: [],
      role: [],
    },
    element: null,
    template: null,
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
   * @param {Record<string, any>} [opts] constructor arguments; see {@link OrgMemberSelector.#DefaultOpts}
   */
  constructor(opts) {
    opts = isRecordType(opts) ? opts : { };
    opts = mergeObjects(opts, OrgMemberSelector.#DefaultOpts, true);
    OrgMemberSelector.#ValidateOpts(opts);

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
   * @param {Record<string, any>} [opts] constructor arguments; see {@link OrgMemberSelector.#DefaultOpts}
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
    return this.value.map(x => ({ user_id: x.user.id, role: x.role }));
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
  #addMember(member) {
    if (!isRecordType(member)) {
      return false;
    }

    const user = member.user;
    if (!isRecordType(user) || typeof user.id !== 'number' || typeof user.username !== 'string') {
      return false;
    }

    const roleOptions = this.#props.options.role;
    if (typeof member.role !== 'number' || !roleOptions.find(x => x.pk === member.role)) {
      member.role = 0;
    }

    let memberElements;
    composeTemplate(this.#templates.OrgMember.row, {
      params: {
        userPk: member.user.id,
        username: member.user.username,
      },
      sanitiseTemplate: false,
      parent: this.#layout.tableBody,
      render: (elems) => {
        const row = elems[0];
        const select = row.querySelector('[data-role="user-role-select"]');
        const button = row.querySelector('[data-role="user-delete-btn"]');
        memberElements = { row, select, button };

        let selectedIndex;
        for (let i = 0; i < roleOptions.length; ++i) {
          let opt = roleOptions[i];
          selectedIndex = opt.pk === member.role ? i : selectedIndex;

          opt = createElement('option', {
            innerText: opt.name,
            attributes: {
              value: opt.pk.toString(),
              selected: selectedIndex === i,
            },
            parent: select,
          });
        }
        select.selectedIndex = selectedIndex;
      }
    });
    member.elements = memberElements;

    const roleSelectHnd = this.#roleSelectHandle.bind(this);
    const removeMemberHnd = this.#removeMemberHandle.bind(this);

    const { select, button } = memberElements;
    select.addEventListener('change', roleSelectHnd);
    button.addEventListener('click', removeMemberHnd);

    return true;
  }

  #render() {
    const props = this.#props
    const layout = this.#layout;

    const userOptions = Array.isArray(props?.options?.user) ? props.options.user : [];
    const userHaystack = userOptions.map(x => x.name);

    const autocomplete = new Autocomplete({
      rootNode: layout.autocomplete.container,
      inputNode: layout.autocomplete.input,
      resultsNode: layout.autocomplete.results,
      searchFn: (input) => {
        if (input.length < 1) {
          return [];
        }
  
        return FuzzyQuery.Search(
          userHaystack,
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
      shouldAutoSelect: true,
    });

    this.#disposables.push(() => autocomplete.dispose());

    if (userOptions.length > 0) {
      const memberAddHnd = this.#addMemberHandle.bind(this);
      layout.autocomplete.button.addEventListener('click', memberAddHnd);

      this.#disposables.push(() => {
        layout.autocomplete.button.removeEventListener('click', memberAddHnd);
      });
    }

    for (let i = 0; i < this.value.length; ++i) {
      const success = this.#addMember(this.value[i]);
      if (success) {
        continue;
      }

      console.warn('[OrgSelector] Failed to add member:', this.value[i]);
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
  #addMemberHandle(e) {
    e.preventDefault();

    const { input } = this.#layout.autocomplete;
    const userOptions = this.#props.options.user;

    let inputValue = input.value;
    input.value = '';

    if (!stringHasChars(inputValue)) {
      return;
    }

    inputValue = userOptions.find(x => x.name.toLocaleLowerCase() === inputValue.toLocaleLowerCase());
    if (isNullOrUndefined(inputValue)) {
      return;
    }

    if (!!this.value.find(x => x.user.id === inputValue.pk)) {
      return;
    }

    const member = { user: { id: inputValue.pk, username: inputValue.name } };
    const success = this.#addMember(member);
    if (success) {
      this.value.push(member);
      this.#toggleContentVisibility();
    }
  }

  #roleSelectHandle(e) {
    const target = document.activeElement;

    let rowRefPk = target.getAttribute('data-ref');
    rowRefPk = parseInt(rowRefPk);
    if (typeof rowRefPk !== 'number' || isNaN(rowRefPk)) {
      return;
    }

    const index = this.value.findIndex(x => x.user.id == rowRefPk);
    const member = index >= 0 ? this.value[index] : null;
    if (!member) {
      return;
    }

    member.role = target?.options?.[target.selectedIndex]
      ? parseInt(target.options[target.selectedIndex].value)
      : member.role;
  }

  #removeMemberHandle(e) {
    const target = document.activeElement;
    e.preventDefault();

    let rowRefPk = target.getAttribute('data-ref');
    rowRefPk = parseInt(rowRefPk);
    if (typeof rowRefPk !== 'number' || isNaN(rowRefPk)) {
      return;
    }

    const index = this.value.findIndex(x => x.user.id == rowRefPk);
    const member = index >= 0 ? this.value[index] : null;
    if (!member) {
      return;
    }
    this.value.splice(index, 1);
    this.#toggleContentVisibility();

    const elements = member.elements;
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
        cls: '',
        help: field.help ?? '',
        title: field.label ?? 'Membership',
        owner: 'OrgMemberSelector',
        required: field.required,
        emptyMessage: 'You haven\'t added any Members yet.',
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

    composeTemplate(templates.OrgMember.table, {
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
        id: 'user-auto-selector',
        searchValue: '',
        searchLabel: 'Find User to add',
        searchPlaceholder: 'Search User...',
        btnId: 'add-member-btn',
        btnIcon: 'user-plus',
        btnTitle: 'Add Selected User',
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
