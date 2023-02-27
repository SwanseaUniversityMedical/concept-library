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