#! /usr/bin/env/python

import unittest
import io

import splice, ui



class TestStreamSplicing(unittest.TestCase):
    buffer = """The quick red fox jumped over the lazy brown dog.
Now is the time for all good men to come to the aid of their country.
Blah, blah, blah.
Badjes? We don't need no steenking badges!"""

    def setUp(self):
        self.__buffer = io.BytesIO(self.buffer)

        testUi = ui.DoesNothing()
        self.__splicer = splice.Splicer(testUi)

    def tearDown(self):
        # Probably redundant
        self.__buffer.close()

    def testNothing(self):
        ''' Just make sure the bare-bones basics work '''
        pass

if __name__ == '__main__':
    unittest.main()
