#! /usr/bin/env python

''' Split/combine big files '''

# Example usage:
# Create an archive:
# ./splice.py -f /usr/bin/whatever.zip
# If you're having I/O issues:
# python ./splice.py -r -f /usr/bin/whatever.zip
# Put the pieces back together
# (actually, I think this sample may be horrible misleading)
# ./splice.py -m -d whatever.zip.split -f whatever.zip.details

from __future__ import with_statement

import hashlib, logging, os, sys
import random # debugging only
import myexceptions

logging.basicConfig(level=logging.DEBUG)

# Set this next to False unless you want lots of weird things happening.
# Nowhere near as efficient as C-preprocessor, but (yet again), this isn't
# a CPU-bound process
_DEBUG = False

def SwitchToDebug(d = True):
    _DEBUG = d

class Splicer:
    # FIXME: Really should have two seperate classes for merging and splitting
    # instead of handling it this way
    def __init__(self, ui):
        self.__ui = ui

        # Just pick a default
        self.__mode = "split"

        # Since this is what we almost always want
        self.__repairing = False

        # Should declare the variables that get created here for the sake of pickling.
        # Wonder if it still works that way?
        # Oh well. This class should pretty much *never* be pickled
        self.ResetSource()

        self.__version = "0.0.2"

        # This pretty much forces the user to specify a size. It's tempting
        # to set it to 0 or None and change it into a required option
        self.__buffer_size = 1
    
        self.__logger = logging.getLogger("splice.Splicer")
        # FIXME: Configure the logger to send its output to self.__ui

        self.__working_directory = '.'

        # Note that this is Merger-specific
        self.__chunk_count = None

    def Operate(self):
        ''' Effectively, this is main() '''
        if self.__mode == "merge":
            self._Merge()
        elif self.__mode == "split":
            self.__ActualSplitter()
        else:
            raise NotImplementedError("Unknown mode: " + str(self.__mode))

    #########################################################
    # Some more or less useful getters/setters boilerplate
    #########################################################

    def SetMergeMode(self):
        self.__mode = "merge"

    def SetRepairSplice(self, mode):
        self.__repairing = mode

    def SourceFileName(self, name=None):
        if name is not None:
            self.__source_file_name = name

        return self.__source_file_name

    def ResetSource(self):
        ''' Work-around to allow Source to work as both a Getter and Setter '''
        # Try to play unix-nice
        self.__source = sys.stdin
        self.__source_file_name = "STDIN"
        # Start with a default that kind of makes sense for piping from STDIN
        self.__source_size = sys.maxint

    def Source(self, src=None):
        if src is not None:
            try:
                src.seek(0, 2)
                self.__source_size = src.tell()
                src.seek(0, 0)
            except AttributeError:
                self.__logger.error("Currently only supporting seekable objects for splicing")
                raise
            self.__source = src

        return self.__source

    def Version(self):
        return self.__version

    def BufferSize(self, size=None):
        if size is not None:
            self.__buffer_size = int(size)

        return self.__buffer_size

    def WorkingDirectory(self, pwd=None):
        if pwd is not None:
            self.__working_directory = pwd

        return self.__working_directory

    def DestinationDirectory(self):
        # Better would be to make this a member variable calculated whenever "Base Name" is set

        # Just go with the file name
        # Note that this depends on the source file being in a separate
        # directory
        base_name = self.__PickBaseName()

        # Somewhere to put the pieces
        destination_directory = base_name + '.split'

        return destination_directory

    ##################################################################################
    # Merging
    ##################################################################################

    def __PickDigest(self, version):
        ''' An unfortunate leftover from the way I'm currently handling version details '''
        # Returns the hashing style. Sets internal buffer size property
        
        # chunk size and hashing algorithm
        # (one of those rare occasions when it needs to be declared...though this 
        # implementation's broken)
        digest = None

        if version == '0.0.1':
            digest = hashlib.md5()
        elif version == '0.0.2':
            digest = hashlib.sha256()
        else:
            raise myexceptions.VersionError("Unknown version")

        return digest

    def __PickSourceRootName(self):
        # There has to be a built-in to just glob this

        # discard the ".details"--really should make the UI simpler. Just go
        # into the folder, run splice.py -m, and it finds the .details file and
        # merges everything.  TODO: do that soon
        source_root_name = self.__source_file_name[:-8]

        # Cheese-ball work-around for windows:
        if source_root_name[:2] == ".\\":
            source_root_name = source_root_name[2:]

        self.__logger.debug("Combining into a file named '" + source_root_name + "'")

        return source_root_name

    def __Chunks(self, list_of_file_names, source_root_name):
        ''' Which chunk files are available? '''
        count = 0
        files_to_merge = []
        for file_name in list_of_file_names:
            #self.__logger.debug("Maybe counting a file named '" + str(file_name) + "'")

            name_pieces = file_name.split('.')
            # ignore the '.###.chunk' part.  Do it this way so I can vary the
            # length of the string that specifies the count
            #self.__logger.debug(str(name_pieces))
            if name_pieces[-1] == 'chunk':
                root_name = '.'.join(name_pieces[:-2])
                if root_name == source_root_name:
                    files_to_merge.append(file_name)
                    count += 1
                else:
                    self.__logger.debug("Not part of this split")
            else:
                self.__logger.debug(file_name + " : Not a chunk")

        return files_to_merge

    def __LoadDetails(self):
        # Suppose I could pipe the details from STDIN, but it just doesn't seem to
        # make any sense.  But what about sending them to STDOUT?
        if not self.__source_file_name:
            # No, this error message isn't very helpful
            raise NotImplementedError("Implement looking for a .details file in the pwd")

        self.__logger.debug("Pulling details out of the directory file '" + self.__source_file_name + "'")

        # the files that might be interesting
        list_of_file_names = os.listdir(self.__working_directory)

        details_file_name = os.path.join(self.__working_directory, self.__source_file_name)
        with open(details_file_name, "r") as details_file:
            # FIXME: This really should be a YAML file
            # Version:
            self.__version = details_file.readline().split(' ')[1].strip()

            # Chunk Count:
            self.__chunk_count = int(details_file.readline().split(' ')[2].strip())

            # stash this for later
            expected_checksum = details_file.readline().split(' ')[1].strip()

            if self.__version == '0.0.1':
                # This really isn't justified. The -b parameter was available then. I just
                # don't recall it ever being used. Does this actually matter on the
                # merge? I'm just reading 'destination' files until the end, then merging
                # them back into the 'source'.
                # Actually, that's a *really* important detail for dealing with trying to
                # work around bad sectors
                self.__buffer_size = 1024
            elif self.__version == '0.0.2':
                self.__buffer_size = int(details_file.readline().split(' ')[1].strip())

    def Validate(self):
        # Copy/pasted from _Merge. Smells!
        list_of_file_names = os.listdir(self.__working_directory)
        source_root_name = self.__PickSourceRootName()

        files_to_merge = self.__Chunks(list_of_file_names, source_root_name)
        return len(files_to_merge) == self.__chunk_count

    def _Merge(self):
        ''' Restore a splice to a single file '''

        # FIXME: Break this into multiple methods. Maybe even its own class

        self.__LoadDetails()

        # Here's where the entire tangled mess starts collapsing.
        # __LoadDetails loads a version.
        # That value is *vastly* different than what's really meant by the splitter.
        # *Very* strong incentive to split these into multiple classes.
        # Especially since the splitters really should have one class per version
        digest = self.__PickDigest(self.__version)

        # *really* tempting to just use magic strings everywhere for version numbers
        # Are they really any less confusing than trying to deal with a variable?
        # Would named constants really gain me anything in this case?
        # No. Much better to parse it and deal with major/minor versions as needed.
        # Though I just realized that I've committed a fairly major sin by breaking
        # the interface between 0.0.1 and 0.0.2. Oh, well. It isn't like anyone but
        # me has ever seen this code yet
        if self.__version == '0.0.1' or self.__version == '0.0.2':
            self.__logger.debug("Have a version '" + version + "' splice that I can handle")

            source_root_name = self.__PickSourceRootName()

            if self.Validate():
                self.__logger.debug("Merging " + str(chunk_count) + " chunks into '" + source_root_name + "'")
                # OK, we can at least try to merge the pieces
                files_to_merge.sort() # Seems reasonable to require them to be in alphabetical order

                # FIXME: Allow the user to specify a destination file? What about
                # piping to STDOUT?

                with open(source_root_name, "wb") as destination:
                    for file_name in files_to_merge:
                        file_path = os.path.join(self.__working_directory, file_name)
                        #self.__logger.info("# " + file_path)

                        # Note the major distinction here between source and self.__source.
                        # Much ugliness has entered this code!
                        with open(file_path, "rb") as source:
                            while True:
                                bytes = source.read()
                                if not bytes:
                                    break
                                digest.update(bytes)
                                destination.write(bytes)
                actual_checksum = digest.hexdigest()

                if actual_checksum != expected_checksum:
                    # Should probably go ahead and throw an exception here
                    self.__logger.error("Checksums don't match!")
                else:
                    self.__logger.debug("Merge succeeded (checksum: '" + actual_checksum + "')") 
            else:
                self.__logger.error("Wrong chunk count. Expected %d. Have %d" % (chunk_count, count))

    #################################################################
    # Splitting
    #################################################################

    def __PickSourceFile(self):
        ''' Caller is responsible for closing '''
        raise myexceptions.ObsoleteMethod("Splicer should not be doing this")

        if not self.__source_file_name:
            self.__source_file_name = 'STDIN'
            source = sys.stdin
        else:
            source = open(self.__source_file_name, "rb")

        # i.e. Go to end
        source.seek(0, 2)
        self.__source_size = source.tell()
        # and then back to beginning
        source.seek(0)

        return source

    def __PickBaseName(self):
        return os.path.split(self.__source_file_name)[1]
    
    def __CreateDirectory(self, destination_directory):
        # Note that trying to recreate an existing directory will raise
        # exceptions

        if os.path.exists(destination_directory):
            assert False, "Duplicate destination: " + str(destination_directory)

        try:
            os.mkdir(destination_directory)
        except OSError:
            # FIXME: Handle this
            raise
        except WindowsError:
            # Will the presence of this cause issues outside Windows?
            self.__logger.error("Destination directory already exists")
            raise
        
    def __PickChunkDigits(self, memo=[]):
        ''' How many digits do we need to account for all the chunks? '''
        # Since there really isn't anything we can do with this that isn't
        # obnoxious
        if self.__source == sys.stdin:
            return 1

        # Note that memoizing this makes re-using a splicer much more problematic
        if not memo:
            # Horrible way to do this
            chunk_count = self.__source_size / self.__buffer_size
            if self.__source_size % self.__buffer_size != 0:
                # Account for the final fragmentary chunk
                chunk_count += 1

            result = 0

            if chunk_count < 10:
                result = 1
            elif chunk_count < 100:
                result = 2
            elif chunk_count < 1000:
                result = 3
            elif chunk_count < 10000:
                result = 4
            elif chunk_count < 100000:
                result = 5
            else:
                self.__logger.debug( "Source Size: %d BufferSize: %d Chunk Count: %d" % 
                                   (self.__source_size,
                                    self.__buffer_size, chunk_count,))

                # Getting more than 10000 files in a single directory used
                # to be a horribly bad idea in windows. No idea whether that's
                # still true, but it still seems like a bad idea
                assert False, "Adjust buffer size"

            memo.append(result)

        return memo[0]

    def __FileNameFormatString(self):
        "What format string should be used for building the destintion file names?"
        chunk_count = self.__PickChunkDigits()
        return '%s.%0' + str(chunk_count) + 'd.chunk'

    def __PickDestinationFileName(self, destination_directory, count):
        # I really don't want to do this every time. But it isn't like
        # this sucker's CPU-bound
        base_name = self.__PickBaseName()

        # How many digits do we need to accomodate?
        format_string = self.__FileNameFormatString()
    
        # FIXME: Be smarter than this.  Could very well have more than 1000
        # chunks.  Not that hard to figure out. file size / chunk size.
        # But get this working first
        destination_name = format_string % (base_name, count)

        # Finally build the actual file name string
        destination_path = os.path.join(destination_directory, destination_name)

        return destination_path

    def __SaveDetails(self, count, digest, destination_directory):
        ''' How do we fit the chunks back together again? '''

        # Not that this is particularly meaningful without all the chunks
        checksum = digest.hexdigest()

        base_name = self.__PickBaseName()
        destination_name = base_name + '.details'
        destination_path = os.path.join(destination_directory, destination_name)
        with open(destination_path, 'w') as destination:
            destination.write("Version: " + self.__version + '\n')
            destination.write('Chunk Count: ' + str(count) + '\n')
            destination.write('Checksum: ' + checksum + '\n')
            destination.write('BlockSize: ' + str(self.__buffer_size) + '\n')

    def __TryToReadDifficultBlock(self, source, index):
        raise NotImplementedError("What should this do?")
        try:
            source.seek(self.__buffer_size * count)
      
            block = source.read(self.__buffer_size)
            if not block:
