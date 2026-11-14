import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../assets/js/analytics-404-filter.js', import.meta.url), 'utf8');
function disabled(path) {
  const window = { location: { pathname: path } };
  vm.runInNewContext(source, { window, document: { currentScript: { dataset: { measurementId: 'G-TEST' } } } });
  return window['ga-disable-G-TEST'] === true;
}

test('exclude observed missing contact and CMS probes', () => {
  for (const path of ['/contact.php', '/corp/inquiry/', '/%E3%81%8A%E5%95%8F%E5%90%88%E3%81%9B',
    '/magento_version', '/layouts/System/VisitorIdentification.aspx',
    '/typo3/sysext/core/Resources/Public/Images/typo3_orange.svg', '/tags/login/log-in']) {
    assert.equal(disabled(path), true, path);
  }
});

test('retain genuine broken links and malformed URLs for diagnosis', () => {
  for (const path of ['/post/ja/missing-article/', '/tags/linux/page/2/',
    '/post/ja/magento_version/', '/contact-details/', '/post/old/_wp_link_placeholder', '/%ZZ']) {
    assert.equal(disabled(path), false, path);
  }
});

test('production 404 opts out before gtag, while ordinary pages remain tracked', () => {
  const error = readFileSync('public/404.html', 'utf8');
  const home = readFileSync('public/index.html', 'utf8');
  const match = error.match(/<script\b[^>]*data-measurement-id=["']?([^\s"'>]+)["']?[^>]*>([\s\S]*?)<\/script>/);
  assert.ok(match, '404 must contain the inline filter');
  assert.ok(error.indexOf(match[0]) < error.indexOf('googletagmanager.com/gtag/js?'));
  const window = { location: { pathname: '/contact.php' } };
  vm.runInNewContext(match[2], { window, document: { currentScript: { dataset: { measurementId: match[1] } } } });
  assert.equal(window[`ga-disable-${match[1]}`], true);
  assert.ok(!home.includes('data-measurement-id'));
  assert.ok(home.includes('googletagmanager.com/gtag/js?'));
});
