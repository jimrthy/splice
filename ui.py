#! /usr/bin/env python

''' Think of this as the View part of MVC.
I'm trying to split the UI away from program logic. '''

class UI:
    def __init__(self):
        # For a cheesy command-line "progress bar". Sufficient for now, though
        self.__current_kilo = 0

    def PromptForYorN(self, msg):
        ''' Ask the user something that indicates a Yes or No response '''
        response = raw_input(msg)
        print
        return response.strip()[0].lower() == 'y'

    def UpdateProgress(self):
        msg = "# %dK, " % (self.__current_kilo,)
        sys.stdout.write (msg)
