# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import pandas
import numpy
from django.test import TestCase

from steelscript.appfwk.apps.alerting.datastructures import (Results,
                                                             DEFAULT_SEVERITY)


class TestResultsClass(TestCase):

    def setUp(self):
        self.severity = DEFAULT_SEVERITY

    def test_simple(self):
        r = Results()
        self.assertEqual(r.get_data(), [])

    def test_single(self):
        r = Results()
        r.add_result(18)
        self.assertEqual(r.get_data(),
                         [{'data': 18, 'severity': self.severity}])

    def test_single_oneliner(self):
        r = Results().add_result(18)
        self.assertEqual(r.get_data(),
                         [{'data': 18, 'severity': self.severity}])

    def test_multiple_single(self):
        r = Results()
        r.add_result(18)
        r.add_result(42)
        self.assertEqual(r.get_data(),
                         [{'data': 18, 'severity': self.severity},
                          {'data': 42, 'severity': self.severity}])

    def test_sequence(self):
        r = Results()
        r.add_results([18, 42])
        self.assertEqual(r.get_data(),
                         [{'data': 18, 'severity': self.severity},
                          {'data': 42, 'severity': self.severity}])

    def test_multiple_sequence(self):
        r = Results()
        r.add_results([18, 42])
        r.add_results([88, 11])
        self.assertEqual(r.get_data(),
                         [{'data': 18, 'severity': self.severity},
                          {'data': 42, 'severity': self.severity},
                          {'data': 88, 'severity': self.severity},
                          {'data': 11, 'severity': self.severity}])

    def test_single_keys(self):
        r = Results()
        r.add_result(18, threshold=15)
        self.assertEqual(
            r.get_data(),
            [{'data': 18, 'severity': self.severity, 'threshold': 15}]
        )

    def test_sequence_single_keys(self):
        r = Results()
        r.add_results([18, 42], threshold=15)
        self.assertEqual(
            r.get_data(),
            [{'data': 18, 'severity': self.severity, 'threshold': 15},
             {'data': 42, 'severity': self.severity, 'threshold': 15}]
        )

    def test_multiple_sequence_single_keys(self):
        r = Results()
        r.add_results([18, 42], threshold=15)
        r.add_results([88, 11], threshold=15)
        self.assertEqual(
            r.get_data(),
            [{'data': 18, 'severity': self.severity, 'threshold': 15},
             {'data': 42, 'severity': self.severity, 'threshold': 15},
             {'data': 88, 'severity': self.severity, 'threshold': 15},
             {'data': 11, 'severity': self.severity, 'threshold': 15}]
        )

    def test_sequence_multiple_keys(self):
        r = Results()
        r.add_results([18, 42], threshold=[15, 40])
        self.assertEqual(
            r.get_data(),
            [{'data': 18, 'severity': self.severity, 'threshold': 15},
             {'data': 42, 'severity': self.severity, 'threshold': 40}]
        )

    def test_multiple_sequence_multiple_keys(self):
        r = Results()
        r.add_results([18, 42], threshold=[15, 40])
        r.add_results([88, 11], threshold=[80, 10])
        self.assertEqual(
            r.get_data(),
            [{'data': 18, 'severity': self.severity, 'threshold': 15},
             {'data': 42, 'severity': self.severity, 'threshold': 40},
             {'data': 88, 'severity': self.severity, 'threshold': 80},
             {'data': 11, 'severity': self.severity, 'threshold': 10}]
        )

    def test_multiple_sequence_invalid_keys(self):
        r = Results()
        r.add_results([18, 42], threshold=15)
        with self.assertRaises(ValueError) as cm:
            r.add_results([88, 11])

        self.assertTrue('Missing data keys' in cm.exception.args[0])

        with self.assertRaises(ValueError) as cm:
            r.add_results([88, 11], foo=12)

        self.assertTrue('Invalid keys' in cm.exception.args[0])

    def test_sequence_multiple_invalid_keys(self):
        r = Results()
        with self.assertRaises(ValueError) as cm:
            r.add_results([88, 11], threshold=[15])
        self.assertTrue('Length' in cm.exception.args[0])

        with self.assertRaises(ValueError) as cm:
            r.add_results([88, 11], threshold=[15, 22, 33])
        self.assertTrue('Length' in cm.exception.args[0])

    def test_dataframe(self):

        # create 8x4 dataframe
        dates = pandas.date_range('1/1/2000', periods=8)
        df = pandas.DataFrame(numpy.random.randn(8, 4), index=dates,
                              columns=['A', 'B', 'C', 'D'])
        data = df.to_dict('records')
        result = [dict(data=x, severity=10, threshold=90) for x in data]

        r = Results()
        r.add_results(df, severity=10, threshold=90)

        self.assertEqual(r.get_data(), result)
