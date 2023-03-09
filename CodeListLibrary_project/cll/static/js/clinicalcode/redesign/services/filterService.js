/**
  * FilterService
  * @desc A class that can be used to control filters for dynamic search pages with dynamic filters
  */

class FilterService {
  constructor() {
    this.filters = { }
    this.#collectFilters();
    this.#collectURLParameters();
    this.#setUpFilters();
  }

  #collectFilters() {
    const filters = document.querySelectorAll('[data-controller="filter"]');
    for (let i = 0; i < filters.length; ++i) {
      const filter = filters[i];
      const filterClass = filter.getAttribute('data-class');
      const filterField = filter.getAttribute('data-field');
      this.filters[filterField] = {
        filter: filter,
        filterClass: filterClass,
      };
    }
  }

  #collectURLParameters() {
    const params = new URL(location == undefined ? window.location.href : location);
    params.searchParams.forEach((value, key) => {
      if (key in this.filters) {
        
      }
    });
  }

  #setUpFilters() {

  }
}

domReady.finally(() => {
  const filters = new FilterService();
  window.filterService = filters;
});
