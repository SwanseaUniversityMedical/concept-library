import * as Const from '../constants.js';

import Tagify from '../../../components/tagify.js';
import { OrgMemberSelector } from '../components/orgMemberSelector.js';
import { OrgAuthoritySelector } from '../components/orgAuthoritySelector.js';

/**
 * @desc coerces the given value into the required string representation
 * 
 * @param {'TimeField'|'DateField'|'DateTimeField'} fieldType         a string specifying the desired field type
 * @param {Date|string}                             value             either a `Date` instance or a datetime `string` to coerce
 * @param {any}                                     [defaultValue=''] optionally specify a default value to return if coercion failure; defaults to an empty string
 * 
 * @returns {string} either (a) a string representing the given date/time/datetime field; or (b) the specified default value 
 */
const coerceDateTimeFieldValue = (fieldType, value, defaultValue = '') => {
  if (typeof value === 'string' && stringHasChars(value)) {
    value = new Date(Date.parse(value));
  } else if (!(value instanceof Date)) {
    return defaultValue;
  }

  try {
    switch (fieldType) {
      case 'TimeField':
        value = `${value.getHours()}:${value.getMinutes()}`;
        break;

      case 'DateField':
        value = `${value.getFullYear()}-${value.getMonth()}-${value.getDay()}`;
        break;

      case 'DateTimeField':
        value = value.toISOString().slice(0, 16);
        break;

      default:
        value = defaultValue;
        break
    }
  } catch {
    value = defaultValue;
  }

  return value ?? defaultValue;
}

/**
 * @desc resolves the input attributes associated with the given field
 * 
 * @param {string}                    fieldName     the dict key name, as derived from the model, of the field being evaluated
 * @param {string}                    fieldType     the desired type of the field as derived from the model
 * @param {Record<string, any>}       style         the style dict assoc. with this field
 * @param {Record<string,string>|any} [defaults={}] optionally specify the default return value
 * 
 * @returns {Record<string, string>} the input attributes associated with this field
 */
