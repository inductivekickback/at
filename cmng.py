"""
Example command line executable for nRF91 credential management.
"""
import sys
import os
import argparse
import time

from pynrfjprog import HighLevel
import at


FW_STARTUP_DELAY_S = 3
PREBUILT_HEX_PATH = os.path.sep.join(("hex", "merged.hex"))


def _write_firmware(nrfjprog_probe, fw_hex):
    """Program and verify a hex file."""
    nrfjprog_probe.program(fw_hex)
    nrfjprog_probe.verify(fw_hex)
    nrfjprog_probe.reset()


def _close_and_exit(nrfjprog_api, status):
    """Close the nrfjprog connection if necessary and exit."""
    if nrfjprog_api:
        nrfjprog_api.close()
    sys.exit(status)


def _connect_to_jlink(args):
    """Connect to the debug probe."""
    api = HighLevel.API()
    api.open()
    connected_serials = api.get_connected_probes()
    if args.serial_number:
        if args.serial_number in connected_serials:
            connected_serials = [args.serial_number]
        else:
            print(f"error: serial_number not found ({args.serial_number})")
            _close_and_exit(api, -1)
    if not connected_serials:
        print("error: no debug probes found")
        _close_and_exit(api, -1)
    if len(connected_serials) > 1:
        print("error: multiple debug probes found, use --serial_number")
        _close_and_exit(api, -1)
    probe = HighLevel.DebugProbe(api, connected_serials[0], HighLevel.CoProcessor.CP_APPLICATION)
    return (api, probe)


def _power_off_if_necessary(soc):
    """Read the modem's functional state and power it off before deleting or writing."""
    mode = soc.get_functional_mode()
    if mode == 1:
        soc.set_functional_mode(0)


def _add_and_parse_args():
    """Build the argparse object and parse the args."""
    parser = argparse.ArgumentParser(prog='cmng',
                                     description=('A command line interface for ' +
                                                  'managing nRF91 credentials.'),
                                     epilog=('WARNING: nrf_cloud relies on credentials '+
                                             'with sec_tag 16842753.'))

    parser.add_argument('operation', choices=('list', 'read', 'write', 'delete', 'query'),
                        help="operation", type=str)
    parser.add_argument('port', metavar='SERIAL_PORT_DEVICE',
                        help="serial port device to use for AT commands", type=str)
    parser.add_argument("--sec_tag", type=int, metavar="SECURITY_TAG",
                        help="specify sec_tag [0, 2147483647]")
    parser.add_argument("--cred_type", type=int, metavar="CREDENTIAL_TYPE",
                        help="specify cred_type [0, 5]")
    parser.add_argument("--passwd", type=str, default=None, metavar="PRIVATE_KEY_PASSWD",
                        required=False, help="specify private key password")
    parser.add_argument("-o", "--out_file", type=str, metavar="PATH_TO_OUT_FILE",
                        help="write output from read operation to file instead of stdout.")
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
    parser.add_argument("-c", "--command", type=str, default=None, metavar="MODEM_COMMAND",
                        help="request custom information from modem")

    args = parser.parse_args()
    if args.operation != 'query':
        if args.sec_tag is None and args.operation != 'list':
            parser.print_usage()
            print("error: sec_tag required for all operations except listing")
            sys.exit(-1)
        if args.cred_type is None and args.operation != 'list':
            parser.print_usage()
            print("error: cred_type required for all operations except listing")
            sys.exit(-1)
        if args.operation == 'write' and not (args.content or args.content_path):
            parser.print_usage()
            print("error: content or content_path is required when writing")
            sys.exit(-1)
        if args.out_file and args.operation != 'read':
            parser.print_usage()
            print("error: out_file is only available when reading credentials")
            sys.exit(-1)
        if args.serial_number and not (args.program_hex or args.program_app):
            parser.print_usage()
            print("error: serial number is pointless unless programming a hex file")
            sys.exit(-1)
    else:
        if not args.command:
            parser.print_usage()
            print("error: query command has to be specified")
            sys.exit(-1)

    return args


def _read_cert_file(path):
    """Read a certificate file and return it as a string. Line endings should be <LF>."""
    with open(path, 'r') as in_file:
        content = [line.strip() for line in in_file.readlines()]
        return '\n'.join(content)


def _communicate(args):
    """Open the serial port and use the at module."""
    soc = None
    try:
        soc = at.SoC(args.port)
        if args.power_off and args.operation in ('delete', 'write'):
            _power_off_if_necessary(soc)
        if args.operation == 'list':
            result = soc.list_credentials(args.sec_tag, args.cred_type)
            if len(result) == 1:
                print(result[0])
            else:
                print(result)
        elif args.operation == 'read':
            result = soc.read_credential(args.sec_tag, args.cred_type)
            if args.out_file:
                with open(args.out_file, 'wb') as out_file:
                    out_file.write(result.encode())
            else:
                print(result)
        elif args.operation == 'delete':
            soc.delete_credential(args.sec_tag, args.cred_type)
        else:
            content = None
            if args.content_path:
                content = _read_cert_file(args.content_path)
            else:
                content = args.content
            soc.write_credential(args.sec_tag, args.cred_type, content, args.passwd)
    finally:
        if soc:
            soc.close()

def _get_command(port, command):
    """Open the serial port and request given command"""
    soc = None
    try:
        soc = at.SoC(port)
        return soc.query_modem(command)
    finally:
        soc.close()


def _main():
    """Parses arguments for the CLI."""
    args = _add_and_parse_args()
    nrfjprog_api = None
    nrfjprog_probe = None
    try:
        if args.command:
            res = _get_command(args.port, args.command)
            print(res)
            sys.exit(0)

        if args.program_hex or args.program_app:
            nrfjprog_api, nrfjprog_probe = _connect_to_jlink(args)

        if args.program_hex:
            _write_firmware(nrfjprog_probe, PREBUILT_HEX_PATH)
            # Allow the firmware to boot.
            time.sleep(FW_STARTUP_DELAY_S)

        _communicate(args)

        if args.program_app:
            _write_firmware(nrfjprog_probe, args.program_app)

        _close_and_exit(nrfjprog_api, 0)
    except Exception as ex:
        print("error: " + str(ex))
        _close_and_exit(nrfjprog_api, -1)


if __name__ == "__main__":
    _main()
