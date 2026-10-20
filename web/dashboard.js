"use strict";
// Progressive enhancement: public facts and links work without JavaScript.
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
const hearingDay = document.querySelector('#hearing-day');
const hearingCommittee = document.querySelector('#hearing-committee');
function filterHearings() {
  document.querySelectorAll('[data-hearing-day]').forEach(row => {
    row.hidden = (hearingDay.value && row.dataset.hearingDay !== hearingDay.value)
      || (hearingCommittee.value && row.dataset.hearingCommittee !== hearingCommittee.value);
  });
  const shown = [...document.querySelectorAll('.hearing-nav-row')].filter(row => !row.hidden).length;
  document.querySelector('#hearing-filter-count').textContent = `${shown} distinct hearing notices`;
  document.querySelector('#hearing-no-match').hidden = shown !== 0;
}
if (hearingDay && hearingCommittee) {
  hearingDay.addEventListener('change', filterHearings);
  hearingCommittee.addEventListener('change', filterHearings);
  document.querySelector('#hearing-reset').addEventListener('click', () => {
    hearingDay.value = ''; hearingCommittee.value = ''; filterHearings();
  });
}
// An old saved/static page must not keep advertising an expired verification.
document.querySelectorAll('.verified-slip').forEach(link => {
  const hours = (Date.now() - Date.parse(link.dataset.verifiedAt)) / 3600000;
  if (!Number.isFinite(hours) || hours < 0 || hours > 24) {
    link.href = link.dataset.notice;
    link.textContent = 'Witness-form verification expired; check the official notice ↗';
    link.classList.remove('verified-slip');
  }
});
