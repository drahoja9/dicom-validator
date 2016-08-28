import os
import unittest

import pyfakefs.fake_filesystem_unittest

from dcm_spec_tools.spec_reader.part4_reader import Part4Reader
from dcm_spec_tools.spec_reader.spec_reader import SpecReaderLookupError, SpecReaderParseError
from dcm_spec_tools.tests.test_utils import spec_fixture_path


class Part4ReaderTest(pyfakefs.fake_filesystem_unittest.TestCase):
    doc_contents = None

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(spec_fixture_path(), 'part04.xml'), 'rb') as spec_file:
            cls.doc_contents = spec_file.read()

    def setUp(self):
        super(Part4ReaderTest, self).setUp()
        self.setUpPyfakefs()
        spec_path = os.path.join('dicom', 'specs')
        part4_path = os.path.join(spec_path, 'part04.xml')
        self.fs.CreateFile(part4_path, contents=self.doc_contents)
        self.reader = Part4Reader(spec_path)

    def test_read_incomplete_doc_file(self):
        spec_path = '/var/dicom/specs'
        os.makedirs(spec_path)
        self.fs.CreateFile(os.path.join(spec_path, 'part04.xml'),
                           contents='<book xmlns="http://docbook.org/ns/docbook">\n</book>')
        reader = Part4Reader(spec_path)
        self.assertRaises(SpecReaderParseError, reader.iod_chapter, '1.2.840.10008.5.1.4.1.1.2')

    def test_sop_class_lookup(self):
        self.assertRaises(SpecReaderLookupError, self.reader.iod_chapter, '1.1.1.1')
        iod_chapter = self.reader.iod_chapter(sop_class_uid='1.2.840.10008.5.1.4.1.1.2')
        self.assertEqual('A.3', iod_chapter)


if __name__ == '__main__':
    unittest.main()
