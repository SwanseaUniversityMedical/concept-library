/**
 * DETAIL_PG_TEMPLATE_ELEMENTS
 * @desc HTML elements associated with the template element(s)
 * 
 */
const DETAIL_PG_TEMPLATE_ELEMENTS = {
  DETAIL: ' \
    <p><strong>Name: </strong>${field_name}<p> \
    <p><strong>Type: </strong>${field_type}<p> \
    <p><strong>Mandatory: </strong>${field_mandatory}<p> \
    <p><strong>Description: </strong>${field_description}</p>',

  LIST_ITEM: ' \
    <li> \
      ${value}: ${id} \
    </li>'
}

/**
 * renderTemplateDetail
 * @desc responsible for rendering the details of each
 *       template within the `./technical-details.html` page
 * 
 * @param {node} parent the parent container
 * @param {object} data the template data as derived from the API
 * 
 */
const renderTemplateDetail = (parent, data) => {
  data.template.forEach((e, _) => {
    let templateDetail = interpolateString(DETAIL_PG_TEMPLATE_ELEMENTS.DETAIL, e);
    if ('field_inputs' in e) {
      let itemList = '';
      e.field_inputs.forEach((v, _) => {
        itemList += interpolateString(DETAIL_PG_TEMPLATE_ELEMENTS.LIST_ITEM, v);
      });

      templateDetail += `
        <p><strong>Valid inputs:</strong></p>
        <ul>
          ${itemList}
        </ul>`
    }

    const container = createElement('div', {
      'className': 'template-detail__container',
      'innerHTML': {
        src: templateDetail,
        noSanitise: true,
      }
    });

    parent.appendChild(container);
  });
}
