#! /usr/bin/env/python

import os, unittest
import io

import splice, ui

splice.SwitchToDebug()

class TestStreamSplicing(unittest.TestCase):
    buffer = """The quick red fox jumped over the lazy brown dog.
Now is the time for all good men to come to the aid of their country.
Blah, blah, blah.
Badjes? We don't need no steenking badges!
Ipsum Lorem Facto. Je ne parles pas Francais.
Old McDonald had a farm. Really should be working with binary data, but Python's
being obnoxious about that entire thing."""

    ##############################################################
    # Tests
    ##############################################################

    def test_Nothing(self):
        ''' Just make sure the bare-bones basics work '''
        pass

    def test_CreateBasicSplice(self):
        ''' Can we run through the bare splicing process successfully? '''
        self.__splicer.Operate()

    ##############################################################
    # Boiler Plate
    ##############################################################

    def setUp(self):
        self.__buffer = io.BytesIO(self.buffer)

        #self.__splicer = splice.Splicer(self.__ui)
        self.__splicer = splice.Splicer(ui.DoesNothing())
        # Just to give it something vaguely interesting to work with
        self.__splicer.BufferSize(len(self.buffer)/15)
        self.__splicer.SetSourceFileName("quetzalcoatl.testing")

    def __KillTestSplice(self, directory = "quetzalcoatl.testing.split"):
        if os.path.exists(directory):
            files = os.listdir(directory)
            for f in files:
                os.unlink(f)

    def __KillTestDirectory(self, location = "quetzalcoatl.testing.split"):
        if os.path.exists(location):
            self.__KillTestSplice(location)
            os.unlink(location)

    def tearDown(self):
        self.__KillTestDirectory(self.__splicer.DestinationDirectory())

        self.__splicer.Dispose()

        # Totally redundant, since it's just a memory buffer and __splicer.Dispose will handle this
        self.__buffer.close()

if __name__ == '__main__':
    unittest.main()
