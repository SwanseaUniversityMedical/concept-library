/**
  * stickifyTable
  * @desc A function that makes a row's cells fixed in position (when scrolling) if they include the case '.sticky'
  */
const stickifyTable = (table) => {
  const rows = table.querySelectorAll('tr');
  for (let i = 0; i < rows.length; ++i) {
    const row = rows[i];
    const sticky = row.querySelectorAll('.sticky');

    let offset = 0;
    for (let j = 0; j < sticky.length; ++j) {
      const child = sticky[j];
      child.style.setProperty('--column-offset', `${offset}px`);
      offset += child.getBoundingClientRect().width;
    }
  }
}

export { stickifyTable }