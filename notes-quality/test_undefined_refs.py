"""undefined_refs.py の規則の回帰テスト。python3 -m unittest notes-quality/test_undefined_refs.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import undefined_refs as u  # noqa: E402

FM = '---\ntitle: "T - t"\n---\n\n'
MT = '/notes/software-testing/metamorphic-testing/'


def rules(body):
    return [(r, level) for _, r, level, _, _ in u.scan('', FM + body)]


class BareNumbers(unittest.TestCase):
    def test_unitless_nimo_list(self):
        self.assertIn(('bare_numbers', 'ng'), rules('どの段階で数えるかによって、同じ絵文字が 18 にも 8 にも 5 にも 1 にもなります。\n'))

    def test_with_unit(self):
        self.assertEqual(rules('同じ絵文字が 18 バイトにも 8 個にもなります。\n'), [])

    def test_quantity_subject(self):
        self.assertEqual(rules('数え方によって、長さは 18 にも 8 にもなります。\n'), [])

    def test_labeled(self):
        self.assertEqual(rules('どの状態からも block 3 にも 4 にも進めます。\n'), [])

    def test_unit_earlier_in_sentence(self):
        self.assertEqual(rules('絵文字は 2 セルで、○ は環境によって 1 にも 2 にもなります。\n'), [])

    def test_known_values(self):
        self.assertEqual(rules('値は 0 と 1 のどちらかです。\n\n配送順しだいで 0 にも 1 にも決まります。\n'), [])

    def test_code_and_table_skipped(self):
        self.assertEqual(rules('```\n同じ絵文字が 18 にも 8 にもなる\n```\n| 18 にも 8 にも |\n'), [])


class BorrowedTerm(unittest.TestCase):
    def test_target_term_not_defined_here(self):
        self.assertIn(('borrowed_term', 'ng'), rules(f'改行コードで結果が変わらないことは、[Metamorphic Testing]({MT}) の関係として書けます。\n'))

    def test_defined_here(self):
        body = 'メタモルフィックテストでは、入力の変え方と出力の変わり方の組を「関係」と呼びます。\n\n'
        body += f'改行コードで結果が変わらないことは、[Metamorphic Testing]({MT}) の関係として書けます。\n'
        self.assertEqual(rules(body), [])

    def test_inside_parentheses(self):
        self.assertEqual(rules(f'root（覆らないブロック。[Metamorphic Testing]({MT}) の関係として書けます）になります。\n'), [])

    def test_external_link(self):
        self.assertEqual(rules('[Metamorphic Testing](https://example.com/) の関係として書けます。\n'), [])


class AcronymBeforeDefinition(unittest.TestCase):
    def test_used_before_defined(self):
        body = 'PBFT の論文は障害を扱います。\n\n2\n\n3\n\nPBFT（Practical Byzantine Fault Tolerance）は合意の方式です。\n'
        self.assertIn(('acronym_before_def', 'notice'), rules(body))

    def test_forward_reference(self):
        body = '後述の PBFT は障害を扱います。\n\n2\n\n3\n\nPBFT（Practical Byzantine Fault Tolerance）は合意の方式です。\n'
        self.assertEqual(rules(body), [])


class SmallEdit(unittest.TestCase):
    """小さな修正では、足した行に新しく出た指摘だけを返す。"""
    OLD = FM + '同じ絵文字が 18 にも 8 にもなります。\n\n説明です。\n'

    def test_untouched_violation_ignored(self):
        new = self.OLD + '\n足した文です。\n'
        self.assertEqual(u.findings_in_added(self.OLD, new, ['足した文です。']), [])

    def test_added_violation_reported(self):
        line = '別の絵文字は 25 にも 7 にもなります。'
        new = self.OLD + '\n' + line + '\n'
        self.assertEqual([f[1] for f in u.findings_in_added(self.OLD, new, [line])], ['bare_numbers'])


if __name__ == '__main__':
    unittest.main()
