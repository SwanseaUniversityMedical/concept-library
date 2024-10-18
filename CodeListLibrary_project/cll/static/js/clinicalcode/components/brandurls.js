/**
 * brandUrlsgen
 * @desc ...?
 * @param {*} all_brands 
 * @param {*} prod 
 * @param {*} element 
 * @param {*} old_root 
 * @param {*} path 
 * 
 */
const brandUrlsgen = (all_brands,prod,element,old_root,path) =>{
  let new_root = "";
  if (element.getAttribute('value') != '') {
    new_root = "/" + element.getAttribute('value');
  }

  let indx = 1;
  if (all_brands.indexOf(old_root.toUpperCase()) == -1) {
    indx = 0;
  }

  if (prod != "False") {
    if (
      window.location.href
        .toLowerCase()
        .includes("phenotypes.healthdatagateway".toLowerCase())
    ) {
      if (new_root == "/HDRUK") {
        // do nothing
      } else {
        window.location.href = strictSanitiseString(
          "https://conceptlibrary.saildatabank.com" +
          new_root +
          "/" +
          path.split("/").slice(indx).join("/")
        );
      }
    } else {
      if (new_root == "/HDRUK") {
        new_root = "";
        window.location.href = strictSanitiseString(
          "https://phenotypes.healthdatagateway.org" +
          new_root +
          "/" +
          path.split("/").slice(indx).join("/")
        );
      } else {
        window.location.href = strictSanitiseString(
          "https://conceptlibrary.saildatabank.com" +
          new_root +
          "/" +
          path.split("/").slice(indx).join("/")
        );
      }
    }
  } else {
    window.location.href = strictSanitiseString(
      document.location.origin +
      new_root +
      "/" +
      path.split("/").slice(indx).join("/")
    );
  }
}

/**
 * generateOldPathRoot
 * @desc ...?
 * @returns {array} 
 */
const generateOldPathRoot = () =>{
  let lTrimRegex = new RegExp("^/");
  let lTrim = function (input) {
    return input.replace(lTrimRegex, "");
  };

  let all_brands = [];
  for (let brand in all_brands) {
    all_brands.push(brand.toUpperCase());
  }

  let path = window.location.pathname;
  path = lTrim(path);
  old_root = path.split("/")[0];

  return [path, old_root];
}
