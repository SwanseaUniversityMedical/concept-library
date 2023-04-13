const brandUrlsgen = (all_brands,prod,element,old_root,path) =>{
  
  new_root = "";
  if (element.getAttribute('value') != '') {
    new_root = "/" + element.getAttribute('value');
  }

  indx = 1;
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
        window.location.href =
          "https://conceptlibrary.saildatabank.com" +
          new_root +
          "/" +
          path.split("/").slice(indx).join("/");
          
        }
      } else {
        if (new_root == "/HDRUK") {
          new_root = "";
          window.location.href =
            "https://phenotypes.healthdatagateway.org" +
            new_root +
            "/" +
            path.split("/").slice(indx).join("/");
          
        } else {
          window.location.href =
            "https://conceptlibrary.saildatabank.com" +
            new_root +
            "/" +
            path.split("/").slice(indx).join("/");
          
        }
      }
  } else {
    window.location.href =
      document.location.origin +
      new_root +
      "/" +
      path.split("/").slice(indx).join("/");
  }
}

const generateOldPathRoot = () =>{
  var lTrimRegex = new RegExp("^/");
  var lTrim = function (input) {
    return input.replace(lTrimRegex, "");
  };

  var all_brands = [];
  for (var brand in all_brands) {
    all_brands.push(brand.toUpperCase());
  }


  var path = window.location.pathname;
  path = lTrim(path);
  old_root = path.split("/")[0];

  return [path,old_root];
}
