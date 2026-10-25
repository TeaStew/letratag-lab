"""Helpers for interpreting and reporting printer results."""

from dymo_bluetooth.printer import Result

def describe_print_error(exc):
    """Return a user-friendly summary and technical detail."""
    error_type = type(exc).__name__
    technical_detail = f"{error_type}: {exc}"

    if isinstance(exc, OSError) and "WinError -2147023673" in str(exc):
        summary = (
            "Windows cancelled the Bluetooth print operation. "
            "The printer may have switched itself off or lost its connection."
        )
    else:
        summary = (
            "The print operation failed. "
            "The cause could be a Bluetooth, printer, or other error."
        )

    return summary, technical_detail

def handle_print_result(result):
    """Report the printer result and return True only for success."""
    if result == Result.SUCCESS:
        print(f"Print result: {result}")
        return True

    if result == Result.SUCCESS_LOW_BATTERY:
        print(f"Print result: {result}")
        print("Warning: the printer reports low battery.")
        return True

    messages = {
        Result.FAILED: "The printer reported a general print failure.",
        Result.FAILED_CANCEL: "The printer reported that printing was cancelled.",
        Result.FAILED_LOW_BATTERY: (
            "The printer reported low battery and the print failed."
        ),
        Result.FAILED_NO_CASETTE: (
            "The printer reports that no label cassette is present."
        ),
    }

    print(f"Print result: {result}")
    print(messages.get(result, "The printer returned an unrecognised result."))
    print("Queue stopped. Check the physical label before continuing.")
    return False