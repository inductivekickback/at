AT commands can be used for everything from managing certificates to querying network status on Nordic's nRF91 series. The purpose of this library is to make it a little easier to interact with the nRF91 from Python. Nordic's AT commands are documented [here](https://infocenter.nordicsemi.com/pdf/nrf91_at_commands_v0.7.pdf).

### Requirements
No imports, just Python3.

### About
Most AT commands are represented by a single Python dictionary with 'cmd', 'type', and 'params' keys. The 'cmd' value is arbitrary but always starts with '+' or '%' with the nRF91. The 'type' value can be 'SET', 'READ', or 'TEST'. The 'params' value is a list of Python values of type None, int, str, or (single-nested) lists.

A few command strings use a primary command (e.g. %XSUDO to provide authenticatication) followed by one or more "concatenated" commands that are sent as part of a single string. These commands are separated by the ';' character.

    Command string: 'AT+CEMODE=0'
    Dictionary:     {'cmd':'+CEMODE', 'type':'SET', 'params':[0]}

    Command string: 'AT%XSUDO=7,"c2lnbmF0dXJl";%CMNG=1',
    Dictionary:     [{'cmd':'%XSUDO', 'type':'SET', 'params':[7, "c2lnbmF0dXJl"]},
                     {'cmd':'%CMNG', 'type':'SET', 'params':[1]}]

Responses strings are similar to commands and use the same 'params' key and format. However, responses have a 'response' key instead of a 'cmd' key, the 'type' key is set to 'RESPONSE', and an 'error' key is set to True or False.

    Response string: 'OK'
    Dictionary:      {'response':'OK', 'type':'RESPONSE', 'error':False, 'params':[]})

    Response string: '+CMS ERROR: 128'
    Dictionary:      {'response':'+CMS ERROR',
                      'type':'RESPONSE',
                      'error':True,
                      'params':[128]}

The 'test/tests.py' script contains several example strings and their dictionary equivalents.
