import unittest
from contextlib import redirect_stdout
from io import StringIO

from dymo_bluetooth.printer import Result
from scripts.print_batch_connected import handle_print_result


class TestHandlePrintResult(unittest.TestCase):
    def check_result(self, result, expected_continue, expected_message):
        """Check the return value and output for one printer result."""
        output = StringIO()

        with redirect_stdout(output):
            should_continue = handle_print_result(result)

        self.assertEqual(should_continue, expected_continue)
        self.assertIn(expected_message, output.getvalue())

    def test_success_continues(self):
        self.check_result(
            Result.SUCCESS,
            True,
            "Print result: Result.SUCCESS",
        )

    def test_success_low_battery_warns_and_continues(self):
        self.check_result(
            Result.SUCCESS_LOW_BATTERY,
            True,
            "Warning: the printer reports low battery.",
        )

    def test_general_failure_stops(self):
        self.check_result(
            Result.FAILED,
            False,
            "general print failure",
        )

    def test_cancelled_print_stops(self):
        self.check_result(
            Result.FAILED_CANCEL,
            False,
            "printing was cancelled",
        )

    def test_low_battery_failure_stops(self):
        self.check_result(
            Result.FAILED_LOW_BATTERY,
            False,
            "low battery and the print failed",
        )

    def test_missing_cassette_result_stops(self):
        self.check_result(
            Result.FAILED_NO_CASETTE,
            False,
            "no label cassette is present",
        )

    def test_unrecognised_result_stops(self):
        self.check_result(
            999,
            False,
            "unrecognised result",
        )

if __name__ == "__main__":
    unittest.main()