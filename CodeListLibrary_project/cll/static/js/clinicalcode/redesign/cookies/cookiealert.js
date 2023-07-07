(() => {
  "use strict";

  const cookieAlert = document.querySelector(".cookiealert");
  const cookieCard = document.querySelector(".cookie_card");
  const acceptCookies = document.querySelector(".acceptcookies");
  const rejectCookies = document.querySelector(".rejectcookies");


  if (!cookieAlert) {
    return;
  }

  cookieAlert.offsetHeight; // Force browser to trigger reflow (https://stackoverflow.com/a/39451131)

  const getCookie = (cname) => {
    const name = cname + "=";
    const decodedCookie = decodeURIComponent(document.cookie);
    const ca = decodedCookie.split(';').map(c => c.trim());
    const cookie = ca.find(c => c.indexOf(name) === 0);
    return cookie ? cookie.substring(name.length) : "";
  };

  const setCookie = (cname, cvalue, exdays) => {
    const d = new Date();
    d.setTime(d.getTime() + exdays * 24 * 60 * 60 * 1000);
    const expires = `expires=${d.toUTCString()}`;
    document.cookie = `${cname}=${cvalue}; ${expires}; path=/`;
  };

  // Show the alert if we can't find the "acceptCookies" cookie
  
  if (!getCookie("acceptCookies")) {
    cookieAlert.classList.add("show");
  }else{
    cookieCard.classList.add("show");
  }
  
  if (getCookie("rejectCookies")) {
    cookieAlert.classList.remove("show");
    cookieCard.classList.add("show");
  }


  const handleCookies = (eventName, cookieName, cookieValue) => {
    cookieAlert.classList.remove("show");
    setCookie(cookieName, cookieValue, 365);
    window.dispatchEvent(new Event(eventName));
  };

  acceptCookies.addEventListener("click", () => {
    handleCookies("cookieAlertAccept", "acceptCookies", true);
  });

  rejectCookies.addEventListener("click", () => {
    handleCookies("rejectCookiesAlert", "rejectCookies", false);
  });

  window.handleCookies = handleCookies;

})();
