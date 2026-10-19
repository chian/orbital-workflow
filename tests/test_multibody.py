"""Independent physical invariants, absolute-time replay, and scenario scope."""
from dataclasses import asdict, replace
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2]/'OpenChia')
from orbital_workflow.artifacts import Artifacts
from orbital_workflow.credit import CreditController,project_observation
from orbital_workflow.gravity import GravitySystem
from orbital_workflow.persistence import PersistenceSettings
from orbital_workflow.runtime import Kind
from orbital_workflow.scientific import ScientificBindings,load_settings
from orbital_workflow.simulation import ModelTerms,SimulationRequest,generate_forcing,integrate
from orbital_workflow.tools import ToolDispatcher

ROOT=Path(__file__).resolve().parents[1]
BINARY=GravitySystem(kind='circular_binary',masses=(.75,.25),separation=.8,collision_radii=(.05,.035))

class MultipleAttractors(unittest.TestCase):
    def test_binary_is_mutual_newtonian_motion_with_fixed_barycenter_and_separation(self):
        for time in (0,1.234,10.7):
            bodies=BINARY.sources(time)
            positions=np.array([b['position'] for b in bodies])
            velocities=np.array([b['velocity'] for b in bodies])
            np.testing.assert_allclose(np.array(BINARY.masses)@positions,0,atol=1e-15)
            np.testing.assert_allclose(np.array(BINARY.masses)@velocities,0,atol=1e-15)
            self.assertAlmostEqual(np.linalg.norm(positions[1]-positions[0]),BINARY.separation)
            for i in (0,1):
                j=1-i;displacement=positions[j]-positions[i]
                acceleration=BINARY.masses[j]*displacement/np.linalg.norm(displacement)**3
                np.testing.assert_allclose(acceleration,-BINARY.angular_speed**2*positions[i],rtol=1e-14,atol=1e-14)
        period=2*math.pi/BINARY.angular_speed
        np.testing.assert_allclose(BINARY.sources(period)[0]['position'],BINARY.sources(0)[0]['position'],atol=1e-15)

    def test_superposition_source_omission_and_monopole_are_explicit(self):
        time,x,y=1.234,1.1,-.3
        expected=np.zeros(2)
        for body in BINARY.sources(time):
            displacement=np.array([x,y])-body['position']
            contribution=-body['mass']*displacement/np.linalg.norm(displacement)**3
            np.testing.assert_allclose(BINARY.acceleration(time,x,y,(body['id'],)),contribution,rtol=1e-14)
            expected+=contribution
        np.testing.assert_allclose(BINARY.acceleration(time,x,y),expected,rtol=1e-14)
        np.testing.assert_allclose(BINARY.acceleration(time,x,y,mode='monopole'),-np.array([x,y])/math.hypot(x,y)**3)
        np.testing.assert_array_equal(BINARY.acceleration(time,x,y,()),[0,0])
        with self.assertRaises(ValueError):GravitySystem(kind='circular_binary',masses=(1,-1),separation=1)
        with self.assertRaises(ValueError):SimulationRequest('unused',gravity=BINARY,active_bodies=('unknown',))

    def test_binary_jacobi_invariant_and_exact_absolute_time_continuation(self):
        with tempfile.TemporaryDirectory() as temporary:
            store=Artifacts(Path(temporary))
            forcing=generate_forcing(store,1,6)
            request=SimulationRequest(forcing,initial_state=(1,0,0,1.4),end=6,gravity=BINARY,
                radial_limits=(.05,4),scenario_id='scenario_02',
                terms=ModelTerms(modulation=False,rotating=False,forcing=False),
                max_step=.02,rtol=1e-10,atol=1e-12)
            trajectory=integrate(request,store)
            constants=[]
            for time,state in zip(trajectory.times,trajectory.states):
                potential=sum(b['mass']/np.linalg.norm(state[:2]-b['position']) for b in BINARY.sources(time))
                angular_momentum=state[0]*state[3]-state[1]*state[2]
                constants.append(2*potential+2*BINARY.angular_speed*angular_momentum-float(state[2:]@state[2:]))
            np.testing.assert_allclose(constants,constants[0],atol=2e-8,rtol=0)
            prefix=integrate(replace(request,end=2),store)
            self.assertEqual(prefix.outcome,'horizon_reached')
            suffix=integrate(replace(request,start=2,initial_state=tuple(prefix.states[-1])),store)
            np.testing.assert_array_equal(trajectory.states[-1],suffix.states[-1])

    def test_moving_surface_collision_is_a_recorded_physical_endpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            store=Artifacts(Path(temporary));forcing=generate_forcing(store,1,1)
            body=BINARY.sources(0)[1]
            request=SimulationRequest(forcing,gravity=BINARY,scenario_id='scenario_02',end=1,
                radial_limits=(.05,4),initial_state=(body['position'][0]+.04,0,-.1,body['velocity'][1]),
                terms=ModelTerms(modulation=False,rotating=False,forcing=False),max_step=.001)
            trajectory=integrate(request,store)
            self.assertEqual(trajectory.outcome,'collision_body_2')
            final_body=BINARY.sources(trajectory.times[-1])[1]
            self.assertAlmostEqual(np.linalg.norm(trajectory.states[-1,:2]-final_body['position']),.035,places=10)

    def test_binary_barycenter_is_not_an_inner_collision_obstacle(self):
        with tempfile.TemporaryDirectory() as temporary:
            store=Artifacts(Path(temporary));forcing=generate_forcing(store,1,1)
            equal=GravitySystem(kind='circular_binary',masses=(.5,.5),separation=1,collision_radii=(.05,.05))
            request=SimulationRequest(forcing,gravity=equal,scenario_id='scenario_02',end=1,
                radial_limits=(0,4),initial_state=(0,0,0,0),
                terms=ModelTerms(modulation=False,rotating=False,forcing=False))
            trajectory=integrate(request,store)
            self.assertEqual(trajectory.outcome,'horizon_reached')
            np.testing.assert_array_equal(trajectory.states,np.zeros_like(trajectory.states))

    def test_scenario_binding_fixes_masses_and_reduced_evidence_uses_parent_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            settings=load_settings(ROOT/'scenarios/scenario_02/study.toml')
            store=Artifacts(Path(temporary)/'objects');tools=ToolDispatcher(store)
            binding=ScientificBindings(settings,None,tools)
            args=binding.simulation_arguments({'vx':0,'vy':1.4,'experiment':{
                'interval':[0,20],
                'terms':{'modulation':False,'rotating':False,'forcing':False},
                'gravity_mode':'monopole'}},parts=True)
            self.assertEqual(args['gravity']['masses'],(.75,.25))
            self.assertEqual(args['radial_limits'],(0,4))
            with self.assertRaises(ValueError):binding.simulation_arguments({'gravity':{}})
            observation=tools.execute('sim.run',args)
            credit=CreditController(settings,Kind.ROOT,binding.root_score)
            first=credit.observe('monopole parts evidence',project_observation(observation,store),is_root=True)
            self.assertEqual(first.record['credit'],0)
            self.assertEqual(len(credit.assignment.evidence),1)
            self.assertIn('score',observation.findings)
            duplicate=credit.observe('same evidence',project_observation(observation,store),is_root=True)
            self.assertEqual(duplicate.record['marginal_credit'],0)
            reference=tools.execute('math.numeric',binding.simulator.resolve_numeric({'operation':'binary_reference'}))
            self.assertAlmostEqual(reference.findings['binary_period'],2*math.pi*math.sqrt(.8**3))
            self.assertEqual(len(reference.findings['gravity_contributions']),2)

if __name__=='__main__':unittest.main()
