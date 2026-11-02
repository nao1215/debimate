import unittest
from fetch_oss_stars import query_for, updated_catalog


class StarSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {'asOf': '2026-01-01', 'projects': [
            {'name': 'gup', 'stars': 1, 'article': '/post/example'},
            {'name': 'filesql', 'stars': 2},
        ]}

    def test_update_keeps_editorial_fields_and_original(self):
        result = updated_catalog(self.catalog, {'data': {'r0': {'stargazerCount': 10}, 'r1': {'stargazerCount': 0}}}, '2026-11-03')
        self.assertEqual([p['stars'] for p in result['projects']], [10, 0])
        self.assertEqual(result['projects'][0]['article'], '/post/example')
        self.assertEqual(result['asOf'], '2026-11-03')
        self.assertEqual(self.catalog['projects'][0]['stars'], 1)

    def test_incomplete_or_invalid_response_does_not_change_snapshot(self):
        for response in [
            {'errors': [{'message': 'rate limited'}], 'data': {}},
            {'data': {'r0': {'stargazerCount': 10}, 'r1': None}},
            {'data': {'r0': {'stargazerCount': 10}, 'r1': {'stargazerCount': -1}}},
            {'data': {'r0': {'stargazerCount': 10}, 'r1': {'stargazerCount': True}}},
        ]:
            with self.subTest(response=response), self.assertRaises(ValueError):
                updated_catalog(self.catalog, response, '2026-11-03')
            self.assertEqual(self.catalog['projects'][0]['stars'], 1)

    def test_query_names_and_duplicate_validation(self):
        self.assertIn('r1: repository(owner: "nao1215", name: "filesql")', query_for(self.catalog))
        self.catalog['projects'][1]['name'] = 'gup'
        with self.assertRaises(ValueError):
            query_for(self.catalog)
