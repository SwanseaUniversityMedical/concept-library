const TEMPLATE_ELEMENTS = {
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

const renderTemplateDetail = (parent, data) => {
  data.template.forEach((e, _) => {
    let templateDetail = interpolateHTML(TEMPLATE_ELEMENTS.DETAIL, e);
    if ('field_inputs' in e) {
      let itemList = '';
      e.field_inputs.forEach((v, _) => {
        itemList += interpolateHTML(TEMPLATE_ELEMENTS.LIST_ITEM, v);
      });

      templateDetail += `
        <p><strong>Valid inputs:</strong></p>
        <ul>
          ${itemList}
        </ul>`
    }

    const container = createElement('div', {
      'className': 'template-detail__container',
      'innerHTML': templateDetail
    });

    parent.appendChild(container);
  });
}
