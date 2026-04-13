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
 * @desc given a concept object, this method will apply the codelist to its related table element
 * @param {object} conceptData the concept object
 * @param {object} options optional parameters to modify the behaviour of the method
 *                         see CONCEPT_UTILS_DEFAULT_ARGS.APPLICATOR for more details
 */
const applyCodelistsFromConcepts = (conceptData, options) => {
  options = mergeObjects(options || { }, CONCEPT_UTILS_DEFAULT_ARGS.APPLICATOR);

  const { codelistContainerId, showAttributes, perPageSelect } = options;
  const containerId = interpolateString(codelistContainerId, {
    concept_id: conceptData?.concept_id,
    concept_version_id: conceptData?.concept_version_id
  });

  const outOfDate = conceptData?.details?.latest_version?.is_out_of_date;
  if (!isNullOrUndefined(outOfDate) && outOfDate) {
    const target = document.querySelectorAll(`#ood-${conceptData?.concept_id}-${conceptData?.concept_version_id}`);
    for (let j = 0; j < target.length; ++j) {
      target[j].classList.remove('hide');
    }
  }

  const container = document.querySelector(containerId);
  const table = container.appendChild(createElement('table', {
    'id': 'codelist-datatable',
    'class': 'constrained-codelist-table__wrapper',
  }));

  const headings = ['Code', 'Description'];
  const columns = [
    { select: 0, type: 'string' },
    { select: 1, type: 'string' },
  ];

  const attributeHeaders = conceptData?.details?.code_attribute_header;
  if (attributeHeaders && showAttributes) {
    for (let j = 0; j < attributeHeaders.length; ++j) {
      headings.push(attributeHeaders?.[j]);
      columns.push({
        select: columns.length,
        type: 'string',
      });
    }
  }

  let data = [];
  if (conceptData?.codelist) {
    data = conceptData?.codelist.map(item => {
      if (attributeHeaders && showAttributes) {
        const attributes = Array(attributeHeaders.length).fill('[No data]');
        if (item?.attributes) {
          for (let j = 0; j < attributeHeaders.length; ++j) {
            attributes[j] = item.attributes?.[j] || attributes[j];
          }
        }
        
        return [item?.code, item?.description, ...attributes]
      }

      return [item?.code, item?.description]
    })
  }

  new window.simpleDatatables.DataTable(table, {
    perPageSelect: perPageSelect,
    fixedColumns: false,
    classes: {
      wrapper: 'overflow-table-constraint',
      container: 'datatable-container slim-scrollbar',
    },
    data: {
      headings: headings,
      data: data,
    }
  });
};
