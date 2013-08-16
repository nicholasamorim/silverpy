import unittest2 as unittest

from lxml import etree


from api import SilverpopApi, pretty_print

class TestSilverpopApi(unittest.TestCase):
    """Test methods that aren't directly dependant
    of having a internet connection with Silverpop.

    To test: unit2 discover
    """
    def setUp(self):
        self.api = SilverpopApi(
            username = 'test',
            password = 'test',
            url = 'testURL',
        )

    def test_envelope(self):
        expected = "<Envelope><Body><Test/></Body></Envelope>"

        envelope = self.api._envelope('Test')

        self.assertIsInstance(envelope, tuple)
        self.assertEqual(len(envelope), 2)
        
        self.assertEqual(envelope[0].tag, 'Envelope')
        self.assertEqual(envelope[1].tag, 'Test')
        
        self.assertEqual(etree.tostring(envelope[0]), expected)

        self.assertIsInstance(envelope[0], etree._Element)

        with self.assertRaises(TypeError):
            self.api._envelope(123)


    def test_is_successful_with_successful_response(self):
        tree = etree.parse('tests/test_response.xml')
        response = etree.tostring(tree)

        info_tuple = self.api._is_successful(response)

        self.assertIsInstance(info_tuple, tuple)
        self.assertEqual(len(info_tuple), 2)

        self.assertIsInstance(info_tuple[0], bool)
        self.assertTrue(info_tuple[0])
        self.assertIsNone(info_tuple[1])

    def test_is_successful_with_error_response(self):
        tree = etree.parse('tests/test_error_response.xml')
        response = etree.tostring(tree)

        info_tuple = self.api._is_successful(response)

        self.assertIsInstance(info_tuple, tuple)
        self.assertEqual(len(info_tuple), 2)

        self.assertIsInstance(info_tuple[0], bool)
        self.assertFalse(info_tuple[0])
        
        self.assertIsInstance(info_tuple[1], tuple)

        error = info_tuple[1]
        expected_error_msg = """Unable to remove the recipient. The list is private and you are not the owner."""

        self.assertEqual(error[0], '140')
        self.assertEqual(error[1], expected_error_msg)

    def test_is_successful_with_malformed_error_response(self):
        tree = etree.parse('tests/test_error_malformed_response.xml')
        response = etree.tostring(tree)

        with self.assertRaises(ValueError):
            self.api._is_successful(response)

    def test_parse_from_string(self):
        tree = etree.parse('tests/test_error_response.xml')
        response = etree.tostring(tree)

        tree_ret = self.api._parse_from_string(response)

        self.assertIsInstance(tree_ret, etree._Element)

    def test_create_child_element(self):
        root, action_node = self.api._envelope('Test')
        dict_columns = {
            'name' : 'Droichead Orga', 
            'email' : 'tastail@dedsert.com'
        }

        self.api._create_child_element(action_node, 'COLUMN', dict_columns)
        children = action_node.getchildren()

        names = list(dict_columns.iterkeys())
        values = list(dict_columns.itervalues())

        for child in children:
            self.assertEqual(child.tag, 'COLUMN')
            for ch in child:
                if ch.tag == 'NAME':
                    self.assertIn(ch.text, names)
                elif ch.tag == 'VALUE':
                    self.assertIn(ch.text, values)

    def test_insert_text_node(self):
        root, action_node = self.api._envelope('Test')

        node = self.api._insert_text_node('subTest', 'insideText', action_node)

        self.assertEqual(node.tag, 'subTest')
        self.assertEqual(node.text, 'insideText')

    def test_get_session_id(self):
        tree = etree.parse('tests/test_login_response.xml')
        response = etree.tostring(tree)

        session = self.api._get_session_id(response)

        self.assertIsNotNone(session)
        self.assertEqual(len(session), 32)
