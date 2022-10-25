var isSubset = (arr1, arr2) => {
  return arr1.every(i => arr2.includes(i));
}

var generateUUID = () => {
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

/* jQuery utilities */
var scrollableMap = {
  scroll: true,
  auto: true
};

$.isScrollable = ($elem) => {
  $elem = $($elem);
  return $elem[0] 
          ? (scrollableMap[$elem.css('overflow')]
            || scrollableMap[$elem.css('overflow-x')]
            || scrollableMap[$elem.css('overflow-y')])
          : false;
}

$.isScrollbarVisible = ($elem) => {
  $elem = $($elem);
  return $elem[0] ? $elem[0].scrollHeight > $elem.innerHeight() : false;
}