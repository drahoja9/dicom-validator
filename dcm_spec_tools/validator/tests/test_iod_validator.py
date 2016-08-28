import json
import logging
import os
import unittest

from pydicom.dataset import Dataset

from dcm_spec_tools.tests.test_utils import json_fixture_path
from dcm_spec_tools.validator.iod_validator import IODValidator


class IODValidatorTest(unittest.TestCase):
    """Tests IODValidator. Note: some of the fixture data are not consistent with the DICOM Standard."""
    iod_specs = None

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(json_fixture_path(), 'iod_info.json')) as info_file:
            cls.iod_specs = json.load(info_file)
        with open(os.path.join(json_fixture_path(), 'module_info.json')) as info_file:
            cls.module_specs = json.load(info_file)

    def setUp(self):
        super(IODValidatorTest, self).setUp()
        logging.disable(logging.CRITICAL)

    @staticmethod
    def new_data_set(tags):
        """ Create a DICOM data set with the given attributes """
        tags = tags or {}
        data_set = Dataset()
        for tag_name, value in tags.items():
            setattr(data_set, tag_name, value)
        data_set.file_meta = Dataset()
        data_set.is_implicit_VR = False
        data_set.is_little_endian = True
        return data_set

    def test_empty_dataset(self):
        data_set = self.new_data_set(tags={})
        validator = IODValidator(data_set, self.iod_specs, self.module_specs)
        result = validator.validate()
        self.assertIn('fatal', result)

    def test_invalid_sop_class_id(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.3'
        })
        validator = IODValidator(data_set, self.iod_specs, self.module_specs)
        result = validator.validate()
        self.assertIn('fatal', result)

    def test_missing_tags(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.2',  # CT
            'PatientsName': 'XXX',
            'PatientID': 'ZZZ',
        })
        validator = IODValidator(data_set, self.iod_specs, self.module_specs)
        result = validator.validate()

        self.assertNotIn('fatal', result)
        self.assertIn('missing', result)

        # PatientsName is set
        self.assertNotIn('(0010,0010)', result['missing'])
        # PatientsSex - type 2, missing
        self.assertIn('(0010,0040)', result['missing'])  # PatientsSex
        # Clinical Trial Sponsor Name -> type 1, but module usage U
        self.assertNotIn('(0012,0010)', result['missing'])

    def test_empty_tags(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.2',  # CT
            'PatientsName': '',
            'Modality': None
        })
        validator = IODValidator(data_set, self.iod_specs, self.module_specs)
        result = validator.validate()

        self.assertNotIn('fatal', result)
        self.assertIn('empty', result)
        # Modality - type 1, present but empty
        self.assertIn('(0010,0040)', result['missing'])  # PatientsSex
        # PatientsName - type 2, empty tag is allowed
        self.assertNotIn('(0010,0010)', result['missing'])

    def test_fulfilled_condition_existing_tag(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',  # Enhanced X-Ray Angiographic Image
            'CArmPositionerTabletopRelationship': 'YES',
            'SynchronizationTrigger': 'SET',
            'FrameOfReferenceUID': '1.2.3.4.5.6.7.8',
            'PatientsName': 'XXX',
            'PatientID': 'ZZZ'
        })
        validator = IODValidator(data_set, self.iod_specs, self.module_specs)
        result = validator.validate()

        # Frame Of Reference UID Is and Synchronization Trigger set
        self.assertNotIn('(0020,0052)', result['missing'])
        self.assertNotIn('(0018,106A)', result['missing'])

    def test_fulfilled_condition_missing_tag(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',  # Enhanced X-Ray Angiographic Image
            'CArmPositionerTabletopRelationship': 'YES',
            'PatientsName': 'XXX',
            'PatientID': 'ZZZ'
        })
        validator = IODValidator(data_set, self.iod_specs, self.module_specs)
        result = validator.validate()

        self.assertIn('(0020,0052)', result['missing'])
        self.assertIn('(0018,106A)', result['missing'])

    def test_condition_not_met_no_tag(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',  # Enhanced X-Ray Angiographic Image
            'PatientsName': 'XXX',
            'PatientID': 'ZZZ'
        })
        validator = IODValidator(data_set, self.iod_specs, self.module_specs)
        result = validator.validate()

        self.assertNotIn('(0020,0052)', result['missing'])
        self.assertNotIn('not allowed', result)

    def test_condition_not_met_existing_tag(self):
        data_set = self.new_data_set({
            'SOPClassUID': '1.2.840.10008.5.1.4.1.1.12.1.1',  # Enhanced X-Ray Angiographic Image
            'FrameOfReferenceUID': '1.2.3.4.5.6.7.8',
            'SynchronizationTrigger': 'SET',
            'PatientsName': 'XXX',
            'PatientID': 'ZZZ'
        })
        validator = IODValidator(data_set, self.iod_specs, self.module_specs)
        result = validator.validate()

        # Frame Of Reference is allowed, Synchronization Trigger not
        self.assertNotIn('(0020,0052)', result['missing'])
        self.assertNotIn('(0020,0052)', result['not allowed'])
        self.assertIn('(0018,106A)', result['not allowed'])


if __name__ == '__main__':
    unittest.main()