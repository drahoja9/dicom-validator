import logging
import os

import pyfakefs.fake_filesystem_unittest
import time

from spec_reader.edition_reader import EditionReader


class MemoryEditionReader(EditionReader):
    """Mock class that gets the file contents in constructor instead of downloading them.
    We test this class to avoid real download connections during the test.
    """

    def __init__(self, path, contents):
        super(MemoryEditionReader, self).__init__(url='', path=path)
        self.html_contents = contents

    def retrieve(self, html_path):
        with open(html_path, 'w') as html_file:
            html_file.write(self.html_contents)


class EditionReaderTest(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        super(EditionReaderTest, self).setUp()
        self.setUpPyfakefs()
        self.base_path = os.path.join('user', 'dcm-spec-tools')
        self.fs.CreateDirectory(self.base_path)
        logging.disable(logging.CRITICAL)

    def test_empty_html(self):
        reader = MemoryEditionReader(self.base_path, '')
        self.assertIsNone(reader.get_editions())
        self.assertFalse(os.path.exists(os.path.join(self.base_path, reader.json_filename)))

    def test_no_html(self):
        reader = MemoryEditionReader(self.base_path, 'Not html')
        self.assertIsNone(reader.get_editions())
        self.assertFalse(os.path.exists(os.path.join(self.base_path, reader.json_filename)))

    def test_no_editions(self):
        reader = MemoryEditionReader(self.base_path, '<html><A HREF="/medical/dicom/2014a/">test</A><html>')
        self.assertIsNone(reader.get_editions())
        self.assertFalse(os.path.exists(os.path.join(self.base_path, reader.json_filename)))

    def test_valid_editions(self):
        reader = MemoryEditionReader(self.base_path, '<html><A HREF="/bla/">2014a</A>'
                                                     '2014b'
                                                     '<a ref="foo">2015</a>'
                                                     '<a ref="foo">2017e</a>')
        self.assertEqual(['2014a', '2017e'], reader.get_editions())
        self.assertTrue(os.path.exists(os.path.join(self.base_path, reader.json_filename)))

    def test_keep_old_version(self):
        json_path = os.path.join(self.base_path, EditionReader.json_filename)
        self.fs.CreateFile(json_path, contents='["2014a", "2014c"]')
        file_time = time.time() - 29 * 24 * 60 * 60.0
        os.utime(json_path, (file_time, file_time))
        reader = MemoryEditionReader(self.base_path, '<html><A HREF="/bla/">2018a</A>')
        self.assertEqual(['2014a', '2014c'], reader.get_editions())

    def test_replace_old_version(self):
        json_path = os.path.join(self.base_path, EditionReader.json_filename)
        self.fs.CreateFile(json_path, contents='["2014a", "2014c"]')
        file_time = time.time() - 31 * 24 * 60 * 60.0
        os.utime(json_path, (file_time, file_time))
        reader = MemoryEditionReader(self.base_path, '<html><A HREF="/bla/">2018a</A>')
        self.assertEqual(['2018a'], reader.get_editions())

    def test_get_existing_revision(self):
        reader = MemoryEditionReader(self.base_path, '<html><A HREF="/bla/">2014a</A>'
                                                     '<a ref="foo">2014e</a>')
        self.assertEqual('2014a', reader.get_edition('2014a'))

    def test_non_existing_revision(self):
        reader = MemoryEditionReader(self.base_path, '<html><A HREF="/bla/">2014a</A>'
                                                     '<a ref="foo">2014e</a>')
        self.assertIsNone(reader.get_edition('2015a'))

    def test_last_revision_in_year(self):
        reader = MemoryEditionReader(self.base_path, '<html><A HREF="/bla/">2014a</A>'
                                                     '<a ref="foo">2014c</a>'
                                                     '<a ref="foo">2015e</a>')
        self.assertEqual('2014c', reader.get_edition('2014'))

    def test_current_revision(self):
        reader = MemoryEditionReader(self.base_path, '<html><A HREF="/bla/">2014a</A>'
                                                     '<a ref="foo">2014c</a>'
                                                     '<a ref="foo">2015e</a>')
        self.assertEqual('2015e', reader.get_edition('current'))
