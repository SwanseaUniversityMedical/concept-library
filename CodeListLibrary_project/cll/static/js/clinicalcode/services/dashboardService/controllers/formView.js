import * as Const from '../constants.js';

/**
 * Class to dynamically render data model forms
 * 
 * @class
 * @constructor
 */
export class FormView {
  /**
   * @desc default constructor props
   * @type {Record<string, any>}
   * @static
   * @constant
   * 
   * @property {string}                                     url                    Table query URL
   * @property {object}                                     [state={}]             Current table state; defaults to empty state; defaults to an empty object
   * @property {object}                                     [type='create']        Optionally specify the form method type; defaults to `create` object
   * @property {string|HTMLElement}                         [element='#tbl']       The table view root element container; defaults to `#tbl`
   * @property {Record<string, Record<string, HTMLElement>} [templates=null]       Optionally specify the templates to be rendered (will collect from page otherwise); defaults to `null`
   * @property {(...args) => void}                          [finishCallback=null]  Optionally specify the completion callback (used to open view panel); defaults to `null`
   */
  static #DefaultOpts = {
    url: null,
    type: 'create',
    state: {},
    element: null,
    templates: null,
    finishCallback: null,
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
   * @type {Record<string, Record<string, HTMLElement>}
   * @private
   */
  #templates = { };

  /**
   * @desc
   * @type {Record<string, HTMLElement>}
   * @private
   */
  #layout = { };

  /**
   * @desc
   * @type {Array<Function>}
   * @private
   */
  #disposables = [];

  /**
   * @param {Record<string, any>} [opts] constructor arguments; see {@link FormView.#DefaultOpts}
   */
  constructor(opts) {
    opts = isRecordType(opts) ? opts : { };
    opts = mergeObjects(opts, FormView.#DefaultOpts, true);

    this.#initialise(opts);
  }


  /*************************************
   *                                   *
   *              Public               *
   *                                   *
   *************************************/
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
  #clear() {
    const layout = this.#layout;

  }

  #render() {
    const url = this.#props.url;
    const type = this.#props.type;
    const props = this.#props;
    const layout = this.#layout;
    const element = this.element;
    const templates = this.#templates;

    let spinners;
    let spinnerTimeout = setTimeout(() => {
      spinners = {
        load: startLoadingSpinner(element, true),
      };
    }, 200);

    this.#fetch(url)
      .then(res => res.json())
      .then(res => {
        const { detail, renderable } = res;
        const { form } = renderable;
        this.#clear();

        let data;
        if (type === 'update' && res?.data) {
          data = res.data;
        } else if (type === 'create') {
          data = { };
        } else {
          throw new Error(`Fetch Err: Failed to retrieve Model data on View<${type}>`);
        }

        for (const key in form) {
          const field = form[key];
          if (field.read_only) {
            if (data.hasOwnProperty(key)) {
              delete data[key];
            }

            continue;
          }

          const value = data.hasOwnProperty(key) ? data[key] : (field.default ?? field.initial);
          data[key] = {
            key: key,
            type: field.value_format ?? field.type,
            subtype: field.subtype,
            form: field,
            label: field.label ?? transformTitleCase(key.replace('_', ' ')),
            value: value,
            options: field.value_options,
          };
        }

        props.formData = data;
        this.#renderForm();
      })
      .finally(() => {
        if (!spinners) {
          clearTimeout(spinnerTimeout);
        }
        spinners?.load?.remove?.();
      });
  }

  #renderForm() {
    const props = this.#props;
    const element = this.element;
    const templates = this.#templates;
 
    const data = props.formData;
    // console.log(data);
    for (const key in data) {
      const field = data[key];
      const formset = field.form;

      const fieldType = field.type;
      if (isRecordType(fieldType)) {

        continue;
      }

      switch (fieldType) {
        case 'CharField': {
          const [node] = composeTemplate(this.#templates.form.CharField, {
            params: {
              key: field.key,
              help: field.help ?? '',
              title: field.label,
              value: field.value,
              placeholder: formset.initial ?? '',
              required: formset.required,
              minLength: formset.minLength ?? '',
              maxLength: formset.maxLength ?? '',
              autocomplete: transformCamelCase(field.key),
            },
            parent: element,
          });
        } break;

        case 'EmailField': {
          const [node] = composeTemplate(this.#templates.form.EmailField, {
            params: {
              key: field.key,
              help: field.help ?? '',
              title: field.label,
              value: field.value,
              placeholder: formset.initial ?? '',
              required: formset.required,
              minLength: formset.minLength ?? '',
              maxLength: formset.maxLength ?? '',
            },
            parent: element,
          });
        } break;

        case 'BooleanField': {
          let value = field.value.default ?? field.value.initial
          if (typeof value === 'string') {
            value = value.lower() === 'true';
          } else if (typeof value === 'boolean') {
            value = value;
          }

          const [node] = composeTemplate(this.#templates.form.BooleanField, {
            params: {
              key: field.key,
              help: field.help ?? '',
              title: field.label,
              value: value,
              placeholder: formset.initial ?? '',
              required: formset.required,
              minLength: formset.minLength ?? '',
              maxLength: formset.maxLength ?? '',
            },
            parent: element,
          });
        } break;

        default:
          continue;
      }
    }

    const [btn] = composeTemplate(this.#templates.form.button, {
      params: {
        id: 'confirm-btn',
        cls: 'save',
        role: 'button',
        style: 'fit-w margin-left-auto',
        title: 'Save',
      },
      parent: element,
    });
  }


  /*************************************
   *                                   *
   *              Events               *
   *                                   *
   *************************************/



  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/
  #fetch(url, opts = {}) {
    const token = this.#props.state.token;
    opts = mergeObjects(
      {
        method: 'GET',
        credentials: 'same-origin',
        withCredentials: true,
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
      },
      isObjectType(opts) ? opts : {},
      false,
      true
    );

    return fetch(url, opts);
  }


  /*************************************
   *                                   *
   *            Initialiser            *
   *                                   *
   *************************************/
  #initialise(opts) {
    if (!stringHasChars(opts.url)) {
      throw new Exception('InitError: Failed to resolve FormView target URL');
    }

    let element = opts.element;
    delete opts.element;

    if (typeof element === 'string') {
      element = document.querySelector(element);
    }

    if (!isHtmlObject(element)) {
      throw new Exception('InitError: Failed to resolve FormView element');
    }

    let templates = opts.templates;
    if (isRecordType(templates)) {
      this.#templates = templates;
      delete opts.templates;
    } else {
      let elem, view, group, name;
      const tmpl = document.querySelectorAll('template[data-for="dashboard"]');
      for (let i = 0; i < tmpl.length; ++i) {
        elem = tmpl[i];
        name = elem.getAttribute('data-name');
        view = elem.getAttribute('data-view');
        if (!stringHasChars(view)) {
          view = 'base';
        }

        group =  this.#templates?.[view];
        if (!group) {
          group = { };
          this.#templates[view] = group;
        }

        group[name] = elem;
      }

      templates = this.#templates;
    }

    this.#props = opts;
    this.element = element;

    const layout = this.#layout;
    this.#initEvents();
    this.#render();
  }

  #initEvents() {

  }
};
