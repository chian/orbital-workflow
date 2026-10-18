"""Presentation history reads compact ownership; saved science stays unchanged."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / 'OpenChia')
from orbital_workflow.smoke import run_probe
from orbital_workflow.visualization import load_catalog, make_viewer

class PresentationHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory()
        cls.directory=Path(cls.temporary.name)/'fresh'
        run_probe(cls.directory,Path(__file__).resolve().parents[1]/'study.toml')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_tour_retains_repeated_acquisitions_and_both_comparison_sides_without_array_reads(self):
        with patch('numpy.load',side_effect=AssertionError('catalog loaded numerical arrays')):
            data=load_catalog(self.directory)
        self.assertEqual(data['default_playback_mode'],'progress')
        self.assertEqual(len(data['simulations']),3)
        self.assertEqual(len(data['timeline']),5)
        self.assertEqual(len({item['unit_id'] for item in data['timeline']}),4)
        self.assertEqual(len({item['key'] for item in data['timeline']}),5)
        self.assertEqual(len({item['observation_id'] for item in data['timeline']}),3)
        self.assertEqual(data['timeline'][-1]['position'],2)
        self.assertEqual(data['timeline'][-1]['observation_count'],2)
        self.assertEqual(data['warnings'],[])
        self.assertTrue(all(row['states'] is None for row in data['simulations']))

    def test_offline_default_contains_entire_history_as_packets_for_selection(self):
        exported=make_viewer(self.directory)
        html=Path(exported['viewer']).read_text()
        encoded=html.split('<script type="application/json" id="playback-data">',1)[1].split('</script>',1)[0]
        data=json.loads(encoded)
        self.assertEqual(exported['observations'],3)
        self.assertEqual(len(data['timeline']),5)
        self.assertEqual(len(data['embedded_observations']),3)
        self.assertTrue(all(row['states'] is None for row in data['simulations']))
        for row in data['simulations']:
            saved=json.loads(data['embedded_observations'][row['id']])
            self.assertEqual(saved['states'][-1],row['summary']['terminal_state'])
            forcing=json.loads(data['embedded_forcing'][row['forcing_id']])
            self.assertGreaterEqual(forcing['times'][-1],row['request']['end'])
        subset=make_viewer(self.directory,self.directory/'subset.html',observation_ids=[data['simulations'][0]['id']])
        self.assertEqual(subset['observations'],1)
        self.assertEqual(len(data['simulations']),3)

if __name__=='__main__':unittest.main()
