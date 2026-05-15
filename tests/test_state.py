import unittest

from agent_voice.state import AppState, StateMachine


class StateMachineTest(unittest.TestCase):
    def test_normal_command_flow_returns_to_idle(self):
        machine = StateMachine()

        observed = [
            machine.transition("started"),
            machine.transition("wake_detected"),
            machine.transition("recording_complete"),
            machine.transition("parsed"),
            machine.transition("accepted"),
            machine.transition("settled"),
        ]

        self.assertEqual(
            observed,
            [
                AppState.IDLE,
                AppState.LISTENING,
                AppState.RECOGNIZING,
                AppState.SENDING,
                AppState.DONE,
                AppState.IDLE,
            ],
        )

    def test_unknown_command_goes_to_no_match_then_idle(self):
        machine = StateMachine()
        machine.transition("started")
        machine.transition("wake_detected")
        machine.transition("recording_complete")

        self.assertEqual(machine.transition("no_match"), AppState.NO_MATCH)
        self.assertEqual(machine.transition("settled"), AppState.IDLE)

    def test_mute_and_resume(self):
        machine = StateMachine(initial_state=AppState.IDLE)

        self.assertEqual(machine.transition("mute"), AppState.MUTED)
        self.assertEqual(machine.transition("resume"), AppState.IDLE)

    def test_rejects_invalid_transition(self):
        machine = StateMachine(initial_state=AppState.IDLE)

        with self.assertRaises(ValueError):
            machine.transition("accepted")


if __name__ == "__main__":
    unittest.main()
