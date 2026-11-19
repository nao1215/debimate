import unittest
from fetch_sponsors import current_accounts, public_logins, snapshot


def node(login, name=None):
    return {'login': login, 'name': name, 'url': f'https://github.com/{login}',
            'avatarUrl': f'https://avatars.githubusercontent.com/u/1?s=96&v=4&{login}'}


def response(sponsors=(), sponsoring=()):
    return {'data': {'user': {'sponsors': {'nodes': list(sponsors)}, 'sponsoring': {'nodes': list(sponsoring)}}}}


class SponsorSnapshotTests(unittest.TestCase):
    def test_only_current_and_publicly_listed_accounts_are_kept(self):
        data = response([node('alice', 'Alice'), node('hidden')], [node('carol'), node('private-one')])
        accounts = {field: current_accounts(data, field) for field in ('sponsors', 'sponsoring')}
        visible = {
            'sponsors': public_logins('<a data-hovercard-url="/users/alice/hovercard"></a><a data-hovercard-url="/users/past/hovercard"></a>'),
            'sponsoring': public_logins('<a data-hovercard-url="/users/carol/hovercard"></a>'),
        }
        result = snapshot(accounts, visible, '2026-11-19')
        self.assertEqual([a['login'] for a in result['sponsors']], ['alice'])
        self.assertEqual([a['login'] for a in result['sponsoring']], ['carol'])
        self.assertEqual(result['sponsors'][0]['name'], 'Alice')

    def test_missing_name_falls_back_to_login(self):
        self.assertEqual(current_accounts(response([node('bob')]), 'sponsors')[0]['name'], 'bob')

    def test_bad_responses_keep_the_last_snapshot(self):
        bad_url = node('eve')
        bad_url['url'] = 'https://example.com/eve'
        for data in [
            {'errors': [{'message': 'rate limited'}], 'data': {}},
            {'data': {'user': None}},
            response([{'login': '"><script>'}]),
            response([bad_url]),
        ]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                current_accounts(data, 'sponsors')
        with self.assertRaises(ValueError):
            current_accounts({'data': {'user': {'sponsors': {'nodes': []}}}}, 'sponsoring')
        with self.assertRaises(ValueError):
            public_logins('<html>Rate limit</html>')


if __name__ == '__main__':
    unittest.main()
