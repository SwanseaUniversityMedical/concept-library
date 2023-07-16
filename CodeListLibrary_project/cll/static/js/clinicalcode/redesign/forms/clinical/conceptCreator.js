import { parse as parseCSV } from '../../vendor/csv.min.js';
import { ConceptSelectionService } from '../../services/conceptSelectionService.js';

/**
 * tryCleanCodingCSV
 * @desc Attempts to clean a coding CSV such that:
 *          1. leading and trailing null/empty rows are removed
 *          2. separates the first row as a header and the rest as data
 * 
 * @param {array[array[string]]} csv the CSV result array
 * @returns {object} that describes {header: [], data: []}
 */
const tryCleanCodingCSV = (csv) => {
  csv = csv.reduce((filtered, row) => {
    let testRow = row.filter(val => !isNullOrUndefined(val) && !isStringEmpty(val));
    if (testRow.length > 0) {
      filtered.push(testRow);
    }

    return filtered;
  }, []);

  if (csv.length < 2) {
    return { };
  }

  return {
    'header': csv[0],
    'data': csv.slice(1)
  }
}

/**
 * tryCleanCodingRow
 * @desc Attempts to clean a cell, given its col and row, such that:
 *         1. Only returns the first two values of a row - i.e. code & desc
 *         2. Removes leading and trailing whitespace
 * @param {str} val the cell value
 * @param {int} row the row index
 * @param {int} col the col index
 * @returns {str} the value if required
 */
const tryCleanCodingItem = (val, row, col) => {
  if (col > 2) {
    return;
  }
  
  return val.replace(/^\s+|\s+$/gm, '');
}

/**
  * tryParseCodingCSVFile
  * @desc Attempts to parse a file, as returned by an file input element as a CSV.
  * 
  *       The wrapped promise returned does NOT catch errors - it is expected
  *       that exceptions are handled by the caller
  * 
  * @param {object} file The file object as returned by a file input element
  * @returns {promise} A promise that resolves an 2D array, with each outer index 
  *                    representing a row of the CSV's values, and the inner index
  *                    representing a column
  */
const tryParseCodingCSVFile = (file) => {
  return new Promise((resolve, reject) => {
    let fr = new FileReader();
    fr.onload = () => resolve(fr.result);
    fr.onerror = reject;
    fr.readAsText(file, 'UTF-8');
  })
  .then(content => parseCSV(content, {typed: false}, (val, row, col) => tryCleanCodingItem(val, row, col)))
  .then(csv => tryCleanCodingCSV(csv))
}

/**
 * toCodeObjects
 * @desc converts a 2d array of data to {code: str, desc: str} after CSV import
 * @param {array} csv array returned
 * @returns {array} an array of objects describing the codes
 */
const toCodeObjects = (csv) => {
  csv.data = csv?.data.reduce((filtered, value) => {
    filtered.push({
      is_new: true,
      id: generateUUID(),
      code: value[0],
      description: value[1],
    });

    return filtered;
  }, []);

  return csv;
}

/**
 * CONCEPT_CREATOR_OFFSET
 * @desc offset for the editor codelist (i.e., offset after id, code, desc + final)
 */
const CONCEPT_CREATOR_OFFSET = 4;

/**
 * CONCEPT_CREATOR_LOGICAL_TYPES
 * @desc describes the logical types of a concept's components (more may be added in the future)
 */
const CONCEPT_CREATOR_LOGICAL_TYPES = {
  INCLUDE: 'INCLUDE',
  EXCLUDE: 'EXCLUDE'
}

/**
 * CONCEPT_CREATOR_SOURCE_TYPES
 * @desc describes the source types of a concept's components
 */
const CONCEPT_CREATOR_SOURCE_TYPES = {
  CONCEPT: {
    name: 'CONCEPT',
    value: 1,
    template: 'file-rule',
    disabled: true,
  },
  QUERY_BUILDER: { 
    name: 'QUERY_BUILDER',
    value: 2,
    template: 'file-rule',
    disabled: true,
  },
  EXPRESSION: {
    name: 'EXPRESSION',
    value: 3,
    template: 'file-rule',
    disabled: true,
  },
  SELECT_IMPORT: {
    name: 'SELECT_IMPORT',
    value: 4,
    template: 'file-rule',
    disabled: true,
  },
  FILE_IMPORT: {
    name: 'FILE_IMPORT',
    value: 5,
    template: 'file-rule',
    disabled: true,
  },
  SEARCH_TERM: {
    name: 'SEARCH_TERM',
    value: 6,
    template: 'search-rule',
    disabled: false,
  },
  CONCEPT_IMPORT: {
    name: 'CONCEPT_IMPORT',
    value: 7,
    template: 'concept-rule',
    disabled: true,
  },
}

/**
 * CONCEPT_CREATOR_KEYCODES
 * @desc Keycodes used by Concept Creator
 */
const CONCEPT_CREATOR_KEYCODES = {
  // To modify rule name, apply search term etc
  ENTER: 13,
}

/**
 * CONCEPT_CREATOR_FILE_UPLOAD
 * @desc File upload settings for file rule
 */
const CONCEPT_CREATOR_FILE_UPLOAD = {
  allowMultiple: false,
  extensions: ['.csv'],
}

/**
 * CONCEPT_CREATOR_MIN_MSG_DURATION
 * @desc Min. message duration for toast notif popups
 */
const CONCEPT_CREATOR_MIN_MSG_DURATION = 5000; // 5000ms, or 5s

/**
 * CONCEPT_CREATOR_LIMITS
 * @desc Describes limits for components on the page e.g. truncation of strings
 */
const CONCEPT_CREATOR_LIMITS = {
  // Defines max str len for component names when displayed
  STRING_TRUNCATE: 10,
  // Defines how many per page @ default
  PER_PAGE: 10,
  // Defines page select dropdown limits
  PER_PAGE_SELECT: [10, 50, 100],
}

/**
 * CONCEPT_CREATOR_CLASSES
 * @desc Defines the classes assoc. with renderables
 */
const CONCEPT_CREATOR_CLASSES = {
  // The ruleset data icon to show inclusion/exclusion or present/absent state of a code in a codelist
  DATA_ICON: 'ruleset-icon',
}

/**
 * CONCEPT_CREATOR_ICONS
 * @desc Defines the icons for type of incl/excl rules when displayed in codelist
 */
const CONCEPT_CREATOR_ICONS = {
  // Presence icons - used to show whether code is present or absent in a ruleset
  PRESENT: '--present-icon',
  ABSENT: '--absent-icon',

  // Logical type icons - used to show whether a code is included or excluded
  INCLUDE: '--include-icon',
  EXCLUDE: '--exclude-icon',
}

/**
 * CONCEPT_CREATOR_DEFAULTS
 * @desc default constants that are used to build the concept creator
 */
const CONCEPT_CREATOR_DEFAULTS = {
  /* Coding system <select/> for concept editor to determine the current coding system */
  CODING_DEFAULT_HIDDEN_OPTION: '<option value="0" ${is_unselected ? "selected" : ""} hidden>Select Coding System</option>',
  CODING_DEFAULT_ACTIVE_OPTION: '<option value="${value}" ${is_selected ? "selected" : ""}>${name}</option>',

  // ...any
}

/**
 * CONCEPT_CREATOR_TEXT
 * @desc any text that is used throughout the concept creator & presented to the user
 */
const CONCEPT_CREATOR_TEXT = {
  // Edit closure prompt
  CLOSE_EDITOR: {
    title: 'Are you sure?',
    content: '<p>Are you sure you want to close the current editor? You will lose any unsaved progress.</p>',
  },
  // Rule deletion prompt
  RULE_DELETION: {
    title: 'Are you sure?',
    content: '<p>Are you sure you want to delete this Ruleset from your Concept?</p>',
  },
  // Concept deletion prompt
  CONCEPT_DELETION: {
    title: 'Are you sure?',
    content: '<p>Are you sure you want to delete this Concept from your Phenotype?</p>',
  },
  // Toast to inform user to close editor
  REQUIRE_EDIT_CLOSURE: 'Please close the editor before trying to delete a Concept.',
  // Toast for Concept name validation
  REQUIRE_CONCEPT_NAME: 'You need to name your Concept before saving',
  // Toast for Concept CodingSystem validation
  REQUIRE_CODING_SYSTEM: 'You need to select a coding system before saving!',
  // Toast to inform the user that no exclusionary codes were addded since they aren't present in an inclusionary rule
  NO_LINKED_EXCLUSIONS: 'These codes can\'t be excluded when they aren\'t already included',
  // Toast to inform user that no code was matched
  NO_CODE_SEARCH_MATCH: 'No matches for "${value}..."',
  // Toast to inform user we exchanged codes for a null match
  NO_CODE_SEARCH_EXCHANGE: 'No matches for "${value}...", removed ${code_len} codes',
  // Toast to inform user that the search codes were added
  ADDED_SEARCH_CODES: 'Added ${code_len} codes for "${value}..."',
  // Toast to inform user that the search codes were exchanged
  EXCHANGED_SEARCH_CODES: 'Exchanged ${prev_code_len} codes for ${new_code_len} for "${value}..."',
  // Toast to inform the user that the codes from the uploaded files were added
  ADDED_FILE_CODES: 'Added ${code_len} codes via File Upload',
  // Toast to inform the user there was an error when trying to upload their code file
  NO_CODE_FILE_MATCH: 'Unable to parse uploaded file. Please try again.',
  // Toast to inform the user that the codes from the imported concept(s) were added
  ADDED_CONCEPT_CODES: 'Added ${code_len} codes via Concept Import',
  // Toast to inform the user there was an error when trying to upload their code file
  NO_CONCEPT_MATCH: 'We were unable to add this Concept. Please try again.',
  // Toast to inform the user they tried to import non-distinct top-level concepts
  CONCEPT_IMPORTS_ARE_PRESENT: 'Already imported ${failed}',
  // Toast to inform the user they tried to import non-distinct rule-level concepts
  CONCEPT_RULE_IS_PRESENT: 'You have already imported this Concept as a rule',
}

/**
 * ConceptCreator
 * @desc A class that can be used to control concept creation
 * 
 */
export default class ConceptCreator {
  constructor(element, template, data) {
    this.template = template;
    this.data = data || [ ];
    this.element = element;
    this.dirty = false;
    this.state = {
      editing: false,
      data: null,
    };

    this.#collectTemplates();
    this.#setUp();
  }

  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/
  /**
   * isInEditor
   * @desc a method to define editor status
   * @returns {boolean} reflects active editor state
   */
  isInEditor() {
    return !!this.state.editing;
  }

  /**
   * getData
   * @desc gets the current concept data, excluding any current changes
   * @returns {object} current concept data
   */
  getData() {
    return this.data;
  }

  /**
   * getCleanedData
   * @desc gets the submission ready concept data
   * @returns {object} the cleaned concept data
   */
  getCleanedData() {
    const cleaned = [];
    for (let i = 0; i < this.data.length; ++i) {
      const concept = deepCopy(this.data[i]);
      delete concept.aggregatedStateView;

      // Only consider Concepts that have a coding id
      if (isNullOrUndefined(concept?.coding_system?.id)) {
        continue;
      }

      // Clean prev. attributes from our code(s)
      if (concept.details?.code_attribute_headers) {
        concept.components.map(component => {
          const codes = component.codes.map(item => {
            const code = { id: item.id, code: item.code, description: item.description };
            if (item.hasOwnProperty('is_new')) {
              code.is_new = true;
            }

            return code;
          })

          component.codes = codes;
          return component;
        });
      }

      // Clean prev. metadata for new concept(s)
      const codingSystem = concept.coding_system.id;
      delete concept.coding_system;

      concept.details = {
        name: concept.details.name,
        coding_system: codingSystem,
      }

      cleaned.push(concept);
    }

    return cleaned;
  }

  /**
   * isDirty
   * @returns {bool} returns the dirty state of this component
   */
  isDirty() {
    return this.dirty;
  }

  /**
   * getTitle
   * @returns {string|boolean} returns the title of this component if present, otherwise returns false
   */
  getTitle() {
    const group = tryGetRootElement(this.element, 'phenotype-progress__item');
    if (!isNullOrUndefined(group)) {
      const title = group.querySelector('.phenotype-progress__item-title');
      if (!isNullOrUndefined(title)) {
        return title.innerText.trim();
      }
    }
    
    return false;
  }

  /*************************************
   *                                   *
   *               Setter              *
   *                                   *
   *************************************/
  /**
   * makeDirty
   * @desc informs the top-level parent that we're dirty
   *       and updates our internal dirty state
   * @param {int|null} id optional - the id of the concept that is now dirty
   * @param {int|null} historyId optional - the history id of the concept that is now dirty
   * @return {object} return this for chaining
   */
  makeDirty(id, historyId) {
    window.entityForm.makeDirty();
    this.dirty = true;

    if (!isNullOrUndefined(id) && !isNullOrUndefined(historyId)) {
      const concept = this.data.find(item => item.concept_id == id && item.concept_version_id == historyId);
      if (!isNullOrUndefined(concept)) {
        concept.is_dirty = true;
      }
    }

    return this;
  }

  /**
   * clearErrorMessages
   * @desc clears the error messages associated with this component
   */
  clearErrorMessage() {
    const messages = this.element.querySelectorAll('.concepts-view__error');
    for (let i = 0; i < messages.length; ++i) {
      messages[i].remove();
    }
  }

  /**
   * displayError
   * @param {object} error an object describing the error message
   * @returns {node} the error element
   */
  displayError(error) {
    const titleNode = this.element.querySelector('.concepts-view__title');
    const errorNode = createElement('p', {
      'aria-live': 'true',
      'className': 'concepts-view__error',
      'innerText': error.message,
    });
    titleNode.after(errorNode);

    return errorNode;
  }

  /*************************************
   *                                   *
   *               Public              *
   *                                   *
   *************************************/
  /**
   * tryImportConcepts
   * @desc prompts the user to import a Concept as a top-level object,
   *       where the user can select 1 or more concepts to import
   * @returns {promise} that can be used as a Thenable if required
   */
  tryImportConcepts() {
    const prompt = new ConceptSelectionService({
      promptTitle: 'Import Concepts',
      template: this.template?.id,
      allowMultiple: true
    });

    return prompt.show()
      .then((data) => {
        return this.#tryRetrieveCodelists(data);
      });
  }

  /**
   * tryPromptConceptRuleImport
   * @desc tries to prompt the user to import a Concept as a rule,
   *       where the user is only able to select a single concept
   *       that relates to the coding system they're currently working within
   * @returns {promise} a promise that resolves with a concept's data,
   *                    otherwise rejects
   */
  tryPromptConceptRuleImport() {
    const codingSystem = this.state.data.coding_system;
    if (isNullOrUndefined(codingSystem)) {
      return Promise.reject();
    }

    const { id: codingSystemId, name: codingSystemName } = codingSystem;
    if (isNullOrUndefined(codingSystemId) || isNullOrUndefined(codingSystemName)) {
      return Promise.reject();
    }

    const prompt = new ConceptSelectionService({
      promptTitle: `Import Concept as Rule (${codingSystemName})`,
      template: this.template?.id,
      allowMultiple: false,
      ignoreFilters: ['coding_system'],
      forceFilters: {
        coding_system: codingSystemId,
      },
    });

    return prompt.show()
      .then((data) => {
        return this.#tryRetrieveRuleCodelist(data);
      });
  }

  /**
   * tryRetrieveRuleCodelist
   * @desc retrieves the Concept's codelist from the endpoint
   * @param {object} concept the concept to retrieve
   * @returns {object} the retrieved concept
   */
  #tryRetrieveRuleCodelist(concept) {
    const parameters = new URLSearchParams({
      template: this.template?.id,
      concept_id: concept.id,
      concept_version_id: concept.history_id,
    });

