#! /usr/bin/env python

''' Wrapper file for the UI to the splicer '''

import getopt, logging, sys
import splice
import ui

logging.basicConfig(level=logging.DEBUG)

class Program:
    def __init__(self, argv):
        self.__argv = argv

        self.__logger = logging.getLogger("splice.Program")

        interface = ui.UI()
        self.__splicer = splice.Splicer(interface)

    def main(self):
        try:
            self.__logger.debug("Checking options")
            opts, args = getopt.getopt( self.__argv, "hrsmf:vb:d:", 
                                        ["help", "restart", "split", 
                    "merge","file=", "version", "buffer=", 'directory='])
        except getopt.GetoptError:
            print "Option error"
            print self.usage()
            # Really? This is the best magic number I could come up with?
            sys.exit(2)
        else:
            self.__logger.debug("Manipulating options")
            for opt, arg in opts:
                if opt in("-h", "--help"):
                    print self.usage()
                    sys.exit()
                elif opt in ("-m", "--merge"):
                    self.__splicer.SetMergeMode()
                    self.__logger.debug("Merging")
                elif opt in ("-r", "--restart"):
                    self.__splicer.SetRepairSplice(True)
                    self.__logger.info("Repairing")
                elif opt in ("-f", "--file"):
                    # Would be nice to loop through args and split them 1 at a time, creating
                    # subdirectories as appropriate. Do that later, when I have time
                    # (or merging multiple directories, of course)

                    # Actually, that wouldn't be that hard. Just stick them in a list
                    # and pass them into the Splicer one at a time. It probably
                    # shouldn't be handling the source file i/o anyway.
                    # Do that next
                    self.__splicer.SetSourceFileName(arg)
                    self.__logger.info("Splicing %s" % (arg,))
                elif opt in ("-v", "--version"):
                    print self.__splicer.Version()
                    sys.exit()
                elif opt in ("-b", "--buffer"):
                    self.__splicer.BufferSize(int(arg))
                elif opt in ("-d", "--directory"):
                    self.__splicer.WorkingDirectory(arg)

            self.__logger.debug("Operating")
            self.__splicer.Operate()
            self.__logger.debug("Done")

    def usage(self):
        instructions = """./splice.py [-h -m -s -r -v] [-d directory] [-f file]
-h: print this help message
-m: switch to merge mode
-r: allow splitting to be incremental (i.e. if errors happen the first time around)
-v: print version information
-d directory: should specify where to find spliced files to merge. Doesn't seem to work
-f file: operate on file (STDIN by default...although that probably doesn't work)"""
        return instructions

    def Dispose(self):
        self.__splicer.Dispose()

if __name__ == '__main__':
  program = Program(sys.argv[1:])
  try:
    logging.debug("Calling main")
    program.main()
  finally:
    logging.debug("Calling dispose")
    program.Dispose()

  logging.debug("Exiting")
logging.info("Good-bye")
