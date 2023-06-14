/**
 * CONCEPT_UTILS_DEFAULT_ARGS
 * @desc default arguments for concept utility methods
 */
const CONCEPT_UTILS_DEFAULT_ARGS = {
  /* default methods for applyCodelistsFromConcepts() */
  APPLICATOR: {
    // Used to find the given container to apply the codelist to (per Concept's id and version_id)
    codelistContainerId: '#concept-codelist-${concept_id}_${concept_version_id}',
    // Whether or not to render code attributes
    showAttributes: true,
    // How to render the per page select interface
    perPageSelect: [10, 50, 100, ['All', -1]],
  }
};

/**
 * applyCodelistsFromConcepts
 * @desc given an array of concepts objects, this method will apply the codelist of each concept to a given table
 * @param {array[objects]} conceptData the array of concept objects
 * @param {object} options optional parameters to modify the behaviour of the method
 *                         see CONCEPT_UTILS_DEFAULT_ARGS.APPLICATOR for more details
 */
const applyCodelistsFromConcepts = ( conceptData, options = {} ) => {
  options = mergeObjects(options, CONCEPT_UTILS_DEFAULT_ARGS.APPLICATOR);

  const { codelistContainerId, showAttributes, perPageSelect } = options;
  for (let ii = 0; ii < conceptData.length; ii++) {
    const c = conceptData[ii];

    let containerId = interpolateHTML(codelistContainerId, {
      concept_id: c?.concept_id,
      concept_version_id: c?.concept_version_id
    });

    let container = document.querySelector(containerId);        
    let table = container.appendChild(createElement('table', {
      'id': 'codelist-datatable',
      'class': 'constrained-codelist-table__wrapper',
    }));

    let headings = ['Code', 'Description'];
    let columns = [
      { select: 0, type: 'string' },
      { select: 1, type: 'string' },
    ];

    if (c?.details?.code_attribute_headers && showAttributes) {
      for (let i = 0; i < c?.details?.code_attribute_headers.length; i++){
        headings.push(c?.details?.code_attribute_headers?.[i]);
        columns.push({
          select: columns.length,
          type: 'string',
        })
      }
    }

    let data = [];
    if (c?.codelist) {
      data = c?.codelist.map(item => {
        if (item.attributes && showAttributes) {
          return [item?.code, item?.description, ...item?.attributes]
        }

        return [item?.code, item?.description]
      })
    }

    new window.simpleDatatables.DataTable(table, {
      perPageSelect: perPageSelect,
      fixedColumns: false,
      classes: {
        wrapper: 'overflow-table-constraint',
      },
      data: {
        headings: headings,
        data: data,
      }
    });
  }
};