#break
                # Actually, this indicates EOF, so we're done.
                pass

        except IOError:
            # And should it really be handled by another, smaller file?
            raise NotImplementedError("What do I want to do here?")
        finally:
            # Is there anything that needs to happen here?
            pass

    def __ReadBlock(self, source, readSize):
        return source.read(readSize)

    def __PossiblyThrowRandomErrorIfDebugging(self):
        if _DEBUG:
            # FIXME: Debug only
            # Except that it seems likely it's needed again
            percentage = random.randrange(0, 100)
            if percentage < 15:
                raise IOError("Random test simulating read failure")

    def __RecursiveRepairBlock(self, source, initial_offset, chunkSize, chunkCount):
        result = []
        source.seek(initial_offset)

        i = 0
        while i < chunkCount:
            try:
                self.__PossiblyThrowRandomErrorIfDebugging()
                buffer = self.__ReadBlock(source, chunkSize)
                result += buffer
            except IOError:
                # Recurse in a smaller chunks
                if chunkSize == 1:
                    # Just give up. Though there are probably better defaults to 
                    # depict flawed sectors
                    self.__logger.error("Byte %d within the source file is not readable")
                    result.append(0)
                else:
                    divisor = 0

                    if chunkSize > 10:
                        divisor = 10
                    else:
                        divisor = 2

                    # Get the first x sub-chunks:
                    sub_chunk_size = chunkSize / divisor
                    offset = initial_offset + chunkSize * i
                    result += self.__RecursiveRepairBlock(source, offset, sub_chunk_size, 2)

                    remainder = chunkSize % divisor
                    if remainder != 0:
                        # and the last sub-chunk:
                        final_offset = offset + (sub_chunk_size*divisor)
                        result += self.__RecursiveRepairBlock(source, final_offset, remainder, 1)
                        
            i += 1

        return result
    
    # Honestly, this deserves its own class
    def __RepairBlock(self, source, count):
        ''' Entry point for repairing one single block. Returns the block as best it can be repaired '''
        # Can't start out this way. Don't actually know where we are in the file
        #offset = source.tell()
        initial_offset = self.__buffer_size * count
        result = self.__RecursiveRepairBlock(source, initial_offset, self.__buffer_size/10, 10)

        source.seek(initial_offset + self.__buffer_size)

        return result

    def __ActualSplitter(self):
        '''
        source = self.__PickSourceFile()
        '''
        destination_directory = self.DestinationDirectory()
        count = 0
        digest = hashlib.sha256()

        try:
            if not os.path.exists(destination_directory):
                self.__CreateDirectory(destination_directory)
            else:
                self.__logger.warn("Using existing directory, in an attempt to restart")
                # FIXME: If the .details file exists in the directory, read it and hope
                # to find out how many files are supposed to be present

            finished = False

            while True:
                destination_path = self.__PickDestinationFileName(destination_directory,
                                                          count)
        
                if not os.path.exists(destination_path):
                    if finished:
                        # This is what we expect to see
                        # (finished, with no "next" file to deal with)
                        # Really should check that size match source's EOF.
                        # Maybe in a future version
                        break
                    if self.__repairing:
                        # it's tempting to do some prompting here. Maybe this
                        # is a sector we're willing to concede is just bad and
                        # skip, while we'd like to try another sector that failed
                        # during the last run further down the line.
                        # This is what I was trying initially, but it was annoying.
                        
                        # OTOH, this is pretty much the perfect opportunity to switch
                        # into a recursive mode, trying to recover smaller chunks.

                        # Should probably enable this option for non-repairing as well.
                        # Or something along these lines, anyway
                        block = self.__RepairBlock(self.__source, count)

                        msg = "Is there enough in there to be worth trying to save?"
                        commit = self.__ui.PromptForYorN(msg)
                        if not commit:
                            # Skip this block
                            count += 1
                            continue
            
                    else:
                        # Standard logic...not particularly worried about I/O failure
                        try:
                            # There are really two very different standpoints from a performance
                            # standpoint. The first time through, there won't be any pre-existing
                            # destination files. In that case, it really doesn't make any sense
                            # to seek between reads.
                            # OTOH, hopefully almost all the pieces were read the first time through.
                            # On the second pass, we should already have the vast majority of chunks
                            # (or we're *really* screwed), so it doesn't make any sense to seek
                            # in source file *unless* there's a block to read
                            # When the seek actually happens is the difference
                            # between the repairing and standard versions. There's no particular
                            # reason for the standard not to build as much of the broken splice
                            # as possible                            

                            block = self.__ReadBlock(self.__source, self.__buffer_size)
                            if not block:
                                # EOF. We're done
                                break
                            if finished:
                                # (No EOF even though the previously read chunk indicated that
                                # it *should* be)
                                # This isn't pretty, but I'm in a hurry.
                                # Best bet is to just delete the file with the incorrect size
                                # and try running this agais
                                # (what this means is that a pre-existing destination file
                                # had an incorrect bufferSize, but it wasn't the final
                                # chunk)
                                assert False, "Last destination file has wrong chunk size"

                            self.__PossiblyThrowRandomErrorIfDebugging()

                        except IOError, e:
                            msg = "Error reading block # %d (%s). Keep trying?\n" % (count, str(e),)
                            response = ui.PromptForYorN(msg)
                            if response:
                                # Skip to the next block
                                count += 1

                                # This is problematic. Don't really have any guarantee
                                # that each read will get bufferSize bytes.
                                # Even though that *is* the behavior I've seen so far.
                                # Technically, I should be keeping a running total of all
                                # the chunk sizes
                                # Worry about it if it ever becomes an issue
                                if not self.__repairing:
                                    # We've already established that we aren't in repairing mode.
                                    # *Very* strong evidence that this method is *way* too long and complicated
                                    # Could probably seek to self.__buffer_size, relative.
                                    # But, after an IOError, who knows where tell() is?
                                    self.__source.seek(count * self.__buffer_size)
                                continue
                            else:
                                break

                    # Save the chunk
                    with open(destination_path, "wb") as destination:
                        destination.write(block)

                else: # already wrote this chunk
                    # Honestly, this is another special-case. Don't want to waste time on this
                    # if I'm just trying to repair existing chunks
                    # Set this to something reasonable
                    bytes = self.__buffer_size

                    # Read the destination file.
                    with open(destination_path, "rb") as destination:
                        block = destination.read(self.__buffer_size)
                        bytes = len(block)
                        if self.__buffer_size != bytes:
                            finished = True

                    if not self.__repairing:
                        # Again, the distinction between the two
                        self.__source.seek(bytes, 1)
          
                # update the checksum
                digest.update(block)

                count  += 1
                if (count % 1024) == 0:
                    self.__ui.UpdateProgress()

        finally:
            # Don't necessarily want this to happen every time. It's worth
            # contemplating
            self.__SaveDetails(count, digest, destination_directory)

            # FIXME: Make this go away. It's only here currently to make the change
            # more obvious in source control history
            #self.__CloseIfSafe(self.__source)

if __name__ == '__main__':
    logging.error ("Use some sort of UI layer, such as Program or the REPL")
    raise NotImplementedError("Not really meant for direct interactivity")
