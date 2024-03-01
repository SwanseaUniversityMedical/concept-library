/**
 * activateScrollSpyButton
 * @desc controls the `active` class within scrollspy elements
 * @param {array|object<NodeList>} items the element(s) associated with the scrollspy
 * @param {node} item the currently selected element
 * 
 */
const activateScrollSpyButton = (items, item) => {
  items.forEach((e, _) => {
    e.classList.remove('active');
  });

  item.classList.add('active');
};

/**
 * handleScrollspyClick
 * @desc handles the interaction with the scrollspy
 * @param {object<Event>} event the associated `click` event
 * @param {node} anchor the associated `<a/>` element
 * @param {node} e the associated scrollspy element
 * 
 */
const handleScrollspyClick = (event, anchor, e) => {
  event.preventDefault();

  const elem = document.querySelector(anchor.getAttribute('href'));
  if (isNullOrUndefined(elem))
    return;

  elem.scrollIntoView({ behavior: 'instant' });
  setTimeout(() => {
    activateScrollSpyButton(scrollSpyItems, e);
  }, 100);
};


/**
 * Main thread
 * @desc initialises the component once the dom is ready
 * 
 */
domReady.finally(() => {
  const scrollSpyItems = document.querySelectorAll('button.scrollspy__container__item');

  scrollSpyItems.forEach((e, _) => {
    const anchor = e.querySelector('a');
    if (isNullOrUndefined(anchor))
      return;

    anchor.setAttribute('tabindex', -1);
    e.addEventListener('click', event => handleScrollspyClick(event, anchor, e));    
    anchor.addEventListener('click', event => handleScrollspyClick(event, anchor, e));    
  });

  const targetItems = document.querySelectorAll('span.scrollspy-target');
  window.onscroll = () => {
    let scrollY = window.scrollY;
    let bodyRect = document.body.getBoundingClientRect();
    targetItems.forEach((e, i) => {
      let linkedItem = document.querySelector(
        `button.scrollspy__container__item[data-target='#${e.id}']`
      );
      
      if (isNullOrUndefined(linkedItem))
        return;

      let parent = tryGetRootNode(e, 'SECTION');
      if (isNullOrUndefined(parent))
        return;
      
      let parentRect = parent.getBoundingClientRect();
      let elementRect = e.getBoundingClientRect();
      let offset = elementRect.top - bodyRect.top + e.offsetTop,
          height = parentRect.height;      

      if (scrollY >= offset && scrollY < offset + height) {
        activateScrollSpyButton(scrollSpyItems, linkedItem);
      }
    })
  }
});
