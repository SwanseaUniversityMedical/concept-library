/**
 * @class PublishModal
 * @author @zinnurov - Artur Zinnurov
 * @notes originally located within `./forms/clinical` - relocated to `./forms/`
 * @desc A class that controls the publication modal used to publish entities within the detail page,
 *       controls both moderator & normal client usage
 * 
 */
class PublishModal {
  constructor(publish_url, decline_url,redirect_url) {
    this.publish_url = publish_url;
    this.decline_url = decline_url;
    this.redirect_url = redirect_url;
    this.button = document.querySelector("#publish-btn");
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
      console.log(data);

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
            await this.postData(data, this.decline_url);
            window.location.href = this.redirect_url+'?eraseCache=true';
          } else {
            await this.postData(data, this.publish_url);
            window.location.href = this.redirect_url+'?eraseCache=true';
          }
        })
        .catch((result) => {
          if (!(result instanceof ModalFactory.ModalResults)) {
            return console.error(result);
          }
        });
    } catch (error) {
      console.error(error);
    }
  }

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
      }).then(response => {
        if (!response.ok) {
          return Promise.reject(response);
        }
        return response.json();
      }).finally(() => {
        spinner.remove();
      });

    } catch (error) {
      spinner.remove();
      console.log(error);
    }
  }

  generateContent(data) {
    let paragraph;
    switch (data.approval_status) {
      case 1:
        paragraph = `<p>Are you sure you want to approve this version of "${data.name}"?</p>
        <p>Publishing a ${data.entity_type} cannot be undone.</p>`;
        break;
      case 3:
        paragraph = `<p>Are you sure you want to approve previously declined version of "${data.name}"?</p>
        <p>Changes made to this ${data.entity_type} cannot be undone.</p>`;
        break;
      case null:
        if (data.is_moderator || data.is_lastapproved) {
          paragraph = `<p>Are you sure you want to publish this version of "${data.name}"?</p>
        <p>Publishing a ${data.entity_type} cannot be undone.</p>`;
        } else {
          paragraph = `<p>Are you sure you want submit to publish this version of "${data.name}"?</p>
          <p>Changes made to this ${data.entity_type} cannot be undone.</p>
          <p>This ${data.entity_type} is going to be reviewed by the moderator and you will be notified when is published</p>`;
        }
        break;
      default:
        paragraph = `<p>Are you sure you want to publish this version of "${data.name}"?</p>
        <p>Publishing a ${data.entity_type} cannot be undone.</p>`;
        break;
    }
    return paragraph;
  }

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
