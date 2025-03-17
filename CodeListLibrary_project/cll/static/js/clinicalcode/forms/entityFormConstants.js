/**
 * EntityCreator constant(s)
 * 
 */
export const
  /**
   * ENTITY_OPTIONS
   * @desc Defines the ID for the form submission and save draft button(s)
   */
  ENTITY_OPTIONS = {
    // Whether to prompt that the form has been modified when the user tries to leave
    promptUnsaved: true,
    // Whether to force toast errors instead of using the field group
    forceErrorToasts: false,
  },
  /**
   * ENTITY_DATEPICKER_FORMAT
   * @desc Defines how the creator should format dates when producing form values
   */
  ENTITY_DATEPICKER_FORMAT = 'YYYY/MM/DD',
  /**
   * ENTITY_ACCEPTABLE_DATE_FORMAT
   * @desc Defines acceptable date formats
   */
  ENTITY_ACCEPTABLE_DATE_FORMAT = ['DD-MM-YYYY', 'MM-DD-YYYY', 'YYYY-MM-DD'],
  /**
   * ENTITY_TOAST_MIN_DURATION
   * @desc the minimum message time for a toast notification
   */
  ENTITY_TOAST_MIN_DURATION = 5000, // ms, or 5s
  /**
   * ENTITY_FORM_BUTTONS
   * @desc Defines the ID for the form submission and save draft button(s)
   */
  ENTITY_FORM_BUTTONS = {
    'cancel': 'cancel-entity-btn',
    'submit': 'submit-entity-btn',
  },
  /**
   * ENTITY_TEXT_PROMPTS
   * @desc any text that is used throughout the enjtity creator & presented to the user
   */
  ENTITY_TEXT_PROMPTS = {
    // Prompt when cancellation is requested and the data is dirty
    CANCEL_PROMPT: {
      title: 'Are you sure?',
      content: '<p>Are you sure you want to exit this form?</p>'
    },
    // Prompt when attempting to save changes to a legacy version
    HISTORICAL_PROMPT: {
      title: 'Are you sure?',
      content: `
        <p>
          <strong>
            You are saving a legacy Phenotype.
            Updating this Phenotype will overwrite the most recent version.
          </strong>
        </p>
        <p>Are you sure you want to do this?</p>
      `
    },
    // Informs user that they're trying to change group access to null when they've derived access
    DERIVED_GROUP_ACCESS: 'Unable to change group when you\'re deriving access from a group!',
    // Validation error when a field is null
    REQUIRED_FIELD: '${field} field is required, it cannot be empty',
    // Validation error when a field is empty
    INVALID_FIELD: '${field} field is invalid',
    // Message when form is invalid
    FORM_IS_INVALID: 'You need to fix the highlighted fields before saving',
    // Message when user attempts to POST without changing the form
    NO_FORM_CHANGES: 'You need to update the form before saving',
    // Message when POST submission fails due to server error
    SERVER_ERROR_MESSAGE: 'It looks like we couldn\'t save. Please try again',
    // Message when the API fails
    API_ERROR_INFORM: 'An error has occurred, please contact an Admin',
    // Message when a user has failed to confirm / cancel an editable component before attemping to save
    CLOSE_EDITOR: 'Please close the ${field} editor first.'
  };

/**
 * StringInputListCreator constant(s)
 * 
 */
export const 
  /**
   * STR_INPUT_LIST_KEYCODES
   * @desc Keycodes used by list creator
   */
  STR_INPUT_LIST_KEYCODES = {
    // Add list element
    ENTER: 13,
  },
  /**
   * STR_INPUT_LIST_MIN_MSG_DURATION
   * @desc Min. message duration for toast notif popups
   */
  STR_INPUT_LIST_MIN_MSG_DURATION = 5000;

/**
 * PublicationCreator constant(s)
 * 
 */
export const
  /**
   * PUBLICATION_KEYCODES
   * @desc Keycodes used by publication creator
   */
  PUBLICATION_KEYCODES = {
    // Add publication
    ENTER: 13,
  },
  /**
   * PUBLICATION_MIN_MSG_DURATION
   * @desc Min. message duration for toast notif popups
   */
  PUBLICATION_MIN_MSG_DURATION = 5000;
