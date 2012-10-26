#! /usr/bin/env/python

import os, shutil, sys, unittest
import io

import splice, ui

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
    """
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

    def test_Repair(self):
        ''' Build a splice, make sure it's incomplete, then try to repair it '''
        raise NotImplementedError("This is vital!")
    """
    def test_ValidateSlice(self):
        # Switch to non-debug mode
        self.tearDown()
        # Because tearDown() closes the old buffer
        self.__buffer = io.BytesIO(self.buffer)
        self.__BuildTestSplice()

        merger = splice.Splicer(ui.DoesNothing())
        merger.WorkingDirectory(self.__splicer.DestinationDirectory())
        merger.SourceFileName(self.__splicer.SourceFileName() + ".details")
        # Actually, if this fails, you probably have hardware issues
        # Except for the fact that it's so freaking flaky to get this set up.
        # This part of the interaction is horribly brittle
        self.assertTrue(self.__splicer.Validate())

        dst = self.__splicer.DestinationDirectory()
        files = os.listdir(dst)
        found_chunk = False
        for f in files:
            ext = f[-5:]
            if ext == 'chunk':
                found_chunk = True
                os.remove(f)
                break
        self.assertTrue(found_chunk)

        self.assertFalse(self.__splicer.Validate())

    ##############################################################
    # Boiler Plate
    ##############################################################

    def __BuildTestSplice(self):
        self.__splicer = splice.Splicer(ui.DoesNothing())
        # Just to give it something vaguely interesting to work with
        self.__splicer.BufferSize(len(self.buffer)/15)
        self.__splicer.SourceFileName("quetzalcoatl.testing")
        self.__splicer.Source(self.__buffer)

    def setUp(self):
        # This really indicates that I need a TestSuite. Or, at least,
        # multiple TestCase instances. Since frequently I'll be working
        # with files on disk rather than memory.
        # (Though, honestly, I shouldn't be)
        self.__buffer = io.BytesIO(self.buffer)

        splice.SwitchToDebug()

        self.__BuildTestSplice()

    def tearDown(self):
        splice.SwitchToDebug(False)

        dst = self.__splicer.DestinationDirectory()
        if os.path.exists(dst):
            shutil.rmtree(dst)

        del self.__splicer
        self.__buffer.close()

if __name__ == '__main__':
    unittest.main()