    return fetch(
      `${getCurrentURL()}?` + parameters,
      {
        method: 'GET',
        headers: {
          'X-Target': 'import_rule',
          'X-Requested-With': 'XMLHttpRequest',
        }
      }
    )
    .then(response => response.json());
  }

  /**
   * tryRetrieveCodelists
   * @param {list[object]} concepts of type [ {id: [int], history_id: [int] } ]
   * @returns {list[object]} of type [ {concept_id: [int], history_id: [int], codelist: [list] }]
   */
  #tryRetrieveCodelists(concepts) {
    const ids = concepts.map(item => item.id);
    const versions = concepts.map(item => item.history_id);
    const parameters = new URLSearchParams({
      template: this.template?.id,
      concept_ids: ids.join(','),
      concept_version_ids: versions.join(','),
    });

    return fetch(
      `${getCurrentURL()}?` + parameters,
      {
        method: 'GET',
        headers: {
          'X-Target': 'import_concept',
          'X-Requested-With': 'XMLHttpRequest',
        },
      }
    )
    .then(response => response.json())
    .then(response => response.concepts);
  }

  /**
   * tryPromptFileUpload
   * @desc tries to open a file prompt, allowing the user to select the file as defined by
   *       ConceptCreator's const defaults
   * 
   * @returns {promise} a promise that resolves with an object describing the data if
   *                    successfully read + parsed
   */
  tryPromptFileUpload() {
    return new Promise((resolve, reject) => {
      tryOpenFileDialogue({
        ...CONCEPT_CREATOR_FILE_UPLOAD,
        ...{
          callback: (selected, files) => {
            if (!selected) {
              return reject();
            }
    
            const file = files[0];
            tryParseCodingCSVFile(file)
              .then(res => resolve({
                content: toCodeObjects(res),
                fileType: file.type,
              }))
              .catch(e => reject);
          }
        }
      });
    });
  }

  /**
   * tryQueryOptionsParameter
   * @param {string} param the template field name
   * @returns {promise} a promise that resolves with the template's option/source data if successful
   */
  tryQueryOptionsParameter(param) {
    if (!isNullOrUndefined(this.coding_data)) {
      return Promise.resolve(this.coding_data);
    }

    const parameters = new URLSearchParams({
      parameter: param,
      template: this.template?.id,
    });

    return fetch(
      `${getCurrentURL()}?` + parameters,
      {
        method: 'GET',
        headers: {
          'X-Target': 'get_options',
          'X-Requested-With': 'XMLHttpRequest',
        }
      }
    )
    .then(response => response.json())
    .then(response => {
      this.coding_data = response?.result;
      return this.coding_data;
    });
  }
  
  /**
   * tryQueryCodelist
   * @desc given a search term and a coding system id, will attempt to search that table
   *       for codes that match the search term
   * @param {string} searchTerm the search term to match
   * @param {integer} codingSystemId the ID of the coding system to look up
   * @param {boolean} includeDesc whether to incl. the description in the search or not
   * @returns {promise} a promise that resolves with an object describing the results if successful
   */
  tryQueryCodelist(searchTerm, codingSystemId, includeDesc) {
    const encodedSearchterm = encodeURIComponent(searchTerm);
    const query = {
      'template': this.template?.id,
      'search': encodedSearchterm,
      'coding_system': codingSystemId,
      'include_desc': includeDesc,
    }
    
    const parameters = new URLSearchParams(query);
    return fetch(
      `${getCurrentURL()}?` + parameters,
      {
        method: 'GET',
        headers: {
          'X-Target': 'search_codes',
          'X-Requested-With': 'XMLHttpRequest',
        }
      }
    )
    .then(response => response.json());
  }

  /**
   * tryCloseEditor
   * @desc a method to ask the user whether they would like to close the editor
   * @returns {promise} a promise that resovles if the user confirms they are happy to close
   */
  tryCloseEditor() {
    // Resolve if not editing
    if (!this.state.editing) {
      return Promise.resolve();
    }

    // Prompt user to det. whether they want to close the editor despite losing progress
    return new Promise((resolve, reject) => {
      window.ModalFactory.create(CONCEPT_CREATOR_TEXT.CLOSE_EDITOR)
        .then(resolve)
        .catch(reject);
    })
    .then(() => {
      const { id, history_id } = this.state.editing;
      const element = this.state.element;
      const editor = this.state.editor;
      const accordian = element.querySelector('#concept-accordian-header');
      const information = element.querySelector('#concept-information');
      this.state.editing = null;
      this.state.editor = null;
      this.state.element = null;
      this.state.data = null;

      // Remove unaltered, new component if not saved to data
      const obj = this.data.find(item => item.concept_id == id && item.concept_version_id == history_id);
      if (!obj) {
        element.remove();
        this.#toggleNoConceptBox(this.data.length > 0);
        return [id, history_id];
      }

      // Clean up active editor
      element.setAttribute('editing', false);
      information.classList.add('show');
      accordian.classList.remove('is-open');
      editor.remove();

      return [id, history_id];
    })
  }
  
  /**
   * isCodingSystemSearchable
   * @desc determines whether a coding system has a reference table, given a coding system id
   * @param {integer} codingSystemId 
   * @returns {boolean} reflecting whether the reference table exists and is searchable
   */
  isCodingSystemSearchable(codingSystemId) {
    if (isNullOrUndefined(this.coding_data)) {
      return false;
    }

    const codingSystem = this.coding_data.find(item => item.value == codingSystemId);
    return !isNullOrUndefined(codingSystem) && codingSystem?.can_search;
  }

  /*************************************
   *                                   *
   *                Init               *
   *                                   *
   *************************************/
  /**
   * collectTemplates
   * @desc collects all assoc. ConceptCreator template fragments
   */
  #collectTemplates() {
    this.templates = { };
    
    const templates = this.element.querySelectorAll('template');
    for (let i = 0; i < templates.length; ++i) {
      let template = templates[i];
      this.templates[template.getAttribute('id')] = Array.prototype.reduce.call(
        template.content.childNodes,
        (result, node) => result + (node.outerHTML || node.nodeValue),
        ''
      );
    }
  }

  /**
   * setUp
   * @desc main entry point which initialises the ConceptCreator
   */
  #setUp() {
    this.#toggleNoConceptBox(this.data.length > 0);
    if (this.data.length > 0) {
      for (let i = 0; i < this.data.length; ++i) {
        const concept = this.data[i];
        this.#tryRenderConceptComponent(concept);
      }
    }

    // Set up assoc. top-level button(s)
    const createBtn = this.element.querySelector('#create-concept-btn');
    createBtn.addEventListener('click', this.#handleConceptCreation.bind(this));

    const importBtn = this.element.querySelector('#import-concept-btn');
    importBtn.addEventListener('click', this.#handleConceptImporting.bind(this));
  }

  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/
  /**
   * generateConceptRuleSource
   * @desc generates the rule source name for a given concept
   * @param {object} data the concept data returned from the prompt
   * @returns {string} the source name
   */
  #generateConceptRuleSource(data) {
    return `C${data.concept_id}/${data.concept_version_id}`;
  }

  /**
   * getImportedName
   * @desc modifies the concept's name to include its origin as a prefix
   * @param {object} data the concept data
   * @returns {string} the modified name
   */
  #getImportedName(data) {
    const name = data.details.name;
    const { concept_id: id, concept_version_id: history_id } = data;
    return `C${id}/${history_id} - ${name}`;
  }

  /**
   * sieveCodes
   * @desc removes exclusionary codes if not present within an inclusionary rule
   * @param {str} logicalType the rule logical type
   * @param {array[object]} data the code list
   * @param {boolean|null} applyNewAttribute whether to apply the `is_new` attribute
   * @returns {object} the resulting codes 
   */
  #sieveCodes(logicalType, data, applyNewAttribute) {
    if (!Array.isArray(data) || data.length < 1) {
      return [ ];
    }

    const components = this.state.data?.components;
    if (isNullOrUndefined(components) || logicalType == CONCEPT_CREATOR_LOGICAL_TYPES.INCLUDE) {
      if (applyNewAttribute) {
        return data.map(item => {
          item.is_new = true;
          return item;
        });
      }

      return data;
    }

    return data.reduce((filtered, row) => {
      let i;
      let isIncluded = false;
      for (i = 0; i < components.length; ++i) {
        const component = components[i];
        if (component?.logical_type == CONCEPT_CREATOR_LOGICAL_TYPES.EXCLUDE || isNullOrUndefined(component?.codes) || component.codes.length <= 0) {
          continue;
        }

        const index = component.codes.findIndex(item => row.code == item.code);
        if (index >= 0) {
          isIncluded = true;
          break;
        }
      }

      if (isIncluded) {
        if (applyNewAttribute) {
          row.is_new = true;
        }

        filtered.push(row);
      }
  
      return filtered;
    }, []);
  }

  /**
   * isConceptRuleImportDistinct
   * @desc ensures that the concept, imported as a rule in this case,
   *       is distinct for its logical type
   * @param {object} result the imported concept
   * @param {string} logicalType the logical type of the rule i.e. include/exclude
   * @returns {boolean} that reflects its uniqueness
   */
  #isConceptRuleImportDistinct(result, logicalType) {
    const components = this.state.data?.components;
    if (isNullOrUndefined(components)) {
      return true;
    }

    const source = this.#generateConceptRuleSource(result);
    const index = components?.findIndex(item => item?.source == source && item?.logical_type == logicalType);
    return index < 0;
  }

  /**
   * isConceptImportDistinct
   * @desc ensures that the concept, imported as a top-level object in this case,
   *       is distinct
   * @param {object} result the imported concept
   * @returns {boolean} that reflects its uniqueness
   */
  #isConceptImportDistinct(result) {
    const index = this.data.findIndex(item => item?.concept_id == result?.concept_id && item.concept_version_id == result?.concept_version_id);
    return index < 0;
  }

  /**
   * deriveEditAccess
   * @desc derives edit access (whether to render the edit button)
   * @param {object} concept the concept to consider
   * @returns {boolean} reflects edit access
   */
  #deriveEditAccess(concept) {
    const canEdit = !isNullOrUndefined(concept?.details?.has_edit_access) ? concept?.details?.has_edit_access : false;
    const isImported = concept?.imported;
    return canEdit && !isImported;
  }

  /**
   * getNextRuleCount
   * @desc gets n+1 of current rules
   */
  #getNextRuleCount(logicalType) {
    if (isNullOrUndefined(logicalType)) {
      return this.state?.data?.components.length + 1;
    }

    const filtered = this.state?.data?.components.filter(item => item.logical_type == logicalType);
    return filtered.length + 1;
  }

  /**
   * getNextRuleCount
   * @desc gets n+1 of current concepts
   */
  #getNextConceptCount() {
    return this.data.length + 1;
  }

  /**
   * isCodeInclusionary
   * @desc determines whether a code is inclusionary by examining its presence in other components
   * @param {list} item the row item of a code
   * @param {list} components the list of components, either from the editor or from the init data
   * @returns {boolean} reflecting whether that code should be included in the final list
   *                    i.e. it is not excluded by any other exclusionary rules
   */
  #isCodeInclusionary(item, components) {
    const presence = item.slice(3);
    for (let i = 0; i < presence.length; ++i) {
      const present = presence[i];
      if (!present) {
        continue;
      } 

      const component = components[i];
      if (!isNullOrUndefined(component) && component.logical_type == CONCEPT_CREATOR_LOGICAL_TYPES.EXCLUDE) {
        return false;
      }
    }

    return true;
  }

  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/
  /**
   * pushToast
   * @desc Wrapper method around ToastNotificationFactory.js to quickly generate toast notifications
   * @param {*} param0 parameters used by ToastNotificationFactory
   * @returns 
   */
  #pushToast({ type = 'information', message = null, duration = CONCEPT_CREATOR_MIN_MSG_DURATION }) {
    if (isNullOrUndefined(message)) {
      return;
    }

    window.ToastFactory.push({
      type: type,
      message: message,
      duration: Math.max(duration, CONCEPT_CREATOR_MIN_MSG_DURATION),
    });
  }

  /**
   * toggleNoConceptBox
   * @desc toggles the "No available concepts" box visibility
   * @param {boolean} whether to hide the no available concept box
   */
  #toggleNoConceptBox(hide) {
    const noConcepts = this.element.querySelector('#no-available-concepts');
    noConcepts.classList[hide ? 'remove' : 'add']('show');
  }

  /**
   * collapseConcepts
   * @desc method to collapse all concept accordians
   */
  #collapseConcepts() {
    const concepts = this.element.querySelectorAll('.concept-list__group');
    for (let i = 0; i < concepts.length; ++i) {
      const concept = concepts[i];
      if (concept.getAttribute('live')) {
        const accordian = concept.querySelector('#concept-accordian-header');
        accordian.classList.remove('is-open');

        const container = concept.querySelector('#concept-codelist-table');
        container.innerHTML = '';
      }
    }
  }

  /**
   * toggleConcept
   * @desc given a concept group, it will toggle its expanded/collapsed state
   * @param {node} target the concept group element
   * @param {boolean} forceUpdate whether to force update the codelist
   */
  #toggleConcept(target, forceUpdate) {
    const conceptGroup = tryGetRootElement(target, 'concept-list__group');
    const conceptId = conceptGroup.getAttribute('data-concept-id');
    const historyId = conceptGroup.getAttribute('data-concept-history-id');

    const item = conceptGroup.querySelector('#concept-accordian-header');
    if (!isNullOrUndefined(this.state?.editing)) {
      const { id, history_id } = this.state.editing;
      if (conceptId == id && historyId == history_id) {
        return;
      }
    }

    item.classList.toggle('is-open');
    
    const container = conceptGroup.querySelector('#concept-codelist-table');
    if (item.classList.contains('is-open')) {
      // Render codelist
      let dataset = this.data.filter(concept => concept.concept_version_id == historyId && concept.concept_id == conceptId);
      dataset = dataset.shift();

      return this.#tryRenderCodelist(container, dataset);
    }

    // Remove codelist from DOM
    container.innerHTML = '';
  }

  /**
   * tryUpdateRenderConceptComponents
   * @desc Renders the update concepts + components.
   * @param {integer|null|undefined} id optional parameter to toggle open a concept after rendering
   * @param {integer|null|undefined} historyId optional parameter to toggle open a concept after rendering
   * @param {boolean} forceUpdate whether to force update the codelist
   */
  #tryUpdateRenderConceptComponents(id, historyId, forceUpdate) {
    const containerList = this.element.querySelector('#concept-content-list');
    containerList.innerHTML = '';
    
    this.#toggleNoConceptBox(this.data.length > 0);

    if (this.data.length > 0) {
      for (let i = 0; i < this.data.length; ++i) {
        const concept = this.data[i];
        this.#tryRenderConceptComponent(concept);
      }
    }

    // Repoen the concept if given ID and history ID
    if (isNullOrUndefined(id) || isNullOrUndefined(historyId)) {
      return;
    }

    const conceptGroup = containerList.querySelector(`[data-concept-id="${id}"][data-concept-history-id="${historyId}"]`)
    conceptGroup.scrollIntoView();
    this.#toggleConcept(conceptGroup, forceUpdate);
  }

  /**
   * tryRenderConceptComponent
   * @desc renders a concept and its components, and initialises the handlers for its header buttons
   * @param {object} concept the concept data to render
   * @returns {node} the rendered concept group
   */
  #tryRenderConceptComponent(concept) {
    const template = this.templates['concept-item'];
    const access = this.#deriveEditAccess(concept);
    const html = interpolateHTML(template, {
      'concept_name': access ? concept?.details?.name : this.#getImportedName(concept),
      'concept_id': concept?.concept_id,
      'concept_version_id': concept?.concept_version_id,
      'coding_id': concept?.coding_system?.id,
      'coding_system': concept?.coding_system?.description,
      'can_edit': access,
      'subheader': access ? 'Codelist' : 'Imported Codelist',
    });

    const containerList = this.element.querySelector('#concept-content-list');
    const doc = parseHTMLFromString(html);
    const conceptItem = containerList.appendChild(doc.body.children[0]);
    conceptItem.setAttribute('live', true);

    const headerButtons = conceptItem.querySelectorAll('#concept-accordian-header span[role="button"]');
    for (let i = 0; i < headerButtons.length; ++i) {
      headerButtons[i].addEventListener('click', this.#handleConceptHeaderButton.bind(this));
    }

    return conceptItem;
  }

  /**
   * tryRenderCodelist
   * @desc given a Concept dataset, will render a codelist within the container
   * @param {node} container the container to render the elements within
   * @param {object} dataset the dataset to utilise when rendering the codelist (editor or init data)
   * @param {boolean} forceUpdate whether to force update the view
   * @returns {simpleDatatables()} the datatable instance
   */
  #tryRenderCodelist(container, dataset, forceUpdate) {
    const noCodes = container.parentNode.querySelector('#no-available-codelist');

    let rows;
    if (forceUpdate || !Array.isArray(dataset.aggregatedStateView)) {
      rows = [ ];

      const hashset = { };
      const spinner = startLoadingSpinner();
      dataset.components.map((component, index) => {
        const columns = dataset.components.map(item => item.id == component.id);
        component.codes.map(row => {
          let related = hashset?.[row.code];
          if (related) {
            related = rows[related];
            related[index + CONCEPT_CREATOR_OFFSET - 1] = true;
            return;
          }

          hashset[row.code] = rows.length;
          rows.push([
            row.id,
            row.code,
            row.description,
            ...columns
          ]);
        });

        component.code_count = component?.codes ? component?.codes.length : 0;
      });
      dataset.aggregatedStateView = rows;
      spinner.remove();
    } else {
      rows = dataset.aggregatedStateView || [ ];
    }

    if (rows.length < 1) {
      noCodes.classList.add('show');
      return;
    }

    const table = container.appendChild(createElement('table', {
      'id': 'codelist-datatable',
      'class': 'constrained-codelist-table__wrapper',
    }));
    noCodes.classList.remove('show');

    return new window.simpleDatatables.DataTable(table, {
      perPage: CONCEPT_CREATOR_LIMITS.PER_PAGE,
      perPageSelect: CONCEPT_CREATOR_LIMITS.PER_PAGE_SELECT,
      fixedColumns: false,
      columns: [
        {
          select: 0,
          type: 'string',
          render: this.#tryRenderRuleTypeIcon.bind(this),
        },
        { select: 1, type: 'string' },
        { select: 2, type: 'string' },
      ],
      classes: {
        wrapper: 'overflow-table-constraint',
      },
      data: {
        headings: ['Final State', 'Code', 'Description'],
        data: rows.map(item => {
          const isIncluded = this.#isCodeInclusionary(item, dataset?.components || []);
          return [isIncluded, item[1], item[2]];
        }),
      }
    });
  }

  /**
   * fetchCodingOptions
   * @desc fetches and returns rendered options, and given a Concept's dataset, will select the associated option
   * @param {object} dataset the dataset and its coding system to compare to determine whether selected
   * @returns {promise} a promise that resolves with a Coding System's options
   */
  #fetchCodingOptions(dataset) {
    // Fetch coding system from server
    const promise = this.tryQueryOptionsParameter('coding_system')
      .then(codingSystems => {
        // Build <select/> option HTML
        let options = interpolateHTML(CONCEPT_CREATOR_DEFAULTS.CODING_DEFAULT_HIDDEN_OPTION, {
          'is_unselected': codingSystems.length  < 1,
        });

        // Sort alphabetically in desc. order
        codingSystems.sort((a, b) => {
          if (a.name < b.name) {
            return -1;
          }

          return (a.name > b.name) ? 1 : 0;
        });
    
        // Build each coding system option
        for (let i = 0; i < codingSystems.length; ++i) {
          const item = codingSystems[i];
          options += interpolateHTML(CONCEPT_CREATOR_DEFAULTS.CODING_DEFAULT_ACTIVE_OPTION, {
            'is_selected': item.value == dataset?.coding_system?.id,
            'name': item.name,
            'value': item.value,
          });
        }

        return options;
      });

    return promise;
  }

  /**
   * tryRenderRuleTypeIcon
   * @desc renders a boolean inclusion/exclusion rule as an icon
   * @param {object} data the row data
   * @param {*} id the column id
   * @param {integer} rowIndex the index of the row
   * @param {integer} cellIndex the index of the cell
   * @returns {string} interpolated element html
   */
  #tryRenderRuleTypeIcon(data, id, rowIndex, cellIndex) {
    const icon = CONCEPT_CREATOR_CLASSES.DATA_ICON;
    const alt = data ? CONCEPT_CREATOR_ICONS.INCLUDE : CONCEPT_CREATOR_ICONS.EXCLUDE;
    return `<span class="${icon} ${icon}--align-center ${icon}${alt}"></span>`
  }

  /**
   * tryRenderRulePresenceIcon
   * @desc renders a boolean present/absent rule as an icon
   * @param {*} value value of the column
   * @param {integer} index index of the column
   * @returns {string} interpolated element html
   */
  #tryRenderRulePresenceIcon(value, index) {
    const alt = value.logical_type == CONCEPT_CREATOR_LOGICAL_TYPES.INCLUDE ? CONCEPT_CREATOR_ICONS.PRESENT : CONCEPT_CREATOR_ICONS.ABSENT;
    return {
      select: CONCEPT_CREATOR_OFFSET + index,
      type: 'string',
      render: (data, td, rowIndex, cellIndex) => {
        const icon = CONCEPT_CREATOR_CLASSES.DATA_ICON;
        if (data) {
          return `<span class="${icon} ${icon}--align-center ${icon}${alt}"></span>`
        }

        return ' ';
      }
    }
  }

  /**
   * updateEditorCodelistColumn
   * @desc updates the headings for the codelist if a ruleset's name is changed
   * @param {integer} index the index of the heading
   * @param {string} value the string value to replace the heading's name with
   */
  #updateEditorCodelistColumns(index, value) {
    if (!this.state.editing) {
      return;
    }

    const datatable = this.state?.activeCodelist;
    if (!datatable) {
      return;
    }

    if (datatable?.data?.headings && datatable.data.headings[CONCEPT_CREATOR_OFFSET + index]) {
      datatable.data.headings[CONCEPT_CREATOR_OFFSET + index].data = value.substring(0, CONCEPT_CREATOR_LIMITS.STRING_TRUNCATE);
      datatable.update();
    }
  }

  /**
   * applyRulesetState
   * @desc applies the ruleset state to the child concepts, see inner comments for details
   * @param {*} param0 { id: integer<CodingSystemId>, editor: node<Element>, ignoreSelection: boolean }
   */
  #applyRulesetState({ id, editor, ignoreSelection = false }) {
    if (!this.state.editing) {
      return;
    }

    // Disable ruleset addition if no coding system present
    const hasCodingSystem = !isNullOrUndefined(id);
    const rulesetBtns = editor.querySelectorAll('.dropdown-btn input[type="radio"]');
    for (let i = 0; i < rulesetBtns.length; ++i) {
      rulesetBtns[i].disabled = !hasCodingSystem;
    }

    // Change visibility of coding system
    const dropdownOptions = editor.querySelectorAll('.dropdown-btn li');
    for (let i = 0; i < dropdownOptions.length; ++i) {
      const option = dropdownOptions[i];
      const optionSource = option.getAttribute('data-source');
      if (optionSource == CONCEPT_CREATOR_SOURCE_TYPES.SEARCH_TERM.name) {
        if (!this.isCodingSystemSearchable(id)) {
          option.classList.add('hide');
          continue;
        }
        option.classList.remove('hide');
      }
    }

    // Only disable/enable the coding selector if not updated via the change event
    if (ignoreSelection) {
      return;
    }

    // Don't allow users to reselect the coding system once we've created at least 1 rule + selected a system
    const selector = editor.querySelector('#coding-system-select')
    selector.disabled = hasCodingSystem;

    // Only enable to change event if no coding system is present
    if (hasCodingSystem) {
      return;
    }
    selector.addEventListener('change', this.#handleCodingSelection.bind(this));
  }

  /**
   * tryRenderRuleItem
   * @desc attempts to render a ruleset item and its associated fields
   * @param {integer} index the index of this particular ruleset
   * @param {object} rule the ruleset data
   * @param {node} ruleList the container to render the component within
   */
  #tryRenderRuleItem(index, rule, ruleList) {
    const source = rule?.source;
    const sourceType = rule?.source_type;
    if (!CONCEPT_CREATOR_SOURCE_TYPES.hasOwnProperty(sourceType)) {
      return;
    }

    const sourceInfo = CONCEPT_CREATOR_SOURCE_TYPES[sourceType];
    const template = this.templates[sourceInfo.template];
    const html = interpolateHTML(template, {
      'id': rule?.id,
      'index': index,
      'name': rule?.name,
      'source': (isNullOrUndefined(source) && sourceInfo.template == 'file-rule') ? 'Unknown File' : (source || ''),
    });

    const doc = parseHTMLFromString(html);
    const item = ruleList.appendChild(doc.body.children[0]);
    const input = item.querySelector('input[data-item="rule"]');

    // Add handler for each rule type, otherwise disable element
    if (sourceInfo.disabled) {
      input.disabled = true;
    } else {
      // e.g. search, any future rules - can ignore file-rule because it should already be imported
      switch (sourceInfo.template) {
        case 'search-rule': {
          this.#handleSearchRule(index, input);
        } break;

        default: break;
      }
    }

    // Handle name change of each rule
    this.#handleRuleNameChange(index, rule, item);

    // Handle deletion of individual rules
    this.#handleRuleDeletion(index, item);
  }

  /**
   * toggleRuleAreas
   * @desc updates the rule area so that it contextually displays the codelist or info panel
   *       given the inclusionary/exclusionary rules
   * @param {list} rules the list of rules and its associated data
   * @param {node} area the ruleset area of this concept
   */
  #toggleRuleAreas(rules, area) {
    const showRules = !isNullOrUndefined(rules) && rules.length > 0;
    const noRules = area.querySelector('#no-rules');
    const ruleList = area.querySelector('#rules-list');

    if (!showRules) {
      noRules.classList.add('show');
      ruleList.classList.remove('show');
      return;
    }

    ruleList.classList.add('show');
    noRules.classList.remove('show');
  }

  /**
   * tryRenderRules
   * @desc attempts to render all rules within inclusionary/exclusionary lists
   * @param {list} rules the list of rules and its associated data
   * @param {node} inclusionArea the inclusionary area element
   * @param {node} exclusionArea the exclusionary area element
   */
  #tryRenderRules(rules, inclusionArea, exclusionArea) {
    // Toggle visibility
    if (isNullOrUndefined(rules) || rules.length < 0) {
      this.#toggleRuleAreas(rules, inclusionArea);
      this.#toggleRuleAreas(rules, exclusionArea);
      return;
    }

    const inclusionary = rules.filter(item => item.logical_type == CONCEPT_CREATOR_LOGICAL_TYPES.INCLUDE);
    const exclusionary = rules.filter(item => item.logical_type == CONCEPT_CREATOR_LOGICAL_TYPES.EXCLUDE);
    this.#toggleRuleAreas(inclusionary, inclusionArea);
    this.#toggleRuleAreas(exclusionary, exclusionArea);

    // Cleanup
    const includeRuleList = inclusionArea.querySelector('#rules-list');
    includeRuleList.innerHTML = '';

    const excludeRuleList = exclusionArea.querySelector('#rules-list');
    excludeRuleList.innerHTML = '';

    // Render each rule
    for (let i = 0; i < rules.length; ++i) {
      const rule = rules[i];
      this.#tryRenderRuleItem(
        i,
        rule,
        rule.logical_type == CONCEPT_CREATOR_LOGICAL_TYPES.INCLUDE ? includeRuleList : excludeRuleList
      );
    }
  }

  /**
   * tryRenderRulesets
   * @desc attempts to render all rules within a concept
   */
  #tryRenderRulesets() {
    if (!this.state.editing) {
      return;
    }

    const editor = this.state?.editor;
    const components = this.state?.data?.components;
    
    const inclusionArea = editor.querySelector('#inclusion-rulesets');
    const exclusionArea = editor.querySelector('#exclusion-rulesets');
    this.#tryRenderRules(components, inclusionArea, exclusionArea);
  }
 
  /**
   * tryRenderAggregatedCodelist
   * @desc attempts to render the aggregated codelist after considering its presence and logical type
   * @param {boolean} forceUpdate whether to force an update of the rows e.g. in the case of adding codes
   * @returns {simpleDatatables()} the rendered aggregated codelist within the simpleDatatables class
   */
  #tryRenderAggregatedCodelist(forceUpdate) {
    if (!this.state.editing) {
      return;
    }

    const editor = this.state.editor;
    const noCodes = editor.querySelector('#no-available-codelist');
    const container = editor.querySelector('#aggregated-codelist-table');
    container.innerHTML = '';

    let codes;
    if (forceUpdate || !Array.isArray(this.state?.data?.aggregatedStateView)) {
      codes = [ ];

      const hashset = { };
      for (let i = 0; i < this.state?.data?.components.length; ++i) {
        let component = this.state?.data?.components[i];

        const columns = this.state?.data?.components.map(item => item.id == component.id);
        for (let j = 0; j < component?.codes.length; ++j) {
          let row = component?.codes?.[j];
          let related = hashset?.[row.code];
          if (!isNullOrUndefined(related)) {
            codes[related][i + CONCEPT_CREATOR_OFFSET - 1] = true;
            continue;
          }

          hashset[row.code] = codes.length;
          codes.push([
            row.id,
            row.code,
            row.description,
            ...columns
          ]);
        }

        component.code_count = component?.codes ? component?.codes.length : 0;
      }

      this.state.data.aggregatedStateView = codes;
    } else {
      codes = this.state?.data?.aggregatedStateView || [ ];
    }

    if (codes.length < 1) {
      noCodes.classList.add('show');
      return;
    }

    const table = container.appendChild(createElement('table', {
      'id': 'codelist-datatable',
      'class': 'constrained-codelist-table__wrapper',
    }));
    noCodes.classList.remove('show');

    this.state.activeCodelist = new window.simpleDatatables.DataTable(table, {
      perPage: CONCEPT_CREATOR_LIMITS.PER_PAGE,
      perPageSelect: CONCEPT_CREATOR_LIMITS.PER_PAGE_SELECT,
      fixedColumns: false,
      columns: [
        {
          select: 0,
          type: 'string',
          render: this.#tryRenderRuleTypeIcon.bind(this),
        },
        { select: 1, hidden: true },
        { select: 2, type: 'string' },
        { select: 3, type: 'string' },
        ...this.state?.data?.components.map((_, index) => this.#tryRenderRulePresenceIcon(_, index)),
      ],
      classes: {
        wrapper: 'overflow-table-constraint',
      },
      data: {
        headings: [
          'Final State', 'id', 'Code', 'Description',
          ...this.state?.data?.components.map(component => {
            if (component.name.length > 10) {
              return `${component.name.substring(0, CONCEPT_CREATOR_LIMITS.STRING_TRUNCATE)}...`
            }

            return component.name;
          }),
        ],
        data: codes.map(item => {
          const isIncluded = this.#isCodeInclusionary(item, this.state.data.components);
          return [isIncluded, ...item]
        }),
      }
    });

    return this.state.activeCodelist;
  }

  /**
   * tryRenderEditor [async]
   * @desc async method to render the editor when a user enters the editor state
   * @param {node} conceptGroup the concept group node related to the Concept being edited
   * @param {object} dataset the concept dataset
   * @returns {node} the editor element
   */
  async #tryRenderEditor(conceptGroup, dataset) {
    const conceptId = conceptGroup.getAttribute('data-concept-id');
    const historyId = conceptGroup.getAttribute('data-concept-history-id');
    
    if (isNullOrUndefined(dataset)) {
      return;
    }
    this.#collapseConcepts();

    const information = conceptGroup.querySelector('#concept-information');
    const accordian = conceptGroup.querySelector('#concept-accordian-header');
    information.classList.remove('show');
    accordian.classList.add('is-open');
    conceptGroup.setAttribute('editing', true);

    const systemOptions = await this.#fetchCodingOptions(dataset);
    const template = this.templates['concept-editor'];
    const html = interpolateHTML(template, {
      'concept_name': dataset?.details?.name,
      'coding_system_id': dataset?.coding_system?.id,
      'coding_system_options': systemOptions,
      'has_inclusions': false,
      'has_exclusions': false,
    });

    const doc = parseHTMLFromString(html);
    const editor = conceptGroup.appendChild(doc.body.children[0]);
    this.state.data = dataset;
    this.state.editor = editor;
    this.state.element = conceptGroup;
    this.state.editing = { id: conceptId, history_id: historyId };
    this.#applyRulesetState({ id: dataset?.coding_system?.id, editor: editor});
    this.#tryRenderRulesets();

    // Handle name changing
    const conceptNameInput = editor.querySelector('#concept-name');
    conceptNameInput.addEventListener('keyup', this.#handleConceptNameChange.bind(this));

    // Handle ruleset button
    const dropdownOptions = editor.querySelectorAll('.dropdown-btn li');
    for (let i = 0; i < dropdownOptions.length; ++i) {
      const option = dropdownOptions[i];
      option.addEventListener('click', this.#handleRulesetAddition.bind(this));
    }

    // Handle editor submission
    const cancelChanges = editor.querySelector('#cancel-changes');
    cancelChanges.addEventListener('click', this.#handleCancelEditor.bind(this));

    const confirmChanges = editor.querySelector('#confirm-changes');
    confirmChanges.addEventListener('click', this.#handleConfirmEditor.bind(this));
    
    // Render codelist
    this.#tryRenderAggregatedCodelist();

    return editor;
  }

  /**
   * tryAddNewRule
   * @desc attempts to add a new rule to the concept's rule groups, and appends the renderable
   * @param {string} logicalType the logical type of the rule i.e. include/exclude
   * @param {object} sourceType an object retrieved from the ConceptCreator's sourceType map
   * @param {object|null} data only required during file uploads, passed from the resolved promise after prompt
   */
  #tryAddNewRule(logicalType, sourceType, data) {
    if (!this.state.editing) {
      return;
    }

    // Create new rule
    const ruleIncrement = this.#getNextRuleCount(logicalType);
    const element = this.state.element;
    const ruleArea = logicalType == CONCEPT_CREATOR_LOGICAL_TYPES.INCLUDE ? 'inclusion' : 'exclusion'
    const rule = {
      id: generateUUID(),
      name: `${transformTitleCase(ruleArea)} ${ruleIncrement}`,
      code_count: 0,
      source_type: sourceType.name,
      logical_type: logicalType,
      is_new: true,
    }

    switch (sourceType.template) {
      case 'search-rule': {
        rule.source = null;
        rule.codes = [ ];
      } break;

      case 'file-rule': {
        rule.source = data?.fileType;
        rule.codes = data?.content?.data;
      } break;

      case 'concept-rule': {
        const ruleSource = this.#generateConceptRuleSource(data);
        rule.name = `Imported from ${ruleSource}`
        rule.source = ruleSource;
        rule.codes = data?.codelist;
      } break;

      default: break;
    }

    const ruleList = element.querySelector(`#${ruleArea}-rulesets #rules-list`);
    const index = this.state.data.components.push(rule) - 1;
    this.#tryRenderRuleItem(index, rule, ruleList);

    // Toggle rule area
    let area, rules;
    switch (logicalType) {
      case 'INCLUDE': {
        area = this.state.editor.querySelector('#inclusion-rulesets');
        rules = this.state.data.components.filter(item => item.logical_type == CONCEPT_CREATOR_LOGICAL_TYPES.INCLUDE);
      } break;

      case 'EXCLUDE': {
        area = this.state.editor.querySelector('#exclusion-rulesets');
        rules = this.state.data.components.filter(item => item.logical_type == CONCEPT_CREATOR_LOGICAL_TYPES.EXCLUDE);
      } break;
    }
    this.#toggleRuleAreas(rules, area);

    if (rule.codes.length > 0) {
      this.#tryRenderAggregatedCodelist(true);
      this.state.data.components[index].code_count = rule.codes.length;
    }
    this.#applyRulesetState({ id: this.state.data.coding_system.id, editor: this.state.editor });

    // Open most relevant checkbox, hide the rest
    const checkboxes = element.querySelectorAll(`.fill-accordian__input`);
    for (let i = 0; i < checkboxes.length; ++i) {
      let checkbox = checkboxes[i];
      checkbox.checked = checkbox.matches(`#rule-${rule.id}`);
    }
  }

  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/
  /**
   * handleRuleDeletion
   * @desc initialises the deletion handler for a ruleset
   * @param {integer} index the index of this ruleset
   * @param {node} item the ruleset element
   */
  #handleRuleDeletion(index, item) {
    const deleteBtn = item.querySelector('#remove-rule-btn');
    deleteBtn.addEventListener('click', (e) => {
      if (!this.state.editing) {
        return;
      }

      new Promise((resolve, reject) => {
        window.ModalFactory.create(CONCEPT_CREATOR_TEXT.RULE_DELETION)
        .then(resolve)
        .catch(reject);
      })
      .then(() => {
        this.state.data.components.splice(index, 1);
        
        this.#tryRenderRulesets();
        this.#tryRenderAggregatedCodelist(true);
      })
      .catch((e) => {
        if (!isNullOrUndefined(e)) {
          console.warn(e);
        }
      });
    });
  }

  /**
   * handleCodingSelection
   * @desc handles the selection of coding systems whilst editing a Concept's ruleset
   * @param {event} e the event object
   */
  #handleCodingSelection(e) {
    if (!this.state.editing) {
      return;
    }

    const target = e.target;
    const selection = target.options[target.selectedIndex];
    this.state.data.coding_system = {
      id: parseInt(selection.value),
      name: selection.text,
      description: selection.text,
    };

    this.#applyRulesetState({ id: selection.value, editor: this.state.editor, ignoreSelection: true });
  }

  /**
   * handleRuleNameChange
   * @desc initialises the name change input for a given ruleset
   * @param {integer} index the index of this ruleset
   * @param {object} rule the rule dataset
   * @param {node} item the ruleset element
   */
  #handleRuleNameChange(index, rule, item) {
    const input = item.querySelector('input#rule-name');
    input.addEventListener('keyup', (e) => {
      e.preventDefault();
      e.stopPropagation();

      const value = input.value;
      if (!input.checkValidity() || isNullOrUndefined(value) || isStringEmpty(value)) {
        input.classList.add('fill-accordian__name-input--invalid');
        return;
      }

      input.classList.remove('fill-accordian__name-input--invalid');

      this.state.data.components[index].name = value;
      this.#updateEditorCodelistColumns(index, value);
    });
  }

  /**
   * handleSearchRule
   * @desc initialises the search input for search-related rules
   * @param {integer} index the index of this rule
   * @param {node} input the search input element
   */
  #handleSearchRule(index, input) {
    const searchBtn = input.parentNode.querySelector('.code-text-input__icon');
    if (!isNullOrUndefined(searchBtn)) {
      searchBtn.addEventListener('click', (e) => {
        input.dispatchEvent(new KeyboardEvent('keyup', { keyCode: CONCEPT_CREATOR_KEYCODES.ENTER }));
      });
    }

    input.addEventListener('keyup', (e) => {
      const code = e.keyIdentifier || e.which || e.keyCode;
      if (code != CONCEPT_CREATOR_KEYCODES.ENTER) {
        return;
      }

      const value = input.value;
      if (!input.checkValidity() || isNullOrUndefined(value) || isStringEmpty(value)) {
        return;
      }

      e.preventDefault();
      e.stopPropagation();

      let includeDesc = input.parentNode.parentNode.querySelector('input[name="search-method"]:checked');
      includeDesc = !isNullOrUndefined(includeDesc) ? 1 : 0;

      const spinner = startLoadingSpinner();
      this.tryQueryCodelist(value, this.state.data?.coding_system?.id, includeDesc)
        .then(response => {
          const logicalType = this.state.data.components[index].logical_type;
          const codes = this.#sieveCodes(
            logicalType,
            response?.result,
            true
          );

          // Update row
          const prevCodeLength = this.state.data.components?.[index]?.codes?.length;
          this.state.data.components[index].codes = codes.length > 0 ? codes : [ ];
          this.state.data.components[index].source = codes.length > 0 ? value : null;
          this.state.data.components[index].code_count = codes.length;

          // Blur the input focus
          input.blur();

          // Apply changes and recompute codelist
          if (codes.length > 0) {
            this.#tryRenderAggregatedCodelist(true);
          }

          // Inform of null results 
          if (codes.length < 1) {
            // Null as a result of there being no exclusionary matches
            if (logicalType == CONCEPT_CREATOR_LOGICAL_TYPES.EXCLUDE) {
              this.#pushToast({
                type: 'warning',
                message: CONCEPT_CREATOR_TEXT.NO_LINKED_EXCLUSIONS
              });

              return;
            }

            // Either (a) inform of loss of codes or (b) that no codes were added
            if (prevCodeLength) {
              this.#pushToast({
                type: 'danger',
                message: interpolateHTML(
                  CONCEPT_CREATOR_TEXT.NO_CODE_SEARCH_EXCHANGE,
                  {
                    value: value.substring(0, CONCEPT_CREATOR_LIMITS.STRING_TRUNCATE),
                    code_len: prevCodeLength,
                  }
                )
              });

              return;
            }

            this.#pushToast({
              type: 'danger',
              message: interpolateHTML(
                CONCEPT_CREATOR_TEXT.NO_CODE_SEARCH_MATCH,
                {
                  value: value.substring(0, CONCEPT_CREATOR_LIMITS.STRING_TRUNCATE)
                }
              )
            });
            
            return;
          }

          // If we reran search / changed search term, inform user of exchange count
          if (prevCodeLength) {
            this.#pushToast({
              type: 'success',
              message: interpolateHTML(
                CONCEPT_CREATOR_TEXT.EXCHANGED_SEARCH_CODES,
                {
                  prev_code_len: prevCodeLength,
                  new_code_len: codes.length.toLocaleString(),
                  value: value.substring(0, CONCEPT_CREATOR_LIMITS.STRING_TRUNCATE),
                }
              )
            });

            return;
          }

          // Inform user of result count
          this.#pushToast({
            type: 'success',
            message: interpolateHTML(
              CONCEPT_CREATOR_TEXT.ADDED_SEARCH_CODES,
              {
                code_len: codes.length.toLocaleString(),
                value: value.substring(0, CONCEPT_CREATOR_LIMITS.STRING_TRUNCATE),
              }
            )
          });
        })
        .catch(() => { /* SINK */ })
        .finally(() => {
          spinner.remove();
        });
    });
  }

  /**
   * handleRulesetAddition
   * @desc handles the addition of rulesets via the dropdown selection menu
   * @param {event} e the associated event
   */
  #handleRulesetAddition(e) {
    const target = e.target;
    const dropdown = target.parentNode.parentNode;
    const logicalType = dropdown.getAttribute('data-type');

    let sourceType = target.getAttribute('data-source');
    sourceType = CONCEPT_CREATOR_SOURCE_TYPES[sourceType];
    
    switch (sourceType.template) {
      case 'file-rule': {
        let spinner;
        this.tryPromptFileUpload()
          .then(file => {
            const codes = this.#sieveCodes(
              logicalType,
              file?.content?.data
            );

            if (codes.length > 0) {
              spinner = startLoadingSpinner();
              file.content.data = codes;
  
              this.#tryAddNewRule(logicalType, sourceType, file);
              this.#pushToast({
                type: 'success',
                message: interpolateHTML(CONCEPT_CREATOR_TEXT.ADDED_FILE_CODES, {
                  code_len: file?.content?.data.length.toLocaleString(),
                })
              });

              return;
            }

            this.#pushToast({
              type: 'warning',
              message: CONCEPT_CREATOR_TEXT.NO_LINKED_EXCLUSIONS
            });

            return 
          })
          .catch(e => {
            console.warn(e);
            this.#pushToast({ type: 'danger', message: CONCEPT_CREATOR_TEXT.NO_CODE_FILE_MATCH});
          })
          .finally(() => {
            if (!isNullOrUndefined(spinner)) {
              spinner.remove();
            }
          });
      } break;

      case 'search-rule': {
        this.#tryAddNewRule(logicalType, sourceType);
      } break;

      case 'concept-rule': {
        let spinner;
        this.tryPromptConceptRuleImport()
          .then(result => {
            spinner = startLoadingSpinner();
            if (!this.#isConceptRuleImportDistinct(result, logicalType)) {
              this.#pushToast({ type: 'danger', message: CONCEPT_CREATOR_TEXT.CONCEPT_RULE_IS_PRESENT});
              return;
            }

            const codes = this.#sieveCodes(logicalType, result?.codelist);
            if (codes.length > 0) {
              result.codelist = codes;

              this.#tryAddNewRule(logicalType, sourceType, result);
              this.#pushToast({
                type: 'success',
                message: interpolateHTML(CONCEPT_CREATOR_TEXT.ADDED_CONCEPT_CODES, {
                  code_len: result?.codelist.length.toLocaleString(),
                })
              });

              return;
            }

            this.#pushToast({
              type: 'warning',
              message: CONCEPT_CREATOR_TEXT.NO_LINKED_EXCLUSIONS
            });
          })
          .catch(e => {
            if (!isNullOrUndefined(e)) {
              this.#pushToast({ type: 'danger', message: CONCEPT_CREATOR_TEXT.NO_CONCEPT_MATCH});
              console.error(e);
              return;
            }
          })
          .finally(() => {
            if (!isNullOrUndefined(spinner)) {
              spinner.remove();
            }
          });
      } break;

      default: break;
    }

    setTimeout(() => {
      let inputs = dropdown.querySelector('#close-ruleset-selection');
      inputs.click();
    }, 50);
  }

  /**
   * handleConceptNameChange
   * @desc updates the concept's name within the editor dataset
   * @param {event} e the associated event
   */
  #handleConceptNameChange(e) {
    const input = e.target;
    const value = input.value;
    if (!input.checkValidity() || isNullOrUndefined(value) || isStringEmpty(value)) {
      return;
    }

    e.preventDefault();
    e.stopPropagation();

    this.state.data.details.name = value;
  }

  /**
   * handleCancelEditor
   * @desc closes the editor when the user interacts with the cancel button
   * @param {event} e the associated event
   */
  #handleCancelEditor(e) {
    const conceptGroup = tryGetRootElement(e.target, 'concept-list__group');
    this.tryCloseEditor()
      .then((res) => {
        this.#toggleConcept(conceptGroup);
        return;
      })
      .then((res) => {
        this.element.scrollIntoView();
      })
      .catch(() => { /* User does not want to lose progress, sink edit request */ })
  }

  /**
   * handleConfirmEditor
   * @desc handles prompting the user and saving the data when they interact with the confirm button
   * @param {event} e the associated event
   */
  #handleConfirmEditor(e) {
    const data = this.state.data;

    // Validate the concept data
    if (isNullOrUndefined(data?.details?.name) || isStringEmpty(data?.details?.name)) {
      this.#pushToast({ type: 'danger', message: CONCEPT_CREATOR_TEXT.REQUIRE_CONCEPT_NAME });
      return;
    }

    if (isNullOrUndefined(data?.coding_system)) {
      this.#pushToast({ type: 'danger', message: CONCEPT_CREATOR_TEXT.REQUIRE_CODING_SYSTEM});
      return;
    }
    
    // Clean the data
    this.state.editing = null;
    this.state.editor = null;
    this.state.element = null;
    this.state.data = null;
    
    // Create or update the concept given the editor data
    let index = this.data.findIndex(item => item.concept_id == data.concept_id && item.concept_version_id == data.concept_version_id);
    let isNew = index < 0;
    if (isNew) {
      this.data.push(data);
    } else {
      this.data[index] = data;
    }

    // Reset the interface
    this.#tryUpdateRenderConceptComponents(data.concept_id, data.concept_version_id, true);

    // Inform the parent form we're dirty
    this.makeDirty(data?.concept_id, data?.concept_version_id);
  }

  /**
   * handleConceptImporting
   * @desc handles the importing of a concept when a user interacts with the assoc. button
   * @param {event} e the assoc. event
   */
  #handleConceptImporting(e) {
    this.tryCloseEditor()
      .then(() => {
        return this.tryImportConcepts();
      })
      .then((concepts) => {
        const failedImports = [];
        for (let i = 0; i < concepts.length; ++i) {
          const data = concepts[i];
          if (!this.#isConceptImportDistinct(data)) {
            failedImports.push(this.#generateConceptRuleSource(data));
            continue;
          }

          data.imported = true;
          this.data.push(data);

          this.#tryRenderConceptComponent(data);
        }
        this.#toggleNoConceptBox(this.data.length > 0);

        if (failedImports.length > 0) {
          this.#pushToast({
            type: 'danger',
            message: interpolateHTML(CONCEPT_CREATOR_TEXT.CONCEPT_IMPORTS_ARE_PRESENT, {
              failed: failedImports.join(', '),
            }),
          });
        }
      })
      .catch((e) => {
        if (!isNullOrUndefined(e)) {
          console.error(e);
        }
      })
  }

  /**
   * handleConceptCreation
   * @desc handles the creation of a concept when the user selects the 'Add Concept' button
   * @param {event} e the associated event 
   */
  #handleConceptCreation(e) {
    this.tryCloseEditor()
      .then(() => {
        const conceptIncrement = this.#getNextConceptCount();
        const concept = {
          is_new: true,
          concept_id: generateUUID(),
          concept_version_id: generateUUID(),
          components: [ ],
          details: {
            name: `Concept ${conceptIncrement}`,
            has_edit_access: true,
          },
        }

        const conceptGroup = this.#tryRenderConceptComponent(concept);
        this.#tryRenderEditor(conceptGroup, concept);
        this.#toggleNoConceptBox(true);
      })
      .catch(() => { /* User does not want to lose progress, sink edit request */ })
  }

  /**
   * handleEditing
   * @desc transitions the user into the editor mode, and prompts the user to confirm if they're already editing
   * @param {node} target the target concept group
   */
  #handleEditing(target) {
    // If editing, prompt before continuing
    return this.tryCloseEditor()
      .then((res) => {
        const spinner = startLoadingSpinner();
        const [id, history_id] = res || [ ];
        const conceptGroup = tryGetRootElement(target, 'concept-list__group');
        const conceptId = conceptGroup.getAttribute('data-concept-id');
        const historyId = conceptGroup.getAttribute('data-concept-history-id');

        // Don't edit this target if we are cancelling the same one
        if (conceptId == id && history_id == historyId) {
          spinner.remove();
          return this.#toggleConcept(conceptGroup);
        }

        // Render the editor
        let dataset = this.data.filter(concept => concept.concept_version_id == historyId && concept.concept_id == conceptId);
        dataset = deepCopy(dataset.shift());

        this.#tryRenderEditor(conceptGroup, dataset);
        spinner.remove();
      })
      .catch(() => { /* User does not want to lose progress, sink edit request */ })
  }

  /**
   * handleDeletion
   * @desc prompts & handles the deletion of concepts when the user interacts with the trash icon
   * @param {node} target the target concept group
   * @returns {promise} that resolves if the user deletes the concept
   */
  #handleDeletion(target) {
    if (this.state.editing) {
      this.#pushToast({ type: 'danger', message: CONCEPT_CREATOR_TEXT.REQUIRE_EDIT_CLOSURE });
      return;
    }

    return new Promise((resolve, reject) => {
        window.ModalFactory.create(CONCEPT_CREATOR_TEXT.CONCEPT_DELETION).then(resolve).catch(reject);
      })
      .then(() => {
        const conceptGroup = tryGetRootElement(target, 'concept-list__group');
        const conceptId = conceptGroup.getAttribute('data-concept-id');
        const historyId = conceptGroup.getAttribute('data-concept-history-id');

        // Remove if it's a concept that's in our dataset
        const index = this.data.findIndex(item => item.concept_id == conceptId && item.concept_version_id == historyId);
        if (index < 0) {
          return;
        }
        this.data.splice(index, 1);
        
        // Reset the interface
        this.#tryUpdateRenderConceptComponents();
        this.element.scrollIntoView();

        // Inform the parent form we're dirty
        this.makeDirty();
      })
      .catch((e) => {
        if (!isNullOrUndefined(e)) {
          console.error(e);
        }
      });
  }

  /**
   * handleConceptHeaderButton
   * @desc switch method to determine which handler is necessary to undertake the event
   *       when the user interacts with the header buttons of a Concept's accordian
   * @param {event} e the associated event
   */
  #handleConceptHeaderButton(e) {
    const target = e.target;
    const method = target.getAttribute('data-target');
    switch (method) {
      case 'is-open': {
        this.#toggleConcept(target);
      } break;

      case 'edit': {
        this.#handleEditing(target);
      } break;
      
      case 'delete': {
        this.#handleDeletion(target);
      } break;

      default: break;
    }
  }
}
