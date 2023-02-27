import FuzzyQuery from "./fuzzyQuery.js";

const updateNavBarStyle = (navbar) => {
  const y = window.scrollY;
  if (y >= navbar.offsetHeight/2 - navbar.offsetTop) {
    navbar.classList.add('scrolled');
    navbar.classList.remove('transparent');
  } else {
    navbar.classList.remove('scrolled');
    navbar.classList.add('transparent');
  }
}

const computeBurgerProperty = (burger) => {
  return window.getComputedStyle(burger, ':after').getPropertyValue('--as-burger').replace(/[^\w!?]/g, '');
}

const initHamburgerMenu = () => {
  const burger = document.querySelector('.page-navigation__buttons');
  const panel = burger.querySelector('.page-navigation__items');
  
  burger.addEventListener('click', e => {
    if (panel.classList.contains('open'))
      return;
    
    const isBurger = computeBurgerProperty(burger);
    if (isBurger === 'true') {
      panel.classList.add('open');
      return;
    }

    panel.classList.remove('open');
  });

  document.addEventListener('click', e => {
    const element = e.target;
    if (burger.contains(element)) {
      return;
    }

    panel.classList.remove('open');
  })
}

const setNavigation = (navbar) => {
  const links = navbar.querySelectorAll('.page-navigation__items a');

  let path = getCurrentPath();
  path = path.toLocaleLowerCase();

  let distance, closest;
  for (let i = 0; i < links.length; ++i) {
    const link = links[i];

    let href = link.getAttribute('href');
    href = href.replace(/\/$/, '').toLocaleLowerCase();
    if (!FuzzyQuery.Match(path, href)) {
      continue;
    }
    
    const dist = FuzzyQuery.Distance(path, href);
    if (typeof closest === 'undefined' || dist < distance) {
      distance = dist;
      closest = link;
    }
  }

  if (typeof closest !== 'undefined') {
    closest.classList.add('active');
  }
}

domReady.finally(() => {
  const navbar = document.querySelector('.page-navigation');
  updateNavBarStyle(navbar);

  document.addEventListener('scroll', e => {
    updateNavBarStyle(navbar);
  });

  initHamburgerMenu();
  setNavigation(navbar);
});