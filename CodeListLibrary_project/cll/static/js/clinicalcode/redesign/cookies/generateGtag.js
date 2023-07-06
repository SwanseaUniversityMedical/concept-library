const generateTag = (type,configId, parameters) => {
  window.dataLayer = window.dataLayer || [];

  function gtag() {
    dataLayer.push(arguments);
  }
  gtag("js", new Date());

  gtag("consent", type , parameters);
  gtag("config", configId);
};
