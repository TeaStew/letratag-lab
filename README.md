# LetraTag Lab

An open-source project exploring custom label generation and computer-controlled printing with the DYMO LetraTag 200B (LT-200B).

The project aims to make small-batch, data-driven label printing reproducible and eventually accessible through a simple web interface.

## Goals

- Discover and document the printer's Bluetooth Low Energy (BLE) interface.
- Generate custom monochrome label graphics.
- Print sequential sample identifiers and labels from data files.
- Develop a reusable printing service and web interface.
- Investigate automated cutting, where supported by the printer.

## Development status

**Current phase: Windows-based Python prototype**

Initial development and protocol experiments are performed on Windows using Python and Bluetooth LE.

### Working capabilities

- Discover the LetraTag 200B over BLE and inspect its GATT services and characteristics.
- Generate content-sized monochrome PNG labels using Pillow.
- Generate batches of numbered labels.
- Print individual images using the upstream `dymo-bluetooth` package.
- Print a batch while reusing a BLE connection between labels.
- Clean up BLE notification handlers between print jobs.
- Report the printer library's result after a successful print operation (for example, Result.SUCCESS).
- Recover from the printer's automatic power-off between labels by reconnecting.

### Current limitations

- The batch printer is a command-line prototype, not yet a general-purpose printing service or GUI.
- The printer automatically powers off after a period of inactivity (timed to be five minutes). A later label may require switching the printer back on and reconnecting.
- A successful printer response is not independent verification that a label physically emerged correctly.
- When a Bluetooth error occurs during transmission, software may not know whether the label physically printed. The script asks the operator to check the label; it does not automatically retry an uncertain job.
- Automated cutting has not yet been verified.

## Project layout

- `scripts/discover_printer.py` — discover nearby BLE devices and identify the printer.
- `scripts/inspect_printer.py` — inspect the printer's BLE GATT services and characteristics.
- `scripts/make_sample_label.py` — create a sample label image.
- `scripts/make_sample_sized_label.py` — create a content-sized sample label.
- `scripts/make_sample_label_cli.py` — generate a label from command-line text.
- `scripts/make_batch_labels.py` — generate a batch of numbered label images.
- `scripts/print_batch.py` — print a batch using the original per-job connection workflow.
- `scripts/print_batch_connected.py` — print a batch using a persistent connection, with recovery after automatic power-off.
- `scripts/inspect_driver_api.py` — inspect the installed upstream package's API.

The exact contents of `scripts/` may evolve during development.

## Setup

The current development workflow uses Windows PowerShell.

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation because script execution is restricted, you can activate the environment for the current terminal session using an appropriate PowerShell execution-policy setting, or run the environment's Python executable directly.

Install the project dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Make sure the LetraTag 200B is switched on and Bluetooth is enabled on the computer before running discovery or printing scripts.

## Example workflow

### Discover the printer

```powershell
python scripts\discover_printer.py
```

### Generate three short test labels

```powershell
python scripts\make_batch_labels.py --prefix T --start 1 --count 3 --digits 1 --output-dir output\connected-test
```

This produces `T1.png`, `T2.png`, and `T3.png` in `output/connected-test`.

### Print the batch

```powershell
python scripts\print_batch_connected.py --input-dir output\connected-test
```

The script displays the queue and requires the operator to type `PRINT` before connecting. Press Enter to print each label, or type `q` to stop the queue.

### How connection recovery works

The script handles two main situations:
1. **The connection is already reported as disconnected before a label is sent.** The script searches for the printer and reconnects before attempting that label. If the printer is off and cannot be found, it asks you to switch it on and press Enter to search again, or type q to stop.
2. **The connection appears active, but the print operation fails.** The script reports a friendly explanation alongside the technical exception. Because it cannot reliably tell whether the printer physically produced the label, it asks you to check the label before choosing what to do.

For the print-outcome prompt:

- `y` — the label printed; continue without retrying it.
- `n` — the label definitely did not print; reconnect and retry it once.
- `u` — the outcome is uncertain; stop rather than risk a duplicate.

A retry failure stops the queue and asks you to check the physical label before attempting another print.

**Important:** only answer `n` when you have confirmed that the label did not print. A printer response such as `Result.SUCCESS` is useful feedback from the device, but physical output should still be checked.

## Safety and reliability principles

- Do not automatically resend a print job when its physical outcome is uncertain.
- Prefer small test batches while developing the protocol and recovery behaviour.
- Keep printer communication and image preparation explicit and inspectable.
- Distinguish observed behaviour from assumptions about undocumented printer features.
- Keep generated output and virtual-environment files out of version control where appropriate.

## Upstream work and licensing

This project builds on the reverse-engineering work and Python implementation documented in [ysfchn/dymo-bluetooth](https://github.com/ysfchn/dymo-bluetooth), by Yusuf Cihan. The upstream package is MIT-licensed; see its repository for the license and attribution requirements.

The project's own license is Apache-2.0 (see `LICENSE`).

DYMO and LetraTag are trademarks of their respective owners. This is an independent project and is not affiliated with or endorsed by DYMO.