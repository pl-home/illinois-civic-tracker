/* Progressive enhancement only: the complete historical list is static HTML. */
"use strict";
const controls = document.querySelector("#controls");
const search = document.querySelector("#search");
const type = document.querySelector("#type");
const ceremonial = document.querySelector("#ceremonial");
const records = [...document.querySelectorAll(".record")];
const results = document.querySelector("#results");
const normalize = value => value.toLocaleLowerCase("en-US").replace(/\s+/g, " ").trim();
const searchable = new Map(records.map(record => [record, normalize(record.dataset.search)]));

function filter(updateAddress = true) {
  const words = normalize(search.value).split(" ").filter(Boolean);
  let shown = 0;
  for (const record of records) {
    const matches = (!type.value || record.dataset.type === type.value)
      && (ceremonial.checked || record.dataset.ceremonial !== "true")
      && words.every(word => searchable.get(record).includes(word));
    record.hidden = !matches;
    if (matches) shown++;
  }
  results.textContent = `${shown} of ${records.length} historical measures · newest export action first${ceremonial.checked ? " · ceremonial included" : " · ceremonial hidden"}`;
  document.querySelector("#empty").hidden = shown > 0;
  if (updateAddress) {
    const url = new URL(location.href);
    for (const key of ["q", "type", "ceremonial"]) url.searchParams.delete(key);
    if (search.value.trim()) url.searchParams.set("q", search.value.trim());
    if (type.value) url.searchParams.set("type", type.value);
    if (ceremonial.checked) url.searchParams.set("ceremonial", "1");
    // file: previews may disallow history; filtering still works there.
    try { history.replaceState(null, "", url); } catch (_) { /* no persistence */ }
  }
}

function revealLinkedItem() {
  const id = location.hash.slice(1);
  const record = records.find(item => item.id === id);
  if (!record) return;
  // An explicit item permalink overrides filters so it never opens an invisible item.
  if (record.hidden) {
    search.value = "";
    type.value = "";
    ceremonial.checked = record.dataset.ceremonial === "true";
    filter();
  }
  record.querySelector("details").open = true;
  record.scrollIntoView({block: "start"});
}

function restoreAddress() {
  const params = new URLSearchParams(location.search);
  search.value = params.get("q") || "";
  const requested = params.get("type") || "";
  type.value = [...type.options].some(option => option.value === requested) ? requested : "";
  ceremonial.checked = params.get("ceremonial") === "1";
  filter(false);
  revealLinkedItem();
}

controls.hidden = false;
search.addEventListener("input", () => filter());
type.addEventListener("change", () => filter());
ceremonial.addEventListener("change", () => filter());
document.querySelector("#reset").addEventListener("click", () => {
  search.value = "";
  type.value = "";
  ceremonial.checked = false;
  filter();
  search.focus();
});
addEventListener("hashchange", revealLinkedItem);
addEventListener("popstate", restoreAddress);
restoreAddress();
