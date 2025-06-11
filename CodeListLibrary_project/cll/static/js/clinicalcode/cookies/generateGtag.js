const generateTag = (type,configId, parameters) => {
  window.dataLayer = window.dataLayer || [];

  function gtag() {
    dataLayer.push(arguments);
  }

  gtag("js", new Date());
  gtag("consent", type , parameters);
  gtag("config", configId);
};

const removeGATags = () => {
  const gaScripts = Array.from(document.querySelectorAll("script[src*='google-analytics.com']"));
  gaScripts.forEach(gaScript => {
    gaScript.remove();
  });
};

window.removeGATags = removeGATags;
