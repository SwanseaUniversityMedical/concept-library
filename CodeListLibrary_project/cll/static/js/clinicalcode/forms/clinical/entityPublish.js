/**
 * Represents a modal for publishing or declining an entity.

  /**
   * Creates a new instance of the PublishModal class.
   * @constructor
   * @param {string} publish_url - The URL to publish the entity.
   * @param {string} decline_url - The URL to decline the entity.
   * @param {string} redirect_url - The URL to redirect to after publishing or declining the entity.
   */
class PublishModal {
  constructor(publish_url, decline_url, redirect_url) {
    this.publish_url = publish_url;
    this.decline_url = decline_url;
    this.redirect_url = redirect_url;
    this.button = document.querySelector("#publish2");
    this.button.addEventListener("click", this.handleButtonClick.bind(this));
  }

  async handleButtonClick(e) {
    e.preventDefault();
    const spinner = startLoadingSpinner();

    try {
      const response = await fetch(this.publish_url, {
        headers: {
          "Cache-Control": "no-cache",
        },
      });
      const data = await response.json();
      spinner.remove();

      const publishButton = [
        {
          name: "Cancel",
          type: ModalFactory.ButtonTypes.REJECT,
          html: `<button class="secondary-btn text-accent-darkest bold washed-accent" id="cancel-button"></button>`,
        },
        {
          name: "Publish",
          type: ModalFactory.ButtonTypes.CONFIRM,
          html: `<button class="primary-btn text-accent-darkest bold secondary-accent" ${
            data.errors ? "disabled" : ""
          } id="publish-modal-button"></button>`,
        },
      ];
      const declineButton = [
        {
          name: "Cancel",
          type: ModalFactory.ButtonTypes.REJECT,
          html: `<button class="secondary-btn text-accent-darkest bold washed-accent" id="cancel-button"></button>`,
        },
        {
          name: "Decline",
          type: ModalFactory.ButtonTypes.CONFIRM,
          html: `<button class="primary-btn text-accent-darkest bold danger-accent"  ${
            data.errors ? "disabled" : ""
          } id="decline-modal-button"></button>`,
        },
        {
          name: "Approve",
          type: ModalFactory.ButtonTypes.CONFIRM,
          html: `<button class="primary-btn text-accent-darkest bold secondary-accent" ${
            data.errors ? "disabled" : ""
          } id="approve-modal-button"></button>`,
        },
      ];

      this.createPublishModal(data, declineButton, publishButton);
    } catch (error) {
      console.error(error);
    }
  }

