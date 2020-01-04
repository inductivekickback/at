"""
Basic unit test module for the at module.
"""
import os
import sys
import unittest

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, os.getcwd())

import at


class TestATParsing(unittest.TestCase):
    """Defines unit tests for verifying parsing functionality."""
    TEST_CMDS = [('AT+CEMODE=0',
                  {'cmd':'+CEMODE', 'type':'SET', 'params':[0]}),
                 ('AT+CSIM=14,"A0A40000027F20"',
                  {'cmd':'+CSIM', 'type':'SET', 'params':[14, "A0A40000027F20"]}),
                 ('AT%XSUDO=7,"c2lnbmF0dXJl";%CMNG=1',
                  [{'cmd':'%XSUDO', 'type':'SET', 'params':[7, "c2lnbmF0dXJl"]},
                   {'cmd':'%CMNG', 'type':'SET', 'params':[1]}]),
                 ('AT+CRSM=176,28539,0,0,12',
                  {'cmd':'+CRSM', 'type':'SET', 'params':[176, 28539, 0, 0, 12]}),
                 ('AT+CFUN?',
                  {'cmd':'+CFUN', 'type':'READ', 'params':[]}),
                 ('AT%XSIM?',
                  {'cmd':'%XSIM', 'type':'READ', 'params':[]}),
                 ('AT+CGEREP=?',
                  {'cmd':'+CGEREP', 'type':'TEST', 'params':[]}),
                 ('AT%XCBAND=?',
                  {'cmd':'%XCBAND', 'type':'TEST', 'params':[]}),
                 ('AT%FOO=7,"c2lnbmF0dXJl";+BAR=(1,2,3)',
                  [{'cmd':'%FOO', 'type':'SET', 'params':[7, "c2lnbmF0dXJl"]},
                   {'cmd':'+BAR', 'type':'SET', 'params':[[1, 2, 3]]}])]
    TEST_RSPS = [('ERROR',
                  {'response':'ERROR', 'type':'RESPONSE', 'error':True, 'params':[]}),
                 ('OK',
                  {'response':'OK', 'type':'RESPONSE', 'error':False, 'params':[]}),
                 ('+CME ERROR: 513',
                  {'response':'+CME ERROR',
                    'type':'RESPONSE', 'error':True, 'params':[513]}),
                 ('+CGSN: "352656100032138"',
                  {'response':'+CGSN',
                    'type':'RESPONSE', 'error':False, 'params':["352656100032138"]}),
                 ('+CMEE: 1',
                  {'response':"+CMEE", 'type':'RESPONSE', 'error':False, 'params':[1]}),
                 ('+CMS ERROR: 128',
                  {'response':'+CMS ERROR',
                    'type':'RESPONSE', 'error':True, 'params':[128]}),
                 ('+CNUM: ,"+1234567891234",145',
                  {'response':'+CNUM', 'type':'RESPONSE', 'error':False,
                    'params':[None, '+1234567891234', 145]}),
                 ('+CLCK: ("SC")',
                  {'response':'+CLCK',
                    'type':'RESPONSE', 'error':False, 'params':[['SC']]}),
                 ('%FOO: ("A", "B", 10)',
                  {'response':'%FOO',
                    'type':'RESPONSE', 'error':False, 'params':[['A', 'B', 10]]}),
                 ('%CMNG: 16842753,0,"000000000000000000000000000000000' +
                  '0000000000000000000000000000000"',
                  {'response':'%CMNG',
                    'type':'RESPONSE', 'error':False,
                    'params':[16842753,
                              0,
                              "000000000000000000000000000000000000000000" +
                              "0000000000000000000000"]})]

    def test_command_encoding(self):
        """Encode command dicts and compare them to the original string."""
        for cmd_str, cmd_dict in self.TEST_CMDS:
            result = at.encode_command(cmd_dict)
            self.assertEqual(result, cmd_str)

    def test_command_parsing(self):
        """Parse command strings and compare them to dicts."""
        for cmd_str, cmd_dict in self.TEST_CMDS:
            result = at.parse_string(cmd_str)
            self.assertEqual(result, cmd_dict)

    def test_responses(self):
        """Iterate through sample response strings."""
        for cmd_str, params in self.TEST_RSPS:
            result = at.parse_string(cmd_str)
            self.assertEqual(result, params)


if __name__ == '__main__':
    unittest.main()
