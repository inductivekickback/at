AT commands can be used for everything from managing certificates to querying network status on Nordic's nRF91 series. The purpose of this library is to make it a little easier to interact with the nRF91 from Python. Nordic's AT commands are documented [here](https://infocenter.nordicsemi.com/pdf/nrf91_at_commands_v0.7.pdf).

### Requirements
The pyserial module is used to talk to the serial port and pynrfjprog can be used to program the SoC. Requirements can be installed from the command line using pip:
```
$ cd at
$ pip3 install --user -r requirements.txt
```

### Usage
The SoC module can be used from the REPL or a custom script:

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
