const cookieSettings = (privacyurl) => {
  ModalFactory.create({
    id: 'cookie-dialog',
    title: 'Privacy Settings',
    content: `
      <p>
        We use cookies and similar technologies that are necessary to operate the website. Additional cookies
        are only used with your consent.
      <p>
      </p>
        We use the additional cookies to perform analyses of website usage and to check marketing measures for their efficiency.
        These analyses are carried out to provide you with a better user experience on the website.
      <p>
        Please note that you are free to give, deny, or withdraw your consent at any time by using the <em>"cookie settings"</em> link at the bottom of each page.
        Otherwise, you can consent to our use of cookies by clicking <em>"Save selection"</em>.
      </p>
      <p>
        For more information about what information is collected and how it is shared with our partners, please read our <a href="${privacyurl}" target=_blank rel="noopener">Privacy and cookie policy</a>.
      </p>
      <div class="checkbox-item-container min-size">
        <input id="neccesary-cookies" type="checkbox" disabled checked class="checkbox-input" data-value="1" data-name="must-cookies"/>
        <label for="neccesary-cookies">Necesary cookies</label>
      </div>
      <div class="checkbox-item-container min-size">
        <input id="stats-check"  type="checkbox" class="checkbox-input" data-value="0" data-name="analytics"/>
        <label for="stats-check">Analytics</label.
      </div>
      <p>Monitoring website usage and optimizing the user experience.</p>
    `,
    buttons: [
      {
        name: 'Cancel',
        type: ModalFactory.ButtonTypes.REJECT,
        html: `<button class="secondary-btn text-accent-darkest bold washed-accent" id="cancel-button"></button>`,
      },
      {
        name: 'Save selection',
        type: ModalFactory.ButtonTypes.CONFIRM,
        html: `<button class="primary-btn text-accent-darkest bold secondary-accent" id="save-button"></button>`,
      },
    ]
  })
  .catch((result) => {
    // An error occurred somewhere (unrelated to button input)
    if (!!result && !(result instanceof ModalFactory.ModalResults)) {
      return console.error(result);
    }
  });
}
