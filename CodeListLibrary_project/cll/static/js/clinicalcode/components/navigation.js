import FuzzyQuery from './fuzzyQuery.js';

/**
  * updateNavBarStyle
  * @desc Updates the navigation bar style from transparent to opaque dependent on whether the user has scrolled down the page
  * @param {node} navbar The navigation bar element
  */
const updateNavBarStyle = (navbar) => {
  const y = window.scrollY;

  if (window.innerWidth <= 768){
    navbar.classList.remove('transparent')
    return;
  }

  if (y >= navbar.offsetHeight/2 - navbar.offsetTop) {
    navbar.classList.add('scrolled');
    navbar.classList.remove('transparent');
  } else {
    navbar.classList.remove('scrolled');
    navbar.classList.add('transparent');
  }
}

/**
  * computeBurgerProperty
  * @desc Computes the --as-burger CSS property, see SCSS for further information
  * @param {node} burger The hamburger element
  * @returns {value} The value of the computed property
  */
const computeBurgerProperty = (burger) => {
  return window.getComputedStyle(burger, ':after').getPropertyValue('--as-burger').replace(/[^\w!?]/g, '');
}

/**
  * initHamburgerMenu
  * @desc Initialises the hamburger menu for mobiles on the navigation bar
  */
const initHamburgerMenu = () => {
  const burger = document.querySelector('.page-navigation__buttons');
  const panel = document.querySelector('.page-navigation__items');
  const overlay = document.querySelector('.page-navigation__overlay');
  const avatarMenu = document.querySelector('#dropdown-account');
  const submenu = document.querySelector('.nav-dropdown__content');
  const nestedMenu = document.querySelector('.nested-menu');
  
  burger.addEventListener('click', e => {
    if (panel.classList.contains('open')) {
      panel.classList.remove('open');
      avatarMenu?.classList.remove('open');
      submenu?.classList.remove('open');
      nestedMenu?.classList.remove('open');
      overlay.style.display = 'none'; 
    } else {
      const isBurger = computeBurgerProperty(burger);
      if (isBurger === 'true') {
        panel.classList.add('open');
        overlay.style.display = 'block';
        return;
      }
    }
  });

  document.addEventListener('click', e => {
    const element = e.target;

    if (burger.contains(element) || panel.contains(element)) {
      return;
    }
    panel.classList.remove('open');
    avatarMenu?.classList.remove('open');
    submenu?.classList.remove('open');
    nestedMenu?.classList.remove('open');
    overlay.style.display = 'none'; 
  })
}

const submenuMobile = () => {
  // JavaScript for submenu behavior
  const navText = document.querySelector('.nav-dropdown__text');
  const submenu = document.querySelector('.nav-dropdown__content');

  const avataText = document.querySelector('.avatar-content');
  const avatarMenu = document.querySelector('#dropdown-account');

  // Function to toggle submenu visibility
  function toggleSubmenu() {
    submenu.classList.toggle('open');
    avatarMenu?.classList.remove('open');
  }

  // Add click event listener to the "About" link
  navText.addEventListener('click', (e) => {
    e.preventDefault(); // Prevent the default link behavior
    toggleSubmenu();
  });

  if (avatarMenu) {
    avataText.addEventListener('click', (e) => {
      e.preventDefault(); // Prevent the default link behavior
      avatarMenu.classList.toggle('open');
      submenu.classList.remove('open');
    });
  }
}

const searchBar = () => {

  const searchIcon = document.querySelector('.search-navigation__search-icon');
  const searchInput = document.querySelector('.search-navigation__search-input');
  searchIcon.addEventListener('mouseover', (e) => {
    searchInput.focus();
  });
  document.addEventListener('mouseout', (e) => {
    if (searchInput.contains(e.target) || searchIcon.contains(e.target)) {
      return;
    }
    searchInput.blur();
  });
  

}


const nestedMenu = () => {
  const nestedContainer = document.querySelector('.content-container__nested > a');
  const nestedMenu = document.querySelector('.nested-menu');

  if (nestedContainer && nestedMenu) {
    nestedContainer.addEventListener('click', (e) => {
      e.preventDefault();
      nestedMenu.classList.toggle('open');
    });
  }
}

/**
  * setNavigation
  * @desc Sets the navigation bar's buttons to active or inactive dependent on the URL of the page
  * @param {node} navbar The navigation bar element
  */
const setNavigation = (navbar) => {
  const links = navbar.querySelectorAll('.page-navigation__items a');

  let path = getCurrentPath();
  path = path.toLocaleLowerCase();

  let currentBrand = document.documentElement.getAttribute('data-brand');
  if (!isNullOrUndefined(currentBrand)) {
    currentBrand = currentBrand.toLocaleLowerCase();
    path = path.replace(`${currentBrand}\/`, '');
  }
  
  let root = path.match(/^\/(\w+)/);
  root = !isNullOrUndefined(root) ? root[1] : null;

  let distance, closest;
  for (let i = 0; i < links.length; ++i) {
    const link = links[i];

    // match by data-root attribute
    let roots = link.getAttribute('data-root');
    if (root && !isNullOrUndefined(roots)) {
      roots = roots.split(',');
      if (roots.includes(root)) {
        closest = link;
        break;
      }
    }

    // match by link
    let href = link.getAttribute('href');
    href = href.replace(/\/$/, '').toLocaleLowerCase();
    
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
  submenuMobile();
  nestedMenu();
  searchBar();

  document.addEventListener('scroll', e => {
    updateNavBarStyle(navbar);
  });

  initHamburgerMenu();
  setNavigation(navbar);
});
