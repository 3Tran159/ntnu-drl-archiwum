import unittest
import night_queue as n

class SafetyTests(unittest.TestCase):
    def test_authentication_is_redacted(self):
        for token in ['SYNTHETIC_TEST_KEY','"SYNTHETIC TEST KEY"']:
            self.assertEqual(n.redact('start -podkey '+token+' -np 8'),'start -podkey REDACTED -np 8')
    def test_saved_options_preserve_auth_but_replace_resources(self):
        args=n.parse_saved_command('starccm+.bat -server -power -podkey SYNTHETIC_TEST_KEY -licpath testserver -np 24 -gpgpu 0 -cpubind bandwidth',8)
        self.assertEqual(args,['-power','-podkey','SYNTHETIC_TEST_KEY','-licpath','testserver','-np','8','-cpubind','off'])
    def test_invalid_resource_allocation(self):
        for count in [0,25,-1]:
            with self.assertRaises(ValueError):n.parse_saved_command('starccm+.bat -server',count)
    def test_zero_exit_without_measurement_is_failure(self):
        self.assertEqual(n.classify_outcome(0,{}),'failed')
    def test_unstable_measurement_is_failure(self):
        self.assertEqual(n.classify_outcome(0,{'status':'unstable_or_no_progress'}),'failed_stability')
    def test_completed_measurement_requires_successful_exit(self):
        self.assertEqual(n.classify_outcome(1,{'status':'step_budget_completed'}),'failed')
        self.assertEqual(n.classify_outcome(0,{'status':'step_budget_completed'}),'completed')
    def test_memory_emergency_is_never_overridden(self):
        self.assertEqual(n.classify_outcome(0,{'status':'step_budget_completed'},'memory_emergency_stop'),'memory_emergency_stop')
    def test_unknown_measurement_is_failure(self):
        self.assertEqual(n.classify_outcome(0,{'status':'invented'}),'failed_unrecognized_result')
if __name__=='__main__':unittest.main()
