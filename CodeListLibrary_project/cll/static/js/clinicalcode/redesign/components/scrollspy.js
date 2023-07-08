const activateScrollSpyButton = (items, item) => {
  items.forEach((e, _) => {
    e.classList.remove('active');
  });

  item.classList.add('active');
};

domReady.finally(() => {
  const scrollSpyItems = document.querySelectorAll('button.scrollspy__container__item');
  
  scrollSpyItems.forEach((e, _) => {
    const anchor = e.querySelector('a');
    if (isNullOrUndefined(anchor))
      return;

    anchor.addEventListener('click', (event) => {
      event.preventDefault();

      const elem = document.querySelector(anchor.getAttribute('href'));
      if (isNullOrUndefined(elem))
        return;

      elem.scrollIntoView({ behavior: 'instant' });
      setTimeout(() => {
        activateScrollSpyButton(scrollSpyItems, e);
      }, 100);
    });
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
