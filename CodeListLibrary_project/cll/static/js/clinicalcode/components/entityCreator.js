import { collectFormData as collectEntityCreatorFormData, EntityCreator } from '../forms/entityCreator/index.js';

/**
 * Main thread
 * @desc initialises the form after collecting the assoc. form data
 */
domReady.finally(() => {
  const data = collectEntityCreatorFormData();

  window.entityForm = new EntityCreator(data, {
    promptUnsaved: true,
  });
});
