"use strict";
// Date checks only. Public facts and links are rendered without JavaScript.
const freshness = document.querySelector("#freshness");
const today = new Intl.DateTimeFormat("en-CA", {timeZone:"America/Chicago",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
const age = (Date.parse(today) - Date.parse(freshness.dataset.asOf)) / 86400000;
if (age > 2) {
  const notice = document.createElement("strong");
  notice.textContent = "This snapshot needs a refresh. ";
  freshness.prepend(notice);
}
// Preserve legacy item links after moving the export off the homepage.
if (/^#ga104-(?:hb|sb|hr|hjr|sjr)\d+$/.test(location.hash)) {
  location.replace("archive.html" + location.search + location.hash);
}
