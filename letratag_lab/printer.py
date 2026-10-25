"""Bluetooth printing operations for the DYMO LetraTag."""

import asyncio

from dymo_bluetooth.bluetooth import (
    PRINT_REPLY_UUID,
    PRINT_REQUEST_UUID,
    create_image,
)
from dymo_bluetooth.printer import Result, command_print

STRETCH_FACTOR = 2
REPLY_TIMEOUT_SECONDS = 30

async def print_one(printer, label_path):
    """Print one label and clean up its notification handler."""
    client = printer._client

    # This check occurs before any print commands are sent.
    if not client.is_connected:
        raise RuntimeError("PRECHECK_DISCONNECTED")

    print_request = client.services.get_characteristic(PRINT_REQUEST_UUID)
    print_reply = client.services.get_characteristic(PRINT_REPLY_UUID)

    loop = asyncio.get_running_loop()
    future = loop.create_future()
    should_discard = False

    def reply_get(_, data):
        """Handle printer replies without completing the future twice."""
        nonlocal should_discard

        if future.done():
            return

        try:
            result = Result.from_bytes(data)
        except (ValueError, IndexError) as exc:
            future.set_exception(exc)
            return

        # Preserve the upstream driver's initial-reply behaviour.
        if not should_discard and result.value in (0, 1):
            should_discard = True
            return

        future.set_result(result)

    try:
        await client.start_notify(print_reply, reply_get)

        canvas = create_image(label_path, dither=True)
        canvas = canvas.stretch(factor=STRETCH_FACTOR)

        # Once this loop begins, a communication failure may leave the
        # physical outcome uncertain. Never automatically resend that job.
        for chunk in command_print(canvas):
            await client.write_gatt_char(print_request, chunk, True)

        return await asyncio.wait_for(
            future,
            timeout=REPLY_TIMEOUT_SECONDS,
        )

    finally:
        if not future.done():
            future.cancel()

        # The connection may already have disappeared during standby.
        if client.is_connected:
            try:
                await client.stop_notify(print_reply)
            except Exception as exc:
                print(f"Warning: notification cleanup failed: {exc}")