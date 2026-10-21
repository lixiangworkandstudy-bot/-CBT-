import unittest
from app.engine import Engine, InputError, ACTIVITIES
from robot.bridge import Lease, parser, validate

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.t=100.0;self.e=Engine(lambda:self.t)
        self.s=self.e.create({'adult_present':True,'consent':True})['id']

    def action(self, **data):return self.e.event(self.s,data)

    def answer(self, value=None, skip=False):
        s=self.e.get(self.s)
        return self.action(type='skip' if skip else 'answer',answer=value,revision=s['revision'])

    def test_consent_required(self):
        for d in [{},{'adult_present':True},{'consent':True},{'consent':'true','adult_present':True}]:
            with self.assertRaises(InputError):self.e.create(d)

    def test_all_activity_flows(self):
        for key,a in ACTIVITIES.items():
            self.action(type='start',activity=key)
            for step in a['steps']:self.answer(step['choices'][0])
            self.assertEqual(self.e.get(self.s)['state'],'completed')
        self.assertEqual(self.e.report(self.s)['completed_activities'],4)

    def test_skip_is_not_failure(self):
        self.action(type='start',activity='help')
        for _ in range(3):self.answer(skip=True)
        self.assertEqual(self.e.get(self.s)['stars'],1)

    def test_stale_and_unlisted_input_rejected(self):
        self.action(type='start',activity='feelings')
        with self.assertRaises(InputError):self.action(type='answer',revision=0,answer='wrong')
        with self.assertRaises(InputError):self.answer('wrong')
        self.assertEqual(self.e.get(self.s)['step'],0)

    def test_pause_cancel_and_explicit_resume(self):
        self.action(type='start',activity='feelings');self.answer('晴天 · 舒服');self.answer('安静待一会');self.answer('我想试试')
        self.assertEqual(self.e.robot_poll(self.s,'turtlesim')['cue'],'celebrate')
        self.action(type='stop')
        self.assertEqual(self.e.robot_poll(self.s,'turtlesim')['angular_z'],0)
        with self.assertRaises(InputError):self.action(type='start',activity='help')
        with self.assertRaises(InputError):self.action(type='resume')
        s=self.action(type='resume',adult_confirm=True)
        self.assertEqual(s['state'],'ready');self.assertIsNone(self.e.get(self.s)['command'])

    def test_discomfort_stops(self):
        self.action(type='start',activity='breathing');self.answer('只看云朵');self.answer('我准备好了');self.answer('有些不舒服')
        self.assertEqual(self.e.get(self.s)['state'],'stopped')
        self.assertEqual(self.e.get(self.s)['stars'],0)

    def test_cue_expires_and_device_status_expires(self):
        self.action(type='start',activity='turns')
        for _ in range(3):self.answer(skip=True)
        self.assertNotEqual(self.e.robot_poll(self.s,'dry-run')['angular_z'],0)
        self.t+=2
        self.assertFalse(self.e.view(self.e.get(self.s))['robot']['online'])
        self.assertEqual(self.e.robot_poll(self.s,'dry-run')['angular_z'],0)

class LeaseTests(unittest.TestCase):
    def setUp(self):self.t=1.;self.l=Lease(lambda:self.t)
    def message(self,**kw):return {'cue':'celebrate','state':'completed','lease_ms':150,'angular_z':.12,'linear_x':0,**kw}
    def test_ttl_independent_of_network(self):
        self.l.update(self.message());self.assertEqual(self.l.velocity(),(0.,.12));self.t+=.151
        self.assertEqual(self.l.velocity(),(0.,0.))
    def test_bad_commands_and_errors_fail_closed(self):
        for m in [{}, self.message(angular_z=4),self.message(lease_ms=500),self.message(linear_x=.1),self.message(angular_z=float('nan')),self.message(state='stopped'),self.message(lease_ms=float('inf'))]:
            self.l.update(self.message());self.l.update(m);self.assertEqual(self.l.velocity(),(0.,0.))
    def test_vbot_requires_terminal_gate(self):
        a=parser().parse_args(['--session','abc','--mode','vbot','--execute'])
        with self.assertRaises(ValueError):validate(a)
    def test_duration_and_url_bounds(self):
        for args in [['--duration','nan'],['--duration','121'],['--base-url','http://example.com']]:
            a=parser().parse_args(['--session','abc',*args])
            with self.assertRaises(ValueError):validate(a)

if __name__=='__main__':unittest.main()
