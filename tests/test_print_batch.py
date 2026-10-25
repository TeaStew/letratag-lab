import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from dymo_bluetooth.printer import Result

from letratag_lab.config import DEFAULT_PRINTER_ADDRESS
from scripts.print_batch_connected import print_batch


class TestPrintBatch(unittest.IsolatedAsyncioTestCase):
    async def test_printer_failure_stops_queue_and_disconnects(self):
        # Simulate a connected printer with an asynchronous disconnect method.
        printer = SimpleNamespace(
            _client=SimpleNamespace(is_connected=True),
            disconnect=AsyncMock(),
        )

        labels = [
            Path("T1.png"),
            Path("T2.png"),
            Path("T3.png"),
        ]

        with (
            patch(
                "scripts.print_batch_connected.connect_with_retries",
                new_callable=AsyncMock,
                return_value=printer,
            ) as connect_mock,
            patch(
                "scripts.print_batch_connected.print_one",
                new_callable=AsyncMock,
                side_effect=[
                    Result.SUCCESS,
                    Result.FAILED,
                    Result.SUCCESS,
                ],
            ) as print_mock,
            patch("builtins.input", side_effect=["", "", ""]),
            redirect_stdout(StringIO()) as output,
        ):
            await print_batch(labels, timeout=5)

        # Only T1 and T2 should be attempted; T3 must not be sent.
        self.assertEqual(print_mock.await_count, 2)

        # The queue should have connected once at the start.
        connect_mock.assert_awaited_once_with(None, DEFAULT_PRINTER_ADDRESS, 5)

        # Even when printing fails, the connection must be closed.
        printer.disconnect.assert_awaited_once()

        # Confirm that the failure was reported.
        self.assertIn(
            "general print failure",
            output.getvalue(),
        )

        # T3 should never appear in the queue output.
        self.assertNotIn("Label 3 of 3", output.getvalue())
 
    async def test_confirmed_unprinted_label_is_retried(self):
        printer = SimpleNamespace(
            _client=SimpleNamespace(is_connected=True),
            disconnect=AsyncMock(),
        )

        labels = [
            Path("T1.png"),
            Path("T2.png"),
            Path("T3.png"),
        ]

        with (
            patch(
                "scripts.print_batch_connected.connect_with_retries",
                new_callable=AsyncMock,
                side_effect=[printer, printer],
            ) as connect_mock,
            patch(
                "scripts.print_batch_connected.print_one",
                new_callable=AsyncMock,
                side_effect=[
                    Result.SUCCESS,
                    OSError("Simulated Bluetooth failure"),
                    Result.SUCCESS,
                    Result.SUCCESS,
                ],
            ) as print_mock,
            patch(
                "builtins.input",
                side_effect=["", "", "n", "", ""],
            ),
            redirect_stdout(StringIO()) as output,
        ):
            await print_batch(labels, timeout=5)

        # T1 succeeds, T2 fails and is retried, then T3 succeeds.
        self.assertEqual(print_mock.await_count, 4)

        # Initial connection plus reconnection before retrying T2.
        self.assertEqual(connect_mock.await_count, 2)

        # The retry and T3 should both have succeeded.
        self.assertIn("Retrying the unprinted label once", output.getvalue())
        self.assertIn("Label 3 of 3", output.getvalue())

        # The connection is closed when the queue finishes.
        printer.disconnect.assert_awaited_once()
 
    async def test_uncertain_outcome_stops_without_retry(self):
        printer = SimpleNamespace(
            _client=SimpleNamespace(is_connected=True),
            disconnect=AsyncMock(),
        )

        labels = [
            Path("T1.png"),
            Path("T2.png"),
            Path("T3.png"),
        ]

        with (
            patch(
                "scripts.print_batch_connected.connect_with_retries",
                new_callable=AsyncMock,
                return_value=printer,
            ) as connect_mock,
            patch(
                "scripts.print_batch_connected.print_one",
                new_callable=AsyncMock,
                side_effect=[
                    Result.SUCCESS,
                    OSError("Simulated Bluetooth failure"),
                ],
            ) as print_mock,
            patch(
                "builtins.input",
                side_effect=["", "", "u"],
            ),
            redirect_stdout(StringIO()) as output,
        ):
            await print_batch(labels, timeout=5)

        self.assertEqual(print_mock.await_count, 2)
        connect_mock.assert_awaited_once_with(None, DEFAULT_PRINTER_ADDRESS, 5)
        self.assertIn("outcome is uncertain", output.getvalue())
        self.assertNotIn("Label 3 of 3", output.getvalue())
        printer.disconnect.assert_awaited_once()

    async def test_failed_retry_stops_queue_and_disconnects(self):
        printer = SimpleNamespace(
            _client=SimpleNamespace(is_connected=True),
            disconnect=AsyncMock(),
        )

        labels = [
            Path("T1.png"),
            Path("T2.png"),
            Path("T3.png"),
        ]

        with (
            patch(
                "scripts.print_batch_connected.connect_with_retries",
                new_callable=AsyncMock,
                side_effect=[printer, printer],
            ) as connect_mock,
            patch(
                "scripts.print_batch_connected.print_one",
                new_callable=AsyncMock,
                side_effect=[
                    Result.SUCCESS,
                    OSError("Simulated first Bluetooth failure"),
                    OSError("Simulated retry failure"),
                ],
            ) as print_mock,
            patch(
                "builtins.input",
                side_effect=["", "", "n"],
            ),
            redirect_stdout(StringIO()) as output,
        ):
            await print_batch(labels, timeout=5)

        self.assertEqual(print_mock.await_count, 3)
        self.assertEqual(connect_mock.await_count, 2)
        self.assertIn("Retry failed", output.getvalue())
        self.assertNotIn("Label 3 of 3", output.getvalue())
        printer.disconnect.assert_awaited_once()

if __name__ == "__main__":
    unittest.main()