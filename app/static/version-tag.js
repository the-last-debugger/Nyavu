/* The build number beside the download link, for pages that do not load the whole app.

   It is a file rather than an inline script because the content security policy allows
   scripts from this origin only, which is the correct policy and which silently blocks
   anything written into the page itself. */
fetch("/api/app/version")
  .then(function (r) { return r.ok ? r.json() : null; })
  .then(function (d) {
    if (!d || !d.version) return;
    document.querySelectorAll("#appVersion, #footAppVersion").forEach(function (el) {
      el.textContent = d.version;
    });
  })
  .catch(function () { /* the link still works without the label */ });
