// Runs only on the 404 page, before gtag. Keep genuine broken article links
// measurable; exclude the missing contact/CMS endpoints observed in GA4.
(() => {
  let path;
  try {
    path = decodeURIComponent(window.location.pathname).replace(/\/+$/, '');
  } catch {
    return;
  }
  const probes = new Set([
    '/company/contact', '/contact', '/contact-us', '/contact.html', '/contact.php',
    '/corp/contact', '/corp/inquiry', '/help', '/inquiry', '/support', '/お問合せ',
    '/layouts/System/VisitorIdentification.aspx', '/magento_version',
    '/typo3/sysext/core/Resources/Public/Images/typo3_orange.svg',
  ]);
  if (probes.has(path) || path.endsWith('/log-in')) {
    const id = document.currentScript.dataset.measurementId;
    if (id) window[`ga-disable-${id}`] = true;
  }
})();
