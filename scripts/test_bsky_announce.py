import json
import unittest
from unittest.mock import patch

from bsky_announce import KINDS, MAX_GRAPHEMES, post_text, posted_urls


class PostTextTests(unittest.TestCase):
    def test_prefix_for_each_kind(self):
        cases = {
            'post': '記事：題名',
            'notes': '技術ノート：題名',
            'ml': '機械学習ノート：題名',
            'weeknotes': 'Weeknotes：題名',
        }
        self.assertEqual(set(cases), set(KINDS))
        for kind, heading in cases.items():
            with self.subTest(kind=kind):
                url = f'https://debimate.jp/{kind}/example/'
                self.assertEqual(post_text(kind, '題名', url), f'{heading}\n{url}')

    def test_long_title_keeps_prefix_and_link(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                url = f'https://debimate.jp/{kind}/example/'
                prefix = post_text(kind, '', url).split('\n')[0]
                text = post_text(kind, '長い題名' * 100, url)
                heading, link = text.split('\n')
                self.assertTrue(heading.startswith(prefix))
                self.assertTrue(heading.endswith('…'))
                self.assertEqual(link, url)
                self.assertEqual(len(text), MAX_GRAPHEMES)

    def test_title_at_limit_is_not_truncated(self):
        url = 'https://debimate.jp/notes/example/'
        title = '題' * (MAX_GRAPHEMES - len('技術ノート：\n' + url))
        self.assertEqual(post_text('notes', title, url), f'技術ノート：{title}\n{url}')

    def test_one_character_left_for_title_becomes_ellipsis(self):
        base = 'https://debimate.jp/ml/'
        url = base + 'a' * (MAX_GRAPHEMES - len('機械学習ノート：\n…') - len(base))
        self.assertEqual(post_text('ml', '長い題名', url), f'機械学習ノート：…\n{url}')

    def test_link_only_when_prefix_and_title_do_not_fit(self):
        base = 'https://debimate.jp/notes/'
        for link_length in (MAX_GRAPHEMES - len('技術ノート：\n'),
                            MAX_GRAPHEMES - len('技術ノート：'), MAX_GRAPHEMES):
            with self.subTest(link_length=link_length):
                url = base + 'a' * (link_length - len(base))
                self.assertEqual(post_text('notes', '題名', url), url)

    def test_unknown_kind_fails_even_for_link_only_fallback(self):
        for url in ('https://debimate.jp/example/', 'https://debimate.jp/' + 'a' * 300):
            with self.subTest(url=url), self.assertRaises(KeyError):
                post_text('unknown', '題名', url)


class PostedUrlsTests(unittest.TestCase):
    def test_old_and_prefixed_posts_have_the_same_duplicate_key(self):
        url = 'https://debimate.jp/notes/example/'
        for text in (f'題名\n{url}', post_text('notes', '題名', url)):
            data = {'feed': [{'post': {'record': {'text': text}}}]}
            with self.subTest(text=text), patch('bsky_announce.fetch', return_value=json.dumps(data).encode()):
                self.assertEqual(posted_urls('example.test'), {url.rstrip('/')})


if __name__ == '__main__':
    unittest.main()
