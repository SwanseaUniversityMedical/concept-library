const data = [
  {
    "name": "Unity Pugh",
    "extension": "9958",
    "city": "Curicó",
    "start_date": "2005/02/11"
  },
  {
    "name": "Theodore Duran",
    "extension": "8971",
    "city": "Dhanbad",
    "start_date": "1999/04/07"
  },
  {
    "name": "Kylie Bishop",
    "extension": "3147",
    "city": "Norman",
    "start_date": "2005/09/08"
  },
];

const headings = [
  {
    text: "Name",
    data: "name"
  },
  {
    text: "Ext.",
    data: "extension"
  },
  {
    text: "City",
    data: "city"
  },
  {
    text: "Start date",
    data: "start_date"
  }
];

const datatable = new window.simpleDatatables.DataTable(table, {
  perPage: 10,
  perPageSelect: false,
  fixedColumns: false,
  sortable: false,
  labels: {
    perPage: '',
  },
  classes: {
    wrapper: 'overflow-table-constraint',
  },
  template: (options, dom) => `<div class='${options.classes.top}'>
    <div class='${options.classes.dropdown}'>
      <label>
        <select class='${options.classes.selector}'></select> ${options.labels.perPage}
      </label>
    </div>
    <div class='${options.classes.search}'>
      <input
        id="column-searchbar"
        class='${options.classes.input}'
        type='search'
        placeholder='${options.labels.placeholder}'
        title='${options.labels.searchTitle}'
        ${dom.id ? `aria-controls="${dom.id}"` : ""}>
    </div>
    </div>
    <div class='${options.classes.container}'${options.scrollY.length ? ` style='height: ${options.scrollY}; overflow-Y: auto;'` : ""}></div>
    <div class='${options.classes.bottom}'>
    <div class='${options.classes.info}'></div>
    <nav class='${options.classes.pagination}'></nav>
  </div>`,
  data: {
    headings: headings,
    data: data
  },
});