AT commands can be used for everything from managing certificates to querying network status on Nordic's nRF91 series. The purpose of this library is to make it a little easier to interact with the nRF91-DK from Python. Nordic's AT commands are documented [here](https://infocenter.nordicsemi.com/pdf/nrf91_at_commands_v0.7.pdf).

### Requirements
The pyserial module is used to talk to the serial port and pynrfjprog can be used to program the SoC. Requirements can be installed from the command line using pip:
```
$ cd at
$ pip3 install --user -r requirements.txt
```

### Usage
The module can be used from the REPL or a custom script:
```
$ cd at
$ python3
...
>>> import at
>>> soc = at.SoC("/dev/ttyACM0")
>>> soc.get_manufacturer_id()
'Nordic Semiconductor ASA'
>>> soc.get_imei()
'352656100159253'
>>> soc.get_functional_mode()
0
>>> soc.set_functional_mode(4)
>>> soc.get_functional_mode()
4
>>> soc.list_credentials()
[[51966, 3, '0303030303030303030303030303030303030303030303030303030303030303'], [51966, 4, '0404040404040404040404040404040404040404040404040404040404040404'], [16842753, 0, '0000000000000000000000000000000000000000000000000000000000000000']]
>>> soc.read_credential(16842753, 0)
'-----BEGIN CERTIFICATE-----\nMIIFXjCCBEagAwIBA...NFu0Qg==\n-----END CERTIFICATE-----'
>>> soc.write_credential(101, 4, 'nrf-12345')
>>> soc.read_credential(101, 4)
'nrf-12345'
>>> soc.delete_credential(101, 4)
>>> soc.read_credential(101, 4)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/home/foolsday/workspace/at/at/nrf9160.py", line 163, in read_credential
    raise SoCError('{} list failed: {}.'.format(command, result[at.AT_RESPONSE_KEY]))
at.nrf9160.SoCError: SoC error: %CMNG list failed: ERROR.
>>> soc.close()
```

There is also a proof-of-concept command line interface for credential management. The features of this interface include the ability to automatically program a pre-built 'at_client' hex file onto the nRF91-DK before opening the serial port as well as programming an application hex file before shutting down. It can also automatically put the SoC into CFUN_MODE_POWER_OFF before deleting or writing credentials.
```
$ cd at
$ python3 cmng.py --help
usage: cmng [-h] [--sec_tag SECURITY_TAG] [--cred_type CREDENTIAL_TYPE]
            [--passwd PRIVATE_KEY_PASSWD] [-o PATH_TO_OUT_FILE]
            [--content CONTENT | --content_path PATH_TO_CONTENT]
            [-s JLINK_SERIAL_NUMBER] [-x] [--program_app PATH_TO_APP_HEX_FILE]
            [--power_off]
            {list,read,write,delete} SERIAL_PORT_DEVICE

A command line interface for managing nRF91 credentials.

positional arguments:
  {list,read,write,delete}
                        operation
  SERIAL_PORT_DEVICE    serial port device to use for AT commands

optional arguments:
  -h, --help            show this help message and exit
  --sec_tag SECURITY_TAG
                        specify sec_tag [0, 2147483647]
  --cred_type CREDENTIAL_TYPE
                        specify cred_type [0, 5]
  --passwd PRIVATE_KEY_PASSWD
                        specify private key password
  -o PATH_TO_OUT_FILE, --out_file PATH_TO_OUT_FILE
                        write output from read operation to file instead of
                        stdout.
  --content CONTENT     specify content (i.e. key material)
  --content_path PATH_TO_CONTENT
                        read content (i.e. key material) from file
  -s JLINK_SERIAL_NUMBER, --serial_number JLINK_SERIAL_NUMBER
                        serial number of J-Link
  -x, --program_hex     begin by writing prebuilt 'at_client' hex file to
                        device
  --program_app PATH_TO_APP_HEX_FILE
                        program specified hex file to device before finishing
  --power_off           put modem in CFUN_MODE_POWER_OFF if necessary

WARNING: nrf_cloud relies on credentials with sec_tag 16842753.
```
The basic list, read, delete, and write functionality exists but is not thoroughly tested:
```
$ python3 ./cmng.py list /dev/ttyACM0 -x
[]
$ python3 ./cmng.py write /dev/ttyACM0 --sec_tag 16842753 --cred_type 0 --content_path ./nrf_cloud_ca_cert.crt
$ python3 ./cmng.py list /dev/ttyACM0 
[16842753, 0, '0000000000000000000000000000000000000000000000000000000000000000']
$ python3 ./cmng.py read /dev/ttyACM0 --sec_tag 16842753 --cred_type 0
'-----BEGIN CERTIFICATE-----\nMIIFXjCCB...NFu0Qg==\n-----END CERTIFICATE-----'
$ python3 ./cmng.py delete /dev/ttyACM0 --sec_tag 16842753 --cred_type 0
$ python3 ./cmng.py list /dev/ttyACM0 
[]
```

### Limitations
The module's functionality is currently limited to reading manufacturer ID, IMEI, setting the modem's functional mode, and credential management.

### About
Most AT commands are represented by a single Python dictionary with 'cmd', 'type', and 'params' keys. The 'cmd' value is arbitrary but always starts with '+' or '%' with the nRF91. The 'type' value can be 'SET', 'READ', or 'TEST'. The 'params' value is a list of Python values of type None, int, str, or (single-nested) lists.

Some command strings use a primary command (e.g. %XSUDO to provide authenticatication) followed by one or more "concatenated" commands that are sent as part of a single string. These commands are separated by the ';' character.

    Command string: 'AT+CEMODE=0'
    Dictionary:     {'cmd':'+CEMODE', 'type':'SET', 'params':[0]}

    Command string: 'AT%XSUDO=7,"c2lnbmF0dXJl";%CMNG=1',
    Dictionary:     [{'cmd':'%XSUDO', 'type':'SET', 'params':[7, "c2lnbmF0dXJl"]},
                     {'cmd':'%CMNG', 'type':'SET', 'params':[1]}]

Response strings are similar to commands and use the same 'params' key and format. However, responses have a 'response' key instead of a 'cmd' key, the 'type' key is set to 'RESPONSE', and an 'error' key is set to True or False.

    Response string: 'OK'
    Dictionary:      {'response':'OK', 'type':'RESPONSE', 'error':False, 'params':[]})

    Response string: '+CMS ERROR: 128'
    Dictionary:      {'response':'+CMS ERROR',
                      'type':'RESPONSE',
                      'error':True,
                      'params':[128]}

The 'test/tests.py' script contains several example strings and their dictionary equivalents.
