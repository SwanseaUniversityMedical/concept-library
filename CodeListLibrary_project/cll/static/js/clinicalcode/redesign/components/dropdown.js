/**
 * DROPDOWN_KEYS
 * @desc Keycodes used to navigate through dropdown
 */
const DROPDOWN_KEYS = {
  // Navigate dropdown
  'DOWN': 40,
  'UP': 38,
};

/**
 * createDropdownSelectionElement
 * @desc Creates an accessible dropdown element
 * @param {node} element the element to apply a dropdown element to
 */
const createDropdownSelectionElement = (element) => {
  const container = createElement('div', {
    'className': 'dropdown-selection',
  });

  const list = createElement('ul', {
    'className': 'dropdown-selection__list',
  });

  const btn = createElement('button', {
    'className': 'dropdown-selection__button',
    'data-value': '',
    'type': 'button'
  });

  const title = createElement('span', {
    'innerText': element.getAttribute('placeholder-text'),
  })

  const icon = createElement('span', {
    'className': 'dropdown-selection__button-icon',
  });

  element.parentNode.insertBefore(container, element)
  element.classList.add('hide');
  container.appendChild(element)
  container.appendChild(list);
  container.insertBefore(btn, list);
  btn.appendChild(title);
  btn.appendChild(icon);

  btn.addEventListener('click', e => {
    list.classList.toggle('active');
  });

  for (let i = 0; i < element.options.length; ++i) {
    const option = element.options[i];    
    const item = createElement('li', {
      'className': 'dropdown-selection__list-item',
      'data-value': option.value,
      'innerText': option.text,
      'aria-label': option.text,
      'tabindex': 0,
      'role': 'button',
    });

    if (option.selected) {
      btn.setAttribute('data-value', option.value);
      title.innerText = option.text.trim();
    }
    
    list.appendChild(item);
    item.addEventListener('click', e => {
      const targetValue = e.target.getAttribute('data-value');
      const targetText = e.target.innerText.trim()
      title.innerText = targetText;
      btn.setAttribute('data-value', targetValue);
      list.classList.remove('active');
      
      option.selected = true;
      element.dispatchEvent(new CustomEvent('change', { bubbles: true, detail: { ignore: true } }));
    });
  }

  const handleKeySelection = (e) => {
    if (!list.classList.contains('active')) {
      return;
    }

    const code = e.keyIdentifier || e.which || e.keyCode;
    if (code != DROPDOWN_KEYS.UP && code != DROPDOWN_KEYS.DOWN) {
      return;
    }

    let target = e.target;
    if (container.contains(target)) {
      e.stopPropagation();
      e.preventDefault();

      const children = Array.from(list.children);
      if (!list.contains(target)) {
        target = children[0];
      }

      let index = children.indexOf(target) + (DROPDOWN_KEYS.UP == code ? -1 : 1);
      index = index > children.length - 1 ? 0 : (index < 0 ? children.length - 1 : index);
      children[index].focus();
    }
  }

  list.onkeyup = handleKeySelection;
  btn.onkeyup = handleKeySelection;

  element.addEventListener('change', e => {
    if (!isNullOrUndefined(e.detail) && 'ignore' in e.detail) {
      return;
    }

    const selected = element.value;
    if (isNullOrUndefined(selected)) {
      return;
    }

    const option = element.querySelector(`option[value="${element.value}"`)
    const targetValue = option.getAttribute('data-value');
    const targetText = option.innerText.trim()
    title.innerText = targetText;
    btn.setAttribute('data-value', targetValue);
  });
  
  document.addEventListener('click', e => {
    const clickedWithinDropdown = container.contains(e.target);
    if (clickedWithinDropdown) {
      return;
    }

    list.classList.remove('active');
  });
};

domReady.finally(() => {
  const dropdowns = document.querySelectorAll('select[data-element="dropdown"]');
  for (let i = 0; i < dropdowns.length; ++i) {
    createDropdownSelectionElement(dropdowns[i]);
  }
});
