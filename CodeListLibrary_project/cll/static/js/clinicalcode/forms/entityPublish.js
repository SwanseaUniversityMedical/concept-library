/**
 * @class PublishModal
 * @author @zinnurov - Artur Zinnurov
 * @notes originally located within `./forms/clinical` - relocated to `./forms/`
 * @desc A class that controls the publication modal used to publish entities within the detail page,
 *       controls both moderator & normal client usage
 * 
 */
class PublishModal {
  constructor(publish_url, decline_url, redirect_url) {
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
      spinner?.remove?.();

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
          const redir = data?.is_moderator && !data?.org_user_managed
            ? `${getBrandedHost()}/moderation/`
            : strictSanitiseString(this.redirect_url+'?eraseCache=true');

          if (name == "Decline") {
            await this.postData(data, this.decline_url);
          } else {
            await this.postData(data, this.publish_url);
          }

          window.location.href = redir;
        })
        .catch((result) => {
          if (!!result && !(result instanceof ModalFactory.ModalResults)) {
            return console.error(result);
          }
        });
    } catch (error) {
      console.error(error);
      spinner?.remove?.();
    }
  }

  async postData(data, url) {
    const spinner = startLoadingSpinner();
    try {
      await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie('csrftoken'),
          "Cache-Control": "no-cache",
        },
        body: JSON.stringify(data),
      }).then(response => {
        if (!response.ok) {
          return Promise.reject(response);
        }
        return response.json();
      }).finally(() => {
        spinner?.remove?.();
      });
    } catch (error) {
      spinner?.remove?.();
      console.error(error);
    }
  }

  generateContent(data) {
    let paragraph;
    switch (data.approval_status) {
      case 1:
        paragraph =
          `<p>Are you sure you want to approve this version of "${data.name}"?</p>` +
          `<p>Publishing a ${data.branded_entity_cls} cannot be undone.</p>`;
        break;

      case 3:
        paragraph =
          `<p>Are you sure you want to approve a previously declined version of "${data.name}"?</p>` +
          `<p>Changes made to this ${data.branded_entity_cls} cannot be undone.</p>`;
        break;

      default:
        if (data.is_moderator || data.is_lastapproved) {
          paragraph =
            `<p>Are you sure you want to publish this version of "${data.name}"?</p>` +
            `<p>Publishing a ${data.branded_entity_cls} cannot be undone.</p>`;
        } else {
          paragraph = 
            `<p>Are you sure you want to publish this version of "${data.name}"?</p>` +
            `<p>This ${data.branded_entity_cls} is going to be reviewed by the moderator; you will be notified via e-mail when they have decided to publish your work.</p>`;
        }
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
        title = `Approve - ${data.entity_id} ${data.branded_entity_cls} - ${data.name}`;
        break;
      case 3:
        title = `Publish declined - ${data.entity_id} ${data.branded_entity_cls} - ${data.name}`;
        break;
      default:
        title = `Publish - ${data.entity_id} ${data.branded_entity_cls} - ${data.name}`;
        break;
    }
    return title;
  }
}

domReady.finally(() => {
  const publish_url = document.querySelector('script[id="publish-url"]');
  const decline_url = document.querySelector('script[id="decline-url"]');
  const redirect_url = document.querySelector('script[id="redirect-url"]');
  window.entityForm = new PublishModal(
    strictSanitiseString(publish_url.innerText.trim()),
    strictSanitiseString(decline_url.innerText.trim()),
    strictSanitiseString(redirect_url.innerText.trim())
  );
});