  /**
   * Sends a POST request to the specified URL with the provided data.
   * @async
   * @param {Object} data - The data to send in the request body.
   * @param {string} url - The URL to send the request to.
   */
  async postData(data, url) {
    const spinner = startLoadingSpinner();
    try {
      const csrfToken = document.querySelector(
        "[name=csrfmiddlewaretoken]"
      ).value;

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
          "Cache-Control": "no-cache",
        },
        body: JSON.stringify(data),
      })
        .then((response) => response.json())
        .then((response) => {

          if (!response || !response?.success) {
            window.ToastFactory.push({
              type: response?.approval_status == 3 ? 'danger' : 'success',
              message: response?.message,
              duration: 5000,
            });
            return;
          }
        })
        .finally(() => {
          spinner.remove();
          setTimeout(() => {
            window.location.href = this.redirect_url + "?eraseCache=true";
          }, 5000);
        });
    } catch (error) {
      spinner.remove();
      console.log(error);
    }
  }

  /**
   * Generates a paragraph with a confirmation message for publishing or approving a clinical entity.
   * @param {Object} data - The data object containing information about the clinical entity.
   * @param {string} data.name - The name of the clinical entity.
   * @param {string} data.entity_type - The type of the clinical entity.
   * @param {number|null} data.approval_status - The approval status of the clinical entity. Can be 1, 3 or null.
   * @param {boolean} data.is_moderator - Indicates whether the user is a moderator.
   * @param {boolean} data.is_lastapproved - Indicates whether the user is the last one to approve the clinical entity.
   * @returns {string} A paragraph with a confirmation message for publishing or approving a clinical entity.
   */
  generateContent(data) {
    let paragraph;
    switch (data.approval_status) {
      case 1:
        paragraph = `<p>Are you sure you want to approve this version of "${data.name}"?</p>
        <p>Published ${data.entity_type} cannot be undone.</p>`;
        break;
      case 3:
        paragraph = `<p>Are you sure you want to approve previously declined version of "${data.name}"?</p>
        <p>This change of ${data.entity_type} cannot be undone.</p>`;
        break;
      case null:
        if (data.is_moderator || data.is_lastapproved) {
          paragraph = `<p>Are you sure you want to publish this version of "${data.name}"?</p>
        <p>Published ${data.entity_type} cannot be undone.</p>`;
        } else {
          paragraph = `<p>Are you sure you want submit to publish this version of "${data.name}"?</p>
          <p>This change of ${data.entity_type} cannot be undone.</p>
          <p>This ${data.entity_type} is going to be reviewed by the moderator and you will be notified when is published</p>`;
        }
        break;
      default:
        paragraph = `<p>Are you sure you want to publish this version of "${data.name}"?</p>
        <p>Published ${data.entity_type} cannot be undone.</p>`;
        break;
    }
    return paragraph;
  }

  /**
   * Creates a modal dialog for publishing an entity.
   *
   * @param {Object} data - The data for the entity being published.
   * @param {Object} declineButton - The button to decline publishing the entity.
   * @param {Object} publishButton - The button to publish the entity.
   */
  createPublishModal(data, declineButton, publishButton) {
    ModalFactory.create({
      id: "publish-dialog",
      title: this.generateTitle(data),
      content: data.errors
        ? this.generateErrorContent(data)
        : this.generateContent(data),
      buttons: data.approval_status === 1 ? declineButton : publishButton,
    })
      .then(async (result) => {
        const name = result.name;
        if (name == "Decline") {
          this.declineEntity(data);
        } else {
          await this.postData(data, this.publish_url);
        }
      })
      .catch((result) => {
        if (!(result instanceof ModalFactory.ModalResults)) {
          return console.error(result);
        }
      });
  }

  /**
   * Declines an entity and prompts the user to provide an explanation for the rejection.
   * @param {Object} data - The data object containing information about the entity to be declined.
   * @param {string} data.name - The name of the entity to be declined.
   * @param {string} data.entity_id - The ID of the entity to be declined.
   * @returns {Promise} A promise that resolves when the entity has been declined and the page has been redirected.
   */
  declineEntity = (data) => {
    window.ModalFactory.create({
      id: "decline-dialog",
      title: `Explanation for rejection ${data.name} - ${data.entity_id}?`,
      content: this.generateDeclineMessage(),
      beforeAccept: (modal) => {
        const form = modal.querySelector("#decline-form-area");
        const textField = modal.querySelector("#id_reject");
        data.rejectMessage = textField.value;
        if (textField.value.trim() === "") {
          window.ToastFactory.push({
            type: "warning",
            message: "Please provide an explanation for the rejection.",
            duration: 5000,
          });
          return false;
        }
        return {
          form: new FormData(form),
          action: form.action,
        };
      },
    })
      .then((result) => {
        return this.postData(data, result.data.action)
      })
      .catch((e) => {
        console.warn(e);
      });
  };

  /**
   * Generates HTML content for displaying errors when an entity cannot be published.
   * @param {Object} data - The data object containing the errors.
   * @param {Array} data.errors - An array of error objects.
   * @param {string} data.errors.url_parent - The URL of the parent entity that caused the error (if applicable).
   * @returns {string} - The HTML content to display the errors.
   */
  generateErrorContent(data) {
    let errorsHtml = "";
    for (let i = 0; i < data.errors.length; i++) {
      if (data.errors[i].url_parent) {
        errorsHtml += `<li class="publish-modal__error"><a class="publish-modal__reference" href="${
          data.errors[i].url_parent
        }"class="publish-modal--text-danger publish-modal--cross" target="_blank">${
          Object.values(data.errors[i])[0]
        }</a></li>`;
      } else {
        errorsHtml += `<li class="publish-modal publish-modal__error"><span class="publish-modal--text-danger publish-modal--cross">${
          Object.values(data.errors[i])[0]
        }</span></li>`;
      }
    }
    let html = `
        <p>This entity cannot be published</p>
        <strong><span class="publish-modal--text-danger publish-modal--cross">Errors:</span></strong>
        <br>
        <ul class="publish-modal publish-modal__errors">${errorsHtml}</ul>`;
    return html;
  }

  /**
   * Generates a title based on the approval status, entity ID, entity type, and name.
   * @param {Object} data - The data object containing the approval status, entity ID, entity type, and name.
   * @returns {string} The generated title.
   */
  generateTitle(data) {
    let title;
    switch (data.approval_status) {
      case 1:
        title = `Approve - ${data.entity_id} ${data.entity_type} - ${data.name}`;
        break;
      case 3:
        title = `Publish declined - ${data.entity_id} ${data.entity_type} - ${data.name}`;
        break;
      default:
        title = `Publish - ${data.entity_id} ${data.entity_type} - ${data.name}`;
        break;
    }
    return title;
  }

  /**
   * Generates a decline message form for the owner of an entity to change details.
   * @returns {string} The HTML string of the decline message form.
   */
  generateDeclineMessage() {
    let maincomponent = `
    <form method="post" id="decline-form-area" action="${this.decline_url}">
        <div class="detailed-input-group fill">
        <h3 class="detailed-input-group__title">Message for owner <span class="detailed-input-group__mandatory">*</span></h3>
        <p class="detailed-input-group__description">The owner of entity will see message to change details</p>
        <textarea class="text-area-input simple" cols="40" id="id_reject" required name="message" rows="10"></textarea>
        </div>
        </form>`;

    return maincomponent;
  }
}

domReady.finally(() => {
  const url_publish = document.querySelector('data[id="publish-url"]');
  const url_decline = document.querySelector('data[id="decline-url"]');
  const redirect_url = document.querySelector('data[id="redirect-url"]');
  window.entityForm = new PublishModal(
    url_publish.innerHTML,
    url_decline.innerHTML,
    redirect_url.innerHTML
  );
});