const resolveInputType = (fieldName, fieldType, style, defaults = { inputType: 'text', autocomplete: 'off' }) => {
  let inputType = stringHasChars(style.input_type) ? style.input_type : null;
  let autocomplete = stringHasChars(style.autocomplete) ? style.autocomplete : null;
  if (!!inputType && !!autocomplete) {
    return { inputType, autocomplete };
  }

  switch (fieldType) {
    case 'URLField':
      inputType = inputType ?? 'url';
      autocomplete = autocomplete ?? 'url';
      break;

    case 'EmailField':
      inputType = inputType ?? 'email';
      autocomplete = autocomplete ?? 'email';
      break;

    case 'PhoneNumberField':
      inputType = inputType ?? 'tel';
      autocomplete = autocomplete ?? 'tel';
      break;

    case 'PasswordField':
      inputType = inputType ?? 'password';
      autocomplete = autocomplete ?? 'current-password';
      break;

    default: {
      const lookup = Const.CLU_DASH_ATTRS[fieldName];
      if (isRecordType(lookup)) {
        inputType = inputType ?? lookup.inputType;
        autocomplete = autocomplete ?? lookup.autocomplete;
      }
    } break;
  }

  return {
    inputType: !isNullOrUndefined(inputType) ? inputType : defaults.inputType,
    autocomplete: !isNullOrUndefined(autocomplete) ? autocomplete : defaults.autocomplete,
  };
}

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
   * @property {(...args) => void}                          [actionCallback=null]  Optionally specify the actionbar callback (used to respond to action events, e.g. reset pwd); defaults to `null`
   * @property {(...args) => void}                          [finishCallback=null]  Optionally specify the completion callback (used to open view panel); defaults to `null`
   */
  static #DefaultOpts = {
    url: null,
    type: 'create',
    state: {},
    element: null,
    templates: null,
    actionCallback: null,
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
  #render() {
    const url = this.#props.url;
    const type = this.#props.type;
    const props = this.#props;
    const layout = this.#layout;
    const element = this.element;
    const templates = this.#templates;

    const [dashForm] = composeTemplate(templates.form.entity_form, {
      params: {
        method: 'POST',
        action: url,
      },
      parent: element,
    });
    layout.dashForm = dashForm;

    let spinners;
    let spinnerTimeout = setTimeout(() => {
      spinners = {
        load: startLoadingSpinner(dashForm, true),
      };
    }, 200);

    this.#fetch(url)
      .then(res => res.json())
      .then(res => {
        const { fields, order, form } = res.renderable;

        let data;
        if (type === 'update' && res?.data) {
          data = res.data;
        } else if (type === 'create') {
          data = { };
        } else {
          throw new Error(`Fetch Err: Failed to retrieve Model data on View<${type}>`);
        }

        let fieldOrder = Array.isArray(order) ? order : fields;
        if (!Array.isArray(fieldOrder)) {
          fieldOrder = [];
        }

        const keys = [...Object.keys(form)].sort((a, b) => {
          const relA = fieldOrder.indexOf(a);
          const relB = fieldOrder.indexOf(b);
          if (relA > -1 && relB > -1) {
            return relA < relB ? -1 : (relA > relB ? 1 : 0);
          } else if (relA > -1) {
            return -1;
          } else if (relB > -1) {
            return 1;
          }

          return a < b ? -1 : ((a > b) ? 1 : 0);
        });

        const formData = { };
        for (let i = 0; i < keys.length; ++i) {
          const key = keys[i];
          const field = form[key];
          if (field.read_only) {
            continue;
          }

          let fieldType;
          if (isRecordType(field.style) && stringHasChars(field.style.as_type)) {
            fieldType = field.style.as_type;
          } else if (field.value_format) {
            fieldType = field.value_format;
          } else {
            fieldType = field.type;
          }

          const value = data.hasOwnProperty(key) ? data[key] : (field.default ?? field.initial);
          formData[key] = {
            key: key,
            type: fieldType,
            subtype: field.subtype,
            form: field,
            help: field.help ?? field.help_text ?? '',
            label: field.label ?? transformTitleCase(key.replace('_', ' ')),
            value: value,
            options: field.value_options,
          };
        }

        const features = isRecordType(res.renderable.features) ? res.renderable.features[props.type] : null;
        if (isRecordType(features)) {
          this.#renderFeatures(features);
        }

        props.formData = formData;
        this.#renderForm();
      })
      .finally(() => {
        if (!spinners) {
          clearTimeout(spinnerTimeout);
        }
        spinners?.load?.remove?.();
      });
  }

  #renderFeatures(features) {
    const element = this.element;
    const dashForm = this.#layout.dashForm;
    const callback = this.#props.actionCallback;
    const templates = this.#templates;
    for (const key in features) {
      switch (key) {
        case 'note': {
          createElement('div', {
            className: 'note-block',
            childNodes: [
              createElement('div', {
                className: 'note-block__title',
                childNodes: [
                  '<span class="as-icon" data-icon="&#xf0eb;" aria-hidden="true"></span>',
                  createElement('p', { innerText: 'Note' }),
                ],
              }),
              createElement('pre', {
                className: 'note-block__message',
                innerText: features[key],
              }),
            ],
            parent: dashForm
          });
        } break;

        case 'actionbar': {
          const actions = features[key];
          if (!Array.isArray(actions)) {
            break;
          }

          for (let i = 0; i < actions.length; ++i) {
            let action = actions[i];
            if (action === 'reset_pwd') {
              composeTemplate(templates.form.button, {
                params: {
                  id: action,
                  icon: 'padlock-unlock',
                  role: 'button',
                  style: 'fit-w margin-left-auto',
                  title: 'Send Password Reset',
                },
                render: (elems) => {
                  const btn = elems[0];
                  element.prepend(btn);

                  if (typeof callback === 'function') {
                    btn.addEventListener('click', (e) => callback(
                      action,
                      e,
                      { type: this.#props.type, url: this.#props.url },
                      this,
                      btn
                    ));
                  }
                }
              });
            }
          }

        } break;

        default:
          break
      }
    }
  }

  #renderForm() {
    const props = this.#props;
    const element = this.element;
    const dashForm = this.#layout.dashForm;
    const templates = this.#templates;
 
    const data = props.formData;
    const collectors = { };
    for (const key in data) {
      const field = data[key];
      const formset = field.form;

      let fieldType = field.type;
      if (isRecordType(fieldType)) {
        fieldType = stringHasChars(fieldType.type) ? fieldType.type : field.subtype;
      }

      // Handle ManyToMany `Through` fields
      if (fieldType === 'through') {
        const component = this.#renderComponent(field);
        if (!isNullOrUndefined(component)) {          
          collectors[field.key] = () => {
            return component.getDataValue();
          };
        }

        continue;
      }

      // Handle misc. type-derived component(s)
      let value = field.value ?? formset.default ?? formset.initial;
      const label = field.label ?? formset.label ?? transformTitleCase(key);
      const style = isRecordType(formset.style) ? formset.style : { };
      const helpText = field.help ?? formset.help_text ?? '';
      const isRequired = typeof formset.required === 'boolean' && formset.required;

      let renderParameters, renderTemplate, renderCallback;
      switch (fieldType) {
        // Single or Multi ForeignKey
        case 'ForeignKey':
        case 'PrimaryKeyRelatedField': {
          const subtype = field.subtype;
          if (typeof subtype === 'string' && subtype.toLowerCase().startsWith('list')) {
            // Multi select FK
            const options = field.options;
            if (!Array.isArray(options)) {
              break;
            }

            if (!Array.isArray(value)) {
              value = [];
            }

            renderTemplate = templates.form.MultiForeignKeyField;
            renderParameters = {
              cls: style.class ?? '',
              key: key,
              help: helpText,
              title: label,
              required: isRequired,
            };
            renderCallback = (elems) => {
              const input = elems[0].querySelector('input');
              if (isNullOrUndefined(input)) {
                return;
              }

              const tagbox = new Tagify(input, {
                'autocomplete': true,
                'useValue': true,
                'allowDuplicates': false,
                'restricted': true,
                'items': options.map(item => {
                  const itemPk = !isNullOrUndefined(item.pk) ? item.pk : item.id;
                  const itemName = !isNullOrUndefined(item.name) ? item.name : item.username;
                  return { name: itemName, value: itemPk };
                }),
                'onLoad': (box) => {
                  for (let i = 0; i < value.length; ++i) {
                    const item = value[i];
                    if (typeof item !== 'object') {
                      continue;
                    }

                    const itemPk = !isNullOrUndefined(item.pk) ? item.pk : item.id;
                    const itemName = !isNullOrUndefined(item.name) ? item.name : item.username;
                    if (typeof itemName !== 'string' || isNullOrUndefined(itemPk)) {
                      continue;
                    }

                    box.addTag(itemName, itemPk);
                  }

                  return () => {
                    const choices = box?.options?.items?.length ?? 0;
                    if (choices < 1) {
                      parent.style.setProperty('display', 'none');
                    }
                  }
                }
              }, { });
              this.#disposables.push(() => tagbox.dispose());

              collectors[key] = () => {
                let sel = tagbox.getDataValue();
                if (!Array.isArray(sel) || sel.length < 1) {
                  sel = null;
                }

                return sel;
              };
            };

          } else {
            // Single select FK
            let fkValue;
            if (typeof value === 'number') {
              fkValue = value;
            } else if (isRecordType(value)) {
              fkValue = value.id ?? value.pk;
            } else {
              fkValue = null;
            }

            renderTemplate = templates.form.ForeignKeyField;
            renderParameters = {
              cls: style.class ?? '',
              key: key,
              help: helpText,
              title: label,
              required: isRequired,
            };
            renderCallback = (elems) => {
              const select = elems[0].querySelector('select');
              if (!select) {
                return;
              }

              let index = 0;
              let selectedIndex;
              if (isNullOrUndefined(fkValue)) {
                selectedIndex = index;
                index++;

                createElement('option', {
                  innerText: '-----',
                  attributes: {
                    value: '-1',
                    disabled: 'true',
                    selected: 'true',
                    hidden: 'true',
                  },
                  parent: select,
                });
              }

              const options = field.options;
              for (let i = 0; i < options.length; ++i) {
                const option = options[i];
                createElement('option', {
                  innerText: option.name,
                  attributes: {
                    value: option.pk,
                    selected: option.pk === fkValue,
                  },
                  parent: select,
                });

                if (option.pk === fkValue) {
                  selectedIndex = index;
                }
                index++;
              }

              if (!isNullOrUndefined(selectedIndex)) {
                select.selectedIndex = selectedIndex;
              }

              collectors[key] = () => {
                let sel = select.selectedIndex;
                if (isNullOrUndefined(sel) || isNaN(sel) || sel < 0) {
                  return null;
                }

                sel = select.options[sel];
                if (isNullOrUndefined(sel) || isNullOrUndefined(sel.value)) {
                  return null;
                }
 
                sel = Number(sel.value)
                return sel >= 0 ? sel : null;
              };
            };
          }
        } break;

        // BooleanField(s)
        case 'BooleanField': {
          if (typeof value === 'string') {
            value = value.lower() === 'true';
          } else if (typeof value === 'boolean') {
            value = value;
          }

          renderTemplate = templates.form.BooleanField;
          renderParameters = {
            cls: style.class ?? '',
            key: key,
            title: label,
            help: helpText,
            required: isRequired,
          };
          renderCallback = (elems) => {
            const chk = elems[0].querySelector('[data-class="checkbox"]');
            chk.checked = !!value;

            collectors[key] = () => {
              return !!chk.checked;
            };
          };
        } break;

        // Numeric
        case 'FloatField':
        case 'DecimalField':
        case 'IntegerField':
        case 'DurationField':
          const rounding = formset.rounding;
          const maxDigits = formset.max_digits;
          const decimalPlaces = formset.decimal_places;

          let inputMode;
          if (fieldType === 'IntegerField') {
            inputMode = 'numeric';
          } else {
            inputMode = 'decimal';
          }

          renderTemplate = templates.form.NumericField;
          renderParameters = {
            cls: style.class ?? '',
            key: key,
            title: label,
            help: helpText,
            value: value ?? '',
            inputmode: inputMode,
            required: isRequired,
            placeholder: formset.initial ?? '',
            minValue: formset.min_value ?? '',
            maxValue: formset.max_value ?? '',
            rounding: rounding ?? '',
            maxDigits: maxDigits ?? '',
            decimalPlaces: decimalPlaces ?? '',
          };
          renderCallback = (elems) => {
            const input = elems[0];            
            collectors[key] = () => {
              return Number(input.value);
            };
          };
          break;

        // Choice(s)
        case 'ChoiceField':
          value = !isNullOrUndefined(value) ? value : (formset.default ?? formset.initial);

          renderTemplate = templates.form.ChoiceField;
          renderParameters = {
            cls: style.class ?? '',
            key: key,
            help: helpText,
            title: label,
            required: isRequired,
          };
          renderCallback = (elems) => {
            const select = elems[0].querySelector('select');
            if (!select) {
              return;
            }

            const options = isRecordType(formset.grouped_choices) ? formset.grouped_choices : { };
            const optionValues = isRecordType(formset.choice_strings_to_values) ? formset.choice_strings_to_values : { };

            let index = 0;
            let selectedIndex;
            if (isNullOrUndefined(value) && isNullOrUndefined(formset.default ?? formset.initial)) {
              selectedIndex = index;
              index++;

              createElement('option', {
                innerText: '-----',
                attributes: {
                  value: '-1',
                  disabled: 'true',
                  selected: 'true',
                  hidden: 'true',
                },
                parent: select,
              });
            }

            for (const optKey in options) {
              const optVal = options[optKey];
              const optTrg = optionValues[optKey];
              createElement('option', {
                innerText: optVal,
                attributes: {
                  value: optKey,
                  selected: optTrg === value,
                },
                parent: select,
              });

              if (optTrg === value) {
                selectedIndex = index;
              }
              index++;
            }

            if (!isNullOrUndefined(selectedIndex)) {
              select.selectedIndex = selectedIndex;
            }

            collectors[key] = () => {
              let sel = select.selectedIndex;
              if (isNullOrUndefined(sel) || isNaN(sel) || sel < 0) {
                return null;
              }

              sel = select.options[sel];
              if (isNullOrUndefined(sel) || isNullOrUndefined(sel.value)) {
                return null;
              }

              sel = Number(sel.value)
              return sel >= 0 ? sel : null;
            };
          };
          break;

        // Large Text field(s)
        case 'TextField':
        case 'JSONField':
          const isMarkdown = fieldType !== 'JSONField' && !!style.markdown;
          const minLength = formset.minLength ?? '';
          const maxLength = formset.maxLength ?? '';
          const placeholder = formset.initial ?? '';
          const spellcheck = typeof style.spellcheck === 'boolean' ? style.spellcheck : true;

          let className = isMarkdown ? 'filter-scrollbar' : 'text-area-input';
          className = `${className} ${style.class ?? ''}`

          if (fieldType === 'JSONField') {
            if (Array.isArray(value) || isRecordType(value)) {
              try {
                value = JSON.stringify(value, null, 2);
              } catch {
                value = '';
              }
            } else if (typeof value !== 'string' && !isNullOrUndefined(value)) {
              value = value.toString();
            } else {
              value = '';
            }
          }

          renderTemplate = templates.form.TextAreaField;
          renderParameters = {
            cls: className,
            key: key,
            title: label,
            help: helpText,
            value: '',
            placeholder: placeholder,
            required: isRequired,
            minLength: minLength,
            maxLength: maxLength,
            useMarkdown: isMarkdown,
            spellcheck: spellcheck,
          };
          renderCallback = (elems) => {
            const textarea = elems[0].querySelector('textarea');
            if (!textarea) {
              return;
            }

            collectors[key] = () => {
              let sel;
              try {
                sel = textarea.value.trim();

                if (fieldType === 'JSONField') {
                  sel = JSON.parse(sel);
                }
              } catch (e) {
                console.error(`[FormView] Failed to parse JSONField, invalid data:\n\n${e}`);
                sel = null;
              }

              return sel;
            };

            textarea.value = value;
          };
          break;

        // String
        case 'URLField':
        case 'UUIDField':
        case 'SlugField':
        case 'CharField':
        case 'EmailField':
        case 'PasswordField':
        case 'FilePathField': {
          const pattern = (typeof style.pattern === 'string' && stringHasChars(style.pattern)) ? style.pattern : null;
          const minLength = formset.minLength ?? '';
          const maxLength = formset.maxLength ?? '';
          const placeholder = formset.initial ?? '';

          const inputAttributes = resolveInputType(key, fieldType, style);
          renderTemplate = templates.form.TextField;
          renderParameters = {
            cls: style.class ?? '',
            key: key,
            title: label,
            help: helpText,
            value: '',
            inputtype: inputAttributes.inputType,
            autocomplete: inputAttributes.autocomplete,
            placeholder: placeholder,
            required: isRequired,
            minLength: minLength,
            maxLength: maxLength,
          };
          renderCallback = (elems) => {
            const input = elems[0].querySelector('input');
            if (isNullOrUndefined(input)) {
              return;
            }
            input.value = value ?? '';

            collectors[key] = () => {
              if (fieldType === 'UUIDField' && !stringHasChars(input.value)) {
                return null;
              }

              return input.value.trim();
            };

            if (isNullOrUndefined(pattern) || !stringHasChars(pattern)) {
              return;
            }

            input.setAttribute('pattern', pattern);
          }
        } break;

        case 'DateField':
        case 'TimeField':
        case 'DateTimeField':
          value = coerceDateTimeFieldValue(fieldType, value);

          const datatype = Const.CLU_DATATYPE_ATTR[fieldType] ?? 'date';
          renderTemplate = templates.form.DateTimeLikeField;
          renderParameters = {
            cls: style.class ?? '',
            key: key,
            title: label,
            help: helpText,
            datatype: datatype,
            value: value ?? '',
            required: isRequired,
          };
          renderCallback = (elems) => {
            const input = elems[0].querySelector('input');
            if (isNullOrUndefined(input)) {
              return;
            }

            collectors[key] = () => {
              const sel = coerceDateTimeFieldValue(fieldType, input.value, null);
              return sel;
            };

            input.value = value;
          }
          break;

        // // MultiChoice?
        // case 'MultipleChoiceField':
        //   break;

        // // List(s)?
        // case 'ListField':
        // case 'ListSerializer':
        //   break;

        default:
          console.error(`[Dash::FormView] Failed to render form field for '${key}' as '${fieldType}'`);
          break;
      }

      if (renderTemplate && renderParameters) {
        composeTemplate(renderTemplate, {
          params: renderParameters,
          parent: dashForm,
          render: (elems) => {
            if (typeof renderCallback === 'function') {
              renderCallback(elems);
            }
          }
        });
      }
    }

    const [btn] = composeTemplate(templates.form.button, {
      params: {
        id: 'confirm-btn',
        icon: 'save',
        role: 'button',
        style: 'fit-w margin-left-auto',
        title: 'Save',
      },
      parent: element,
    });

    const submitHnd = (e) => {
      e.preventDefault();

      let success = true;
      let submissionData = { };
      try {
        for (const key in collectors) {
          const res = collectors[key]();
          submissionData[key] = res;
        }
      } catch (e) {
        success = false;
        console.error(`[FormView] Failed to buid form with err:\n\n:${e}`);

        window.ToastFactory.push({
          type: 'warning',
          message: '[E: FB01] Contact an Admin if this error persists.',
          duration: 4000,
        });
      }

      if (!success) {
        return;
      }

      this.#submitForm(submissionData)
        .then(async response => {
          let message;
          if (response.ok) {
            return await response.json();
          }

          const headers = response.headers;
          if (headers.get('content-type').search('json')) {
            try {
              const result = await response.json();
              if (!isRecordType(result)) {
                throw new Error(`Not parseable, expected Record-like response on Res<code: ${response.status}> but got '${typeof result}'`);
              }

              if (response.status === 400) {
                this.#renderValidationErrors(result);
                message = `[${response.status}]: Please fix the errors on the form.`;
              } else if (!isNullOrUndefined(result.detail)) {
                if (typeof result.detail === 'string' && stringHasChars(result.detail)) {
                  message = `[${response.status}]: ${result.detail}`;
                } else if (Array.isArray(result.detail)) {
                  message = result.detail.filter(x => stringHasChars(x)).join(', ');
                  message = `[${response.status}]: ${message}`;
                }
              } else {
                throw new Error(`Not parseable, expected 'detail' element on Res<code: ${response.status}>`);
              }
            } catch (e) {
              console.warn(`[FormView] Failed to resolve response\'s json with err:\n\t-${e}\n`);
            }
          }

          if (isNullOrUndefined(message)) {
            message = `[${response.status}] ${response.statusText}`;
          }

          const err = new Error(message);
          // err callback?

          throw err;
        })
        .then(res => {
          this.#renderValidationErrors();

          // succ callback?

        })
        .catch(e => {
          console.error('[ERROR]', e);

          window.ToastFactory.push({
            type: 'error',
            message: e instanceof Error ? e.message : String(e),
            duration: 4000,
          });
        });
    };

    btn.addEventListener('click', submitHnd);
  }

  #renderValidationErrors(errors) {
    const dashForm = this.#layout.dashForm;
    if (!dashForm) {
      return;
    }

    const keys = isRecordType(errors) ? [...Object.keys(errors)] : [];
    if (keys.length < 1) {
      const errs = dashForm.querySelectorAll('[data-ref="validation"]');
      for (let i = 0; i < errs.length; ++i) {
        errs[i].remove();
      }

      return;
    }

    const allowed = [];
    for (let i = 0; i < keys.length; ++i) {
      const key = keys[i];

      const component = dashForm.querySelector(`[data-fieldset="${key}"]`);
      const descriptor = dashForm.querySelector(`[data-fieldset="${key}"] p[data-ref="help"]`);
      if (isNullOrUndefined(component)) {
        continue;
      }

      let errorMessages = errors[key];
      if (typeof errorMessages === 'string' && stringHasChars(errorMessages)) {
        errorMessages = [errorMessages];
      }

      if (!Array.isArray(errorMessages) || errorMessages.length < 1) {
        continue;
      }

      let elements;
      for (let j = 0; j < errorMessages.length; ++j) {
        const msg = errorMessages[j];
        if (typeof msg !== 'string' || !stringHasChars(msg)) {
          continue;
        }

        if (!elements) {
          elements = [];
        }

        elements.push(createElement('p', { innerText: msg }));
      }

      if (!Array.isArray(elements) || elements.length < 1) {
        continue;
      }

      let validation = component.querySelector(`[data-ref="validation"]`);
      if (isNullOrUndefined(validation)) {
        validation = createElement('div', {
          data: { ref: 'validation' },
          childNodes: [
            createElement('div', {
              className: 'validation__title',
              childNodes: [
                '<span class="as-icon" data-icon="&#xf06a;" aria-hidden="true"></span>',
                createElement('p', { innerText: 'Error:' }),
              ],
            }),
            ...elements
          ],
        });

        if (!isNullOrUndefined(descriptor)) {
          descriptor.after(validation);
        } else {
          descriptor.after(component.firstChild);
        }
      } else {
        clearAllChildren(validation);
        for (let j = 0; j < elements.length; ++j) {
          validation.appendChild(elements[j]);
        }
      }
      allowed.push(validation);
    }

    dashForm.querySelectorAll(`[data-ref="validation"]`)
      .forEach(x => {
        if (!allowed.includes(x)) {
          x.remove();
        }
      });
  }

  #renderComponent(field) {
    const dashForm = this.#layout.dashForm;
    const templates = this.#templates;
    const { component: componentName } = field.type;

    let component;
    switch (componentName) {
      case 'OrgAuthoritySelector':
        component = new OrgAuthoritySelector({
          field: field,
          value: field.value,
          options: field.options,
          element: dashForm,
          templates: templates,
        });
        break;

      case 'OrgMemberSelector':
        component = new OrgMemberSelector({
          field: field,
          value: field.value,
          options: field.options,
          element: dashForm,
          templates: templates,
        });
        break;

      default:
        break;
    }

    if (!!component && typeof component?.dispose === 'function') {
      this.#disposables.push(() => component.dispose());
    }

    return component;
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
      isObjectType(opts) ? opts : {},
      {
        method: 'GET',
        cache: 'no-cache',
        credentials: 'same-origin',
        withCredentials: true,
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
      },
      false,
      true
    );

    return fetch(url, opts);
  }

  #submitForm(formData) {
    const props = this.#props;
    return new Promise((resolve, reject) => {
      const url = props.url;
      const formType = props.type;

      let data;
      try {
        data = JSON.stringify(formData);
      } catch (e) {
        reject(new Error('[E: FB02] Contact an Admin if this error persists.'));
        return;
      }

      this.#fetch(url, {
        method: formType === 'create' ? 'POST' : 'PUT',
        body: data,
      })
        .then(resolve)
        .catch(reject);
    })
  }


  /*************************************
   *                                   *
   *            Initialiser            *
   *                                   *
   *************************************/
  #initialise(opts) {
    if (!stringHasChars(opts.url)) {
      throw new Error('InitError: Failed to resolve FormView target URL');
    }

    let element = opts.element;
    delete opts.element;

    if (typeof element === 'string') {
      element = document.querySelector(element);
    }

    if (!isHtmlObject(element)) {
      throw new Error('InitError: Failed to resolve FormView element');
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

        group = this.#templates?.[view];
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

    this.#initEvents();
    this.#render();
  }

  #initEvents() {

  }
};
