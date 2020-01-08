"""
Example command line executable for nRF91 credential management.

Operations:
    list    (--sec_tag and --cred_type optional)
    write   (--sec_tag and --cred_type and content required)
    delete  (--sec_tag and --cred_type required)
    read    (--sec_tag and --cred_type required)
    write PSK
    write certs

write PSK:
    --psk           "FOOBAR"
    --id            "nrf-foobar"
    --sec_tag       1234

write certs:
    --CA_cert       path
    --client_cert   path
    --private_key   path
    --passwd        "foobar"
    --sec_tag       1234
"""
import sys
import os
import argparse

from at import at
import pynrfjprog
from pynrfjprog import API


def _write_firmware(nrfjprog_api, fw_hex):
    """Replaces the PPK's firmware."""
    print("Writing firmware...", end='')
    nrfjprog_api.erase_all()
    for segment in fw_hex:
        nrfjprog_api.write(segment.address, segment.data, True)
    print("done")


def _close_and_exit(nrfjprog_api, status):
    """"""
    if nrfjprog_api:
        nrfjprog_api.disconnect_from_emu()
        nrfjprog_api.close()
    sys.exit(status)


def _connect_to_emu(args):
    """Connects to emulator and replaces the PPK firmware if necessary."""
    nrfjprog_api = pynrfjprog.API.API('NRF91')
    nrfjprog_api.open()
    if args.serial_number:
        nrfjprog_api.connect_to_emu_with_snr(args.serial_number)
    else:
        nrfjprog_api.connect_to_emu_without_snr()
    return nrfjprog_api


def _add_and_parse_args():
    """Build the argparse object and parse the args."""
    parser = argparse.ArgumentParser(prog='cmng',
                                     description='A command line interface for managing nRF91 credentials.',
                                     epilog='WARNING: nrf_cloud relies on credentials with sec_tag 16842753.')

    parser.add_argument('operation', choices=('list', 'read', 'write', 'delete'),
                        help="operation", type=str)
    parser.add_argument('suboperation', choices=('PSK', 'certs'), nargs='?',
                        help="optional suboperation when writing", type=str)
    parser.add_argument('port', metavar='SERIAL_PORT_DEVICE',
                        help="serial port device to use for AT commands", type=str)
    parser.add_argument("--sec_tag", type=int, metavar="SECURITY_TAG",
                        help="specify sec_tag [0, 2147483647]")
    parser.add_argument("--cred_type", type=int, metavar="CREDENTIAL_TYPE",
                        help="specify cred_type [0, 5]")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--content", type=str, metavar="CONTENT",
                        help="specify content (i.e. key material)")
    group.add_argument("--content_path", type=str, metavar="PATH_TO_CONTENT",
                        help="read content (i.e. key material) from file")
    parser.add_argument("-s", "--serial_number", type=int, metavar="JLINK_SERIAL_NUMBER",
                        help="serial number of J-Link")
    parser.add_argument("-x", "--program_hex", action='store_true',
                        help="begin by writing prebuilt 'at_client' hex file to device")
    parser.add_argument("--program_app", type=str, metavar="PATH_TO_APP_HEX_FILE",
                        help="program specified hex file to device before finishing")
    parser.add_argument("--power_off", action='store_true',
                        help="put modem in CFUN_MODE_POWER_OFF if necessary")

    args = parser.parse_args()

    if not args.sec_tag and args.operation != 'list':
        parser.print_usage()
        print("error: sec_tag required for all operations except listing")
        sys.exit(-1)
    if not args.cred_type and args.operation != 'list':
        parser.print_usage()
        print("error: cred_type required for all operations except listing")
        sys.exit(-1)
    if args.suboperation and args.operation != 'write':
        parser.print_usage()
        print("error: '{}' suboperation only allowed when writing".format(args.suboperation))
        sys.exit(-1)
    if args.operation == 'write' and not (args.content or args.content_path):
        parser.print_usage()
        print("error: content or content_path is required when writing")
        sys.exit(-1)
    if args.serial_number and not (args.program_hex or args.program_app):
        parser.print_usage()
        print("error: serial number is pointless unless programming a hex file")
        sys.exit(-1)
    return args


def _main():
    """Parses arguments for the PPK CLI."""
    args = _add_and_parse_args()
    nrfjprog_api = None
    try:
        if args.program_hex:
            nrfjprog_api = _connect_to_emu(args)
            # TODO: Program, reset, and wait.
            _close_and_exit(nrfjprog_api, 0)
    except Exception as ex:
        print("main.py: error: " + str(ex))
        _close_and_exit(nrfjprog_api, -1)


if __name__ == "__main__":
    _main()
