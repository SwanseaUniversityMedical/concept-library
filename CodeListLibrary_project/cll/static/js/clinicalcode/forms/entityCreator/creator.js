import {
  ENTITY_OPTIONS,
  ENTITY_TOAST_MIN_DURATION,
  ENTITY_FORM_BUTTONS,
  ENTITY_TEXT_PROMPTS
} from '../entityFormConstants.js';

import {
  ENTITY_FIELD_COLLECTOR,
  getTemplateFields,
  createFormHandler,
  tryGetFieldTitle
} from './utils.js';

/**
 * @class EntityCreator
 * @desc A class that can be used to control forms for templated dynamic content
 * 
 */
export default class EntityCreator {
  #locked = false;

  constructor(data, options) {
    this.data = data;
    this.formChanged = false;

    this.#buildOptions(options || { });
    this.#collectForm();
    this.#setUpForm();
    this.#setUpSubmission();
  }

  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/
  /**
   * isLocked
   * @desc whether we're still awaiting the promise to resolve
   * @returns {boolean} represents status of promise
   */
  isLocked() {
    return this.#locked;
  }

  /**
   * getFormMethod
   * @desc describes whether the form is a create or an update form, where 1 = create & 2 = update
   * @returns {int} int representation of the form method enum
   */
  getFormMethod() {
    return this.data?.method;
  }

  /**
   * getData
   * @returns {object} the template, metadata, any assoc. entity and the form method
   */
  getData() {
    return this.data;
  }

  /**
   * getForm
   * @returns {object} form describing the key/value pair of the form as defined
   *                   by its template
   */
  getForm() {
    return this.form;
  }

  /**
   * getFormButtons
   * @returns {object} returns the assoc. buttons i.e. save as draft, submit button
   */
  getFormButtons() {
    return this.buttons;
  }

  /**
   * getOptions
   * @returns {object} the parameters used to build this form
   */
  getOptions() {
    return this.options;
  }

  /**
   * isDirty
   * @returns {boolean} whether the form has been modified and its data is now dirty
   */
  isDirty() {
    return this.data?.is_historical === 1 || this.formChanged;
  }

  /**
   * isEditingChildren
   * @desc checks whether the user is editing a child component
   * @returns {boolean} reflects editing state
   */
  isEditingChildren() {
    for (const [field, packet] of Object.entries(this.form)) {
      if (!packet.handler || !packet.handler.isInEditor) {
        continue;
      }

      if (packet.handler.isInEditor()) {
        return true;
      }
    }

    return false;
  }

  /**
   * getActiveEditor
   * @desc finds the active editor that the user is interacting with
   * @returns {object|null} the active component
   */
  getActiveEditor() {
    for (const [field, packet] of Object.entries(this.form)) {
      if (!packet.handler || !packet.handler.isInEditor) {
        continue;
      }

      if (packet.handler.isInEditor()) {
        return {
          field: field,
          packet: packet,
        };
      }
    }
  }

  /**
   * getSafeGroupId
   * @desc attempts to safely get the default group id if the 
   *       user attempts to change the group when they have derived
   *       access from another group
   * @param {integer|null} groupId optional parameter to test
   * @returns {integer|null} the safe group id
   */
  getSafeGroupId(groupId) {
    groupId = !isNullOrUndefined(groupId) && groupId >= 0 ? groupId : null;

    if (this.data?.derived_access !== 1) {
      return groupId;
    }

    if (isNullOrUndefined(groupId) || groupId < 0) {
      if (window.ToastFactory) {
        window.ToastFactory.push({
          type: 'error',
          message: ENTITY_TEXT_PROMPTS.DERIVED_GROUP_ACCESS,
          duration: ENTITY_TOAST_MIN_DURATION,
        });
      }

      return this.form?.organisation?.value;
    }

    return groupId;
  }

  /*************************************
   *                                   *
   *               Setter              *
   *                                   *
   *************************************/  
  /**
   * makeDirty
   * @desc sets the form as dirty - used by child components
   * @returns this, for chaining
   */
  makeDirty() {
    this.formChanged = true;
    return this;
  }

  /**
   * submitForm
   * @desc submits the form to create/update an entity
   */
  submitForm() {
    // Check that our children aren't in an editor state
    const child = this.getActiveEditor();
    if (child) {
      let title = tryGetFieldTitle(child.field, child.packet);
      title = title || child.field;

      return window.ToastFactory.push({
        type: 'warning',
        message: interpolateString(ENTITY_TEXT_PROMPTS.CLOSE_EDITOR, { field: title }),
        duration: ENTITY_TOAST_MIN_DURATION,
      });
    }

    // Clear prev. error messages
    this.#clearErrorMessages();

    // Collect form data & validate
    const { data, errors } = this.#collectFieldData();

    // If there are errors, update the assoc. fields & prompt the user
    if (errors.length > 0) {
      let minimumScrollY;
      for (let i = 0; i < errors.length; ++i) {
        const error = errors[i];
        const packet = this.form?.[error.field];
        if (isNullOrUndefined(packet)) {
          continue;
        }

        const elem = this.#displayError(packet, error);
        if (!isNullOrUndefined(elem)) {
          if (isNullOrUndefined(minimumScrollY) || elem.offsetTop < minimumScrollY) {
            minimumScrollY = elem.offsetTop;
          }
        }
      }

      minimumScrollY = !isNullOrUndefined(minimumScrollY) ? minimumScrollY : 0;
      window.scrollTo({ top: minimumScrollY, behavior: 'smooth' });
      
      return window.ToastFactory.push({
        type: 'danger',
        message: ENTITY_TEXT_PROMPTS.FORM_IS_INVALID,
        duration: ENTITY_TOAST_MIN_DURATION,
      });
    }

    // Peform dict diff to see if any changes, if not, inform the user to do so
    if (!this.isDirty() && !hasDeltaDiff(this.initialisedData, data)) {
      return window.ToastFactory.push({
        type: 'warning',
        message: ENTITY_TEXT_PROMPTS.NO_FORM_CHANGES,
        duration: ENTITY_TOAST_MIN_DURATION,
      });
    }

    // If no errors and it is different, then attempt to POST
    if (this.#locked) {
      return;
    }
    this.#locked = true;

    const spinner = startLoadingSpinner();
    try {
      const token = getCookie('csrftoken');
      const request = {
        method: 'POST',
        cache: 'no-cache',
        credentials: 'same-origin',
        withCredentials: true,
        headers: {
          'X-CSRFToken': token,
          'Authorization': `Bearer ${token}`
        },
        body: this.#generateSubmissionData(data),
      };
  
      fetch('', request)
        .then(response => {
          if (!response.ok) {
            return Promise.reject(response);
          }
          return response.json();
        })
        .then(content => {
          this.formChanged = false;
          this.initialisedData = data;
          return content;
        })
        .then(content => this.#redirectFormClosure(content))
        .catch(error => {
          if (typeof error.json === 'function') {
            this.#handleAPIError(error);
          } else {
            this.#handleServerError(error);
          }
          spinner.remove();
        })
        .finally(() => {
          this.#locked = false;
        });
    }
    catch (e){
      this.#locked = false;
      spinner.remove();
    }
  }

  /**
   * cancelForm
   * @desc Prompts the user to cancel the form if changes have been made and then either:
   *        a) redirects the user to the search page if the entity does not exist
   *          *OR*
   *        b) redirects the user to the detail page if the entity exists
   * 
   *      If no changes have been made, the user is immediately redirected
   */
  cancelForm() {
    if (!this.isDirty()) {
      this.#redirectFormClosure();
      return;
    }

    window.ModalFactory.create(ENTITY_TEXT_PROMPTS.CANCEL_PROMPT)
      .then(() => {
        this.#redirectFormClosure();
      })
      .catch(() => { /* SINK */ });
  }

  /*************************************
   *                                   *
   *               Private             *
   *                                   *
   *************************************/
  /**
   * handleAPIError
   * @desc handles error responses from the POST request
   * @param {*} error the API error response
   */
  #handleAPIError(error) {
    error.json()
      .then(e => {
        const message = e?.message;
        if (!message) {
          this.#handleServerError(e);
          return;
        }

        const { type: errorType, errors } = message;
        console.error(`API Error<${errorType}> occurred:`, errors);

        if (Array.isArray(errors) && errors.length > 0) {
          for (let i = 0; i < errors.length; i++) {
            if (!stringHasChars(errors[i])) {
              continue;
            }

            window.ToastFactory.push({
              type: 'danger',
              message: errors[i],
              duration: ENTITY_TOAST_MIN_DURATION,
            });
          }
        } else {
          window.ToastFactory.push({
            type: 'danger',
            message: stringHasChars(message) ? message : ENTITY_TEXT_PROMPTS.API_ERROR_INFORM,
            duration: ENTITY_TOAST_MIN_DURATION,
          });
        }
      })
      .catch(e => this.#handleServerError);
  }

  /**
   * handleServerError
   * @desc handles server errors when POSTing data
   * @param {*} error the server error response
   */
  #handleServerError(error) {
    let message;
    if (stringHasChars(error.statusText)) {
      console.error(error.statusText);
      message = error.statusText;
    } else {
      console.error(error);
      message = ENTITY_TEXT_PROMPTS.SERVER_ERROR_MESSAGE;
    }
    
    window.ToastFactory.push({
      type: 'danger',
      message: message,
      duration: ENTITY_TOAST_MIN_DURATION,
    });
  }

  /**
   * generateSubmissionData
   * @desc packages & jsonifies the form data for POST submission
   * @param {object} data the data we wish to submit
   * @returns {string} jsonified data packet
   */
  #generateSubmissionData(data) {
    // update the data with legacy fields (if still present in template)
    const templateData = this.data?.entity?.template_data;
    if (!isNullOrUndefined(templateData)) {
      const templateFields = getTemplateFields(this.data?.template);
      for (const [key, value] of Object.entries(templateData)) {
        if (data.hasOwnProperty(key) || !templateFields.hasOwnProperty(key)) {
          continue;
        }
        
        data[key] = value;
      }
    }

    // package the data
    const packet = {
      method: this.getFormMethod(),
      data: data,
    };

    if (this.data?.object) {
      const { id, history_id } = this.data.object;
      packet.entity = { id: id, version_id: history_id };
    }

    if (this.data?.template) {
      packet.template = {
        id: this.data.template.id,
        version: this.data.template?.definition?.template_details?.version
      }
    }

    return JSON.stringify(packet);
  }

  /**
   * redirectFormClosure
   * @desc redirection after canellation or submission of a form
   * @param {object|null} reference optional parameter to redirect to newly created entity
   */
  #redirectFormClosure(reference = null) {
    // Redirect to newly created object if available
    if (!isNullOrUndefined(reference)) {
      window.location.href = reference.redirect;
      return;
    }

    // Redirect to previous entity if available
    const object = this.data?.object;
    if (object?.referralURL) {
      window.location.href = strictSanitiseString(object.referralURL);
      return;
    }

    // Redirect to search page
    window.location.href = strictSanitiseString(this.data.links.referralURL);
  }

  /**
   * collectFieldData
   * @desc iteratively collects the form data and validates it against the template data
   * @returns {object} which describes the form data and associated errors
   */
  #collectFieldData() {
    const data = { };
    const errors = [ ];
    for (const [field, packet] of Object.entries(this.form)) {
      if (!ENTITY_FIELD_COLLECTOR.hasOwnProperty(packet?.dataclass)) {
        continue;
      }

      // Collect the field value & validate it
      const result = ENTITY_FIELD_COLLECTOR[packet?.dataclass](field, packet, this);
      if (result && result?.valid) {
        data[field] = result.value;
        continue;
      }

      // Validation has failed, append the error message
      const title = tryGetFieldTitle(field, packet);
      result.field = field;
      result.message = interpolateString(result.message, { field: title });
      errors.push(result);
    }
    
    return {
      data: data,
      errors: errors,
    };
  }

  /**
   * buildOptions
   * @desc private method to merge the expected options with the passed options - passed takes priority
   * @param {dict} options the option parameter 
   */
  #buildOptions(options) {
    this.options = mergeObjects(options, ENTITY_OPTIONS);
  }

  /**
   * collectForm
   * @desc collects the form data associated with the template's fields
   */
  #collectForm() {
    const fields = getTemplateFields(this.data.template);
    if (!fields) {
      return console.error('Unable to initialise, no template fields passed');
    }
    
    const form = { };
    for (let field in fields) {
      const element = document.querySelector(`[data-field="${field}"]`);
      if (!element) {
        continue;
      }

      form[field] = {
        element: element,
        validation: this.#getFieldValidation(field),
        value: this.#getFieldInitialValue(field),
      };
    }

    this.form = form;
  }

  /**
   * getFieldValidation
   * @desc attempts to retrieve the validation data associated with a field, given by its template
   * @param {string} field 
   * @returns {object|null} a dict containing the validation information, if present
   */
  #getFieldValidation(field) {
    const fields = getTemplateFields(this.data.template);
    const packet = fields[field];
    if (packet?.is_base_field) {
      let metadata = this.data?.metadata;
      if (!metadata) {
        return null;
      }
      
      return metadata[field]?.validation;
    }

    return packet?.validation;
  }

  /**
   * getFieldInitialValue
   * @desc attempts to determine the initial value of a field based on the entity's template data
   * @param {string} field 
   * @returns {*} any field's initial value
   */
  #getFieldInitialValue(field) {
    // const fields = getTemplateFields(this.data.template);
    // const packet = fields[field];
    // if (packet?.is_base_field) {
    //   let metadata = this.data?.metadata;
    //   if (!metadata) {
    //     return null;
    //   }
      
    //   return metadata[field]?.validation;
    // }

    // // return packet?.validation;
    const entity = this.data?.entity;
    if (!entity) {
      return;
    }

    if (entity.hasOwnProperty(field)) {
      return entity[field];
    }

    if (!entity?.template_data.hasOwnProperty(field)) {
      return;
    }
    
    return entity.template_data[field];
  }


  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/
  /**
   * setUpForm
   * @desc Initialises the form by instantiating handlers for the components,
   *       renders any assoc. components, and responsible for handling the
   *       prompt when users leave the page with unsaved data
   */
  #setUpForm() {
    for (let field in this.form) {
      const pkg = this.form[field];
      const cls = pkg.element.getAttribute('data-class');
      if (!cls) {
        continue;
      }

      this.form[field].handler = createFormHandler(pkg.element, cls, this.data, pkg?.validation);
      this.form[field].dataclass = cls;
    }

    if (this.options.promptUnsaved) {
      window.addEventListener('beforeunload', this.#handleOnLeaving.bind(this), { capture: true });
    }

    const { data, errors } = this.#collectFieldData();
    this.initialisedData = data;
  }

  /**
   * setUpSubmission
   * @desc initialiser for the submit and cancel buttons associated with this form
   */
  #setUpSubmission() {
    this.formButtons = { }

    const submitBtn = document.querySelector(`#${ENTITY_FORM_BUTTONS['submit']}`);
    if (submitBtn) {
      if (this.data?.is_historical === 1) {
        submitBtn.addEventListener('click', (e) => {
          window.ModalFactory.create(ENTITY_TEXT_PROMPTS.HISTORICAL_PROMPT)
            .then(() => {
              this.submitForm();
            })
            .catch(() => { /* SINK */ });
        })
      } else {
        submitBtn.addEventListener('click', this.submitForm.bind(this));
      }
    }

    const cancelBtn = document.querySelector(`#${ENTITY_FORM_BUTTONS['cancel']}`);
    if (cancelBtn) {
      cancelBtn.addEventListener('click', this.cancelForm.bind(this));
    }
  }

  /**
   * setAriaErrorLabels
   * @desc appends aria attributes to the element input field
   *       so that screen readers / accessibility tools are
   *       able to inform the user of the field error
   * @param {node} element the element to append aria attributes
   * @param {object} error the error object as generated by the validation method
   */
  #setAriaErrorLabels(element, error) {
    element.setAttribute('aria-invalid', true);
    element.setAttribute('aria-description', error.message);
  }

  /**
   * clearErrorMessages
   * @desc clears all error messages currently rendered within the input groups
   */
  #clearErrorMessages() {
    // Remove appended error messages
    const items = document.querySelectorAll('.detailed-input-group__error');
    for (let i = 0; i < items.length; ++i) {
      const item = items[i];
      item.remove();
    }

    for (const [field, packet] of Object.entries(this.form)) {
      // Remove aria labels
      const element = packet.element;
      element.setAttribute('aria-invalid', false);
      element.setAttribute('aria-description', null);

      // Remove component error messages
      if (!isNullOrUndefined(packet.handler) && typeof packet.handler?.clearErrorMessages == 'function') {
        packet.handler.clearErrorMessages();
      }
    }
  }

  /**
   * displayError
   * @desc displays the error packets for individual fields as generated by
   *       the field validation methods
   * @param {object} packet the field's template packet
   * @param {object} error the generated error object
   * @returns {node|null} returns the error element if applicable
   */
  #displayError(packet, error) {
    const element = packet.element;
    this.#setAriaErrorLabels(element, error);

    // Add __error class below title if available & the forceErrorToasts parameter was not passed
    if (!this.options.forceErrorToasts) {
      const inputGroup = tryGetRootElement(element, 'detailed-input-group');
      if (!isNullOrUndefined(inputGroup)) {
        const titleNode = inputGroup.querySelector('.detailed-input-group__title');
        const errorNode = createElement('p', {
          'aria-live': 'true',
          'className': 'detailed-input-group__error',
          'innerText': error.message,
        });

        titleNode.after(errorNode);
        return errorNode;
      }

      if (packet.handler && typeof packet.handler?.displayError == 'function') {
        return packet.handler.displayError(error);
      }
    }

    // Display error toast if no appropriate input group
    window.ToastFactory.push({
      type: 'danger',
      message: error.message,
      duration: ENTITY_TOAST_MIN_DURATION,
    });

    return null;
  }

  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/
  /**
   * handleOnLeaving
   * @desc responsible for prompting the user to confirm if they want to leave without saving the page data
   * @param {event} e the associated event
   */
  #handleOnLeaving(e) {
    if (this.#locked) {
      return;
    }
    
    const { data, errors } = this.#collectFieldData();
    if (this.isDirty() || hasDeltaDiff(this.initialisedData, data)) {
      e.preventDefault();
      return e.returnValue = '';
    }
  }
}
