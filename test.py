#! /usr/bin/env/python

import os, shutil, sys, unittest
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

    def test_SourceManipulation(self):
        ''' Switch the source buffers around, just because we can '''
        # I suppose that this should probably be multiple tests
        buffer = self.__splicer.Source()
        self.assertEqual(self.__buffer, buffer)

        garbage = "aeioubcdfghjkl"
        self.assertRaises(AttributeError, self.__splicer.Source, garbage)
        self.assertNotEqual(garbage, self.__splicer.Source())

        self.__splicer.ResetSource()
        self.assertEqual(sys.stdin, self.__splicer.Source())
        self.assertEqual("STDIN", self.__splicer.SourceFileName())

    ##############################################################
    # Boiler Plate
    ##############################################################

    def setUp(self):
        # This really indicates that I need a TestSuite. Or, at least,
        # multiple TestCase instances. Since frequently I'll be working
        # with files on disk rather than memory.
        # (Though, honestly, I shouldn't be)
        self.__buffer = io.BytesIO(self.buffer)

        #self.__splicer = splice.Splicer(self.__ui)
        self.__splicer = splice.Splicer(ui.DoesNothing())
        # Just to give it something vaguely interesting to work with
        self.__splicer.BufferSize(len(self.buffer)/15)
        self.__splicer.SourceFileName("quetzalcoatl.testing")
        self.__splicer.Source(self.__buffer)

    def tearDown(self):
        dst = self.__splicer.DestinationDirectory()
        if os.path.exists(dst):
            shutil.rmtree(dst)

        # Totally redundant, since it's just a memory buffer and __splicer.Dispose will handle this
        self.__buffer.close()

if __name__ == '__main__':
    unittest.main()
