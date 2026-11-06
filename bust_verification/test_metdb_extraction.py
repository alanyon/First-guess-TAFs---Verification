"""Offline regression tests for bulk MetDB extraction failure handling."""
import ast
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
import io
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import numpy as np


class Column(list):
    def __eq__(self, other):
        return [value == other for value in self]


class Reports(list):
    def __getitem__(self, key):
        if isinstance(key, str):
            return Column(row[key] for row in self)
        if isinstance(key, list):
            return Reports(row for row, selected in zip(self, key) if selected)
        return super().__getitem__(key)


class BulkExtractionTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).with_name('verify_busts.py').read_text()
        tree = ast.parse(source)
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name in {'get_day_man_tafs_metars',
                                       'get_metdb_batch',
                                       'metdb_cache_path',
                                       'load_cached_batch',
                                       'save_cached_batch'}]
        self.obs = Mock()
        self.parse_metars = Mock(side_effect=lambda batches, icao: {
            index: batch[0]['value'] for index, batch in enumerate(batches)})
        self.cache_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.cache_dir.cleanup)
        self.namespace = {
            'datetime': datetime, 'timedelta': timedelta,
            'metdb': SimpleNamespace(obs=self.obs),
            'cf': SimpleNamespace(METDB_EMAIL='test@example.com',
                                  REQ_ICAOS=[b'EGAA '],
                                  METDB_CACHE_DIR=self.cache_dir.name),
            'RETRIEVE_TIMEOUT': 300, 'sys': __import__('sys'),
            'get_icao_metars': self.parse_metars, 'np': np, 'os': os,
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]),
                     'verify_busts.py', 'exec'), self.namespace)
        # Mock batches are not numpy arrays, so bypass the cache by default
        self.real_load = self.namespace['load_cached_batch']
        self.real_save = self.namespace['save_cached_batch']
        self.namespace['load_cached_batch'] = Mock(return_value=None)
        self.namespace['save_cached_batch'] = Mock()
        self.tafs = Reports([{'ICAO_ID': b'EGAA ',
                      'TAF_RPT_TXT': b'TAF EGAA 050000Z 0500/0600'}])
        self.batches = [self.tafs] + [Reports([{'value': index}])
                                     for index in range(1, 7)]

    def extract(self):
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            result = self.namespace['get_day_man_tafs_metars'](
                datetime(2023, 8, 5))
        return result, output.getvalue()

    def test_bulk_request_contract(self):
        self.obs.side_effect = self.batches
        (tafs, metars), output = self.extract()
        self.assertEqual(len(tafs['EGAA']), 1)
        self.assertTrue(metars['EGAA'])
        self.assertEqual(self.obs.call_count, 7)
        self.assertEqual([call.args[1] for call in self.obs.call_args_list],
                         ['TAFS'] + ['METARS'] * 3 + ['SPECI'] * 3)
        for call in self.obs.call_args_list:
            self.assertEqual(call.kwargs['keywords'][0], 'PLATFORM EG')
            self.assertEqual(call.kwargs['timeout'], 300)
        expected_dates = ['20230805'] + ['20230805', '20230806', '20230807'] * 2
        for call, date in zip(self.obs.call_args_list, expected_dates):
            self.assertEqual(call.kwargs['keywords'][1:],
                             [f'START TIME {date}/0000Z',
                              f'END TIME {date}/2359Z'])
        self.assertIn('7/7 bulk batches succeeded', output)

    def test_each_failed_batch_keeps_other_results(self):
        for failed_index in range(7):
            with self.subTest(failed_index=failed_index):
                self.obs.reset_mock()
                self.parse_metars.reset_mock()
                responses = list(self.batches)
                responses[failed_index] = OSError('ISTAT = 99')
                self.obs.side_effect = responses
                (tafs, metars), output = self.extract()
                self.assertEqual(self.obs.call_count, 7)
                self.assertEqual(len(tafs['EGAA']), int(failed_index != 0))
                self.assertTrue(metars['EGAA'])
                retained = [batch for call in self.parse_metars.call_args_list
                            for batch in call.args[0]]
                self.assertEqual(len(retained), 6 - int(failed_index != 0))
                self.assertEqual([batch[0]['value'] for batch in retained],
                                 [index for index in range(1, 7)
                                  if index != failed_index])
                self.assertIn('ISTAT = 99', output)
                self.assertIn('202308', output)
                self.assertIn('6/7 bulk batches succeeded', output)

    def test_all_batches_failed_returns_empty_results(self):
        self.obs.side_effect = [OSError('ISTAT = 99')] * 7
        (tafs, metars), output = self.extract()
        self.assertEqual(self.obs.call_count, 7)
        self.assertEqual(tafs, {'EGAA': []})
        self.assertEqual(metars, {'EGAA': []})
        self.assertIn('0/7 bulk batches succeeded', output)

    def test_non_retrieval_errors_are_not_hidden(self):
        self.obs.side_effect = ValueError('bad request')
        with self.assertRaisesRegex(ValueError, 'bad request'):
            self.extract()

    def test_cache_round_trip_skips_metdb(self):
        self.namespace['load_cached_batch'] = self.real_load
        self.namespace['save_cached_batch'] = self.real_save
        batch = np.ma.empty(2, dtype=[('ICAO_ID', 'S5'),
                                      ('TAF_RPT_TXT', 'S500')])
        batch['ICAO_ID'] = [b'EGAA ', b'EGLL ']
        batch['TAF_RPT_TXT'] = [b'TAF EGAA', b'TAF EGLL']
        batch['ICAO_ID'].mask = [False, True]
        self.obs.return_value = batch
        get_batch = self.namespace['get_metdb_batch']

        first = get_batch('TAFS', '20230805/0000', '20230805/2359',
                          'TAF_RPT_TXT')
        second = get_batch('TAFS', '20230805/0000', '20230805/2359',
                           'TAF_RPT_TXT')

        self.assertEqual(self.obs.call_count, 1)
        self.assertTrue(os.path.exists(os.path.join(
            self.cache_dir.name, 'TAFS', '20230805.npz')))
        self.assertIs(first, batch)
        self.assertEqual(second.dtype, batch.dtype)
        self.assertEqual(list(second['TAF_RPT_TXT']),
                         [b'TAF EGAA', b'TAF EGLL'])
        self.assertEqual(list(np.ma.getmaskarray(second['ICAO_ID'])),
                         [False, True])

    def test_failed_and_recent_batches_are_not_cached(self):
        self.namespace['load_cached_batch'] = self.real_load
        self.namespace['save_cached_batch'] = self.real_save
        get_batch = self.namespace['get_metdb_batch']
        self.obs.side_effect = OSError('ISTAT = 99')
        with redirect_stderr(io.StringIO()):
            self.assertIsNone(get_batch('METARS', '20230805/0000',
                                        '20230805/2359', 'MTR_RPT_TXT'))
        self.obs.side_effect = None
        self.obs.return_value = np.ma.empty(0, dtype=[('ICAO_ID', 'S5')])
        today = datetime.now().strftime('%Y%m%d')
        get_batch('METARS', f'{today}/0000', f'{today}/2359', 'MTR_RPT_TXT')
        self.assertFalse(os.path.exists(os.path.join(self.cache_dir.name,
                                                     'METARS')))


if __name__ == '__main__':
    unittest.main()