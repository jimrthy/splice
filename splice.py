#! /usr/bin/env python

''' Split/combine big files '''

# Example usage:
# Create an archive:
# ./splice.py -f /usr/bin/whatever.zip
# If you're having I/O issues:
# python ./splice.py -r -f /usr/bin/whatever.zip
# Put the pieces back together
# (actually, I think this sample may be horrible misleading)
# ./splice.py -m -d zip.split -f zip.details

from __future__ import with_statement

import hashlib, logging, os, sys
logging.basicConfig(level=logging.DEBUG)

# This really isn't the appropriate parent class
class VersionError(IOError):
  pass

class Splicer:
  # FIXME: Really should have two seperate classes for merging and splitting
  # instead of handling it this way
  def __init__(self):

    # Just pick a default
    self._mode = "split"

    # Working restartably is really more complicated and slower.
    # Besides, it was the original default.
    # Currently only really applies to splitting
    self._restartable = False

    # Try to play unix-nice
    # can't do this when splitting.  No good way to tell what the output file
    # name(s) should be.  Well, think about it

    #self._source = sys.stdin
    self._sourceFileName = None

    self._version = "0.0.2"

    # Seems like a safe default. Play with it
    # Works great for small files. Not so much for big ones
    self._bufferSize = 1
    
    # Start with a default that kind of makes sense for piping from STDIN
    self.__source_size = sys.maxint

    self.logger = logging.getLogger("splice.Splicer")

    self._working_directory = '.'

  def Operate(self):
    ''' Effectively, this is main() '''
    if self._mode == "merge":
      self._Merge()
    elif self._mode == "split":
      if not self._restartable:
        self._Split()
      else:
        def DefaultErrorHandler(count):
            response = raw_input("Error reading block # " + str(count) + ". Keep trying?")
            return response.trim()[0].lower() == 'y'

        self._RestartableSplit(DefaultErrorHandler)
    else:
      raise NotImplementedError("Unknown mode: " + str(self._mode))

  #########################################################
  # Some more or less useful getters/setters boilerplate
  #########################################################

  def SetMergeMode(self):
    self._mode = "merge"

  def SetRepairSplice(self, mode):
    self._restartable = mode

  def SetSourceFileName(self, name):
    self._sourceFileName = name

  def Version(self):
    return self._version

  def BufferSize(self, size=None):
    if size is not None:
      self._bufferSize = int(size)

    return self._bufferSize

  def WorkingDirectory(self, pwd=None):
    if pwd is not None:
      self._working_directory = pwd

    return self._working_directory

  def _Merge(self):
    ''' Restore a splice to a single file '''
    # Suppose I could pipe the details from STDIN, but it just doesn't seem to
    # make any sense.  But what about sending them to STDOUT?
    if not self._sourceFileName:
      raise NotImplementedError("Look for a .details file in the pwd")

    self.logger.debug("Pulling details out of the directory file '" + self._sourceFileName + "'")

    # the files that might be interesting
    list_of_file_names = os.listdir(self._working_directory)
    #self.logger.debug("Considering " + str(list_of_file_names))

    directory_file_name = os.path.join(self._working_directory, self._sourceFileName)
    with open(directory_file_name, "r") as directory_file:
      # FIXME: This really should be a YAML file
      # Checksum:
      # Version:
      version = directory_file.readline().split(' ')[1].strip()

      # Chunk Count:
      chunk_count = int(directory_file.readline().split(' ')[2].strip())

      # stash this for later
      expected_checksum = directory_file.readline().split(' ')[1].strip()

      # chunk size and hashing algorithm
      digest = None

      if version == '0.0.1':
        # TODO: open a .chunk file and base this on that instead
        # Better: just use a restartable buffer and let the chunks be any
        # size they like.
        # That's really for future improvements, though. All 0.0.1 chunks
        # were hard-coded to be 1024 bytes long
        # FIXME: That isn't true. It had a -b command line argument, even
        # if I don't ever remember using it
        self._bufferSize = 1024;

        digest = hashlib.md5()
      elif version == '0.0.2':
        self._bufferSize = int(directory_file.readline().split(' ')[1].strip())
        digest = hashlib.sha256sum()
      else:
        raise VersionError("Unknown version")

    # *really* tempting to just use magic strings everywhere for version numbers
    # Are they really any less confusing than trying to deal with a variable?
    # Would named constants really gain me anything in this case?
    if version == self._version or version == '0.0.1':
      self.logger.debug("Have a version '" + version + "' splice")
      # has to be a built-in to just glob this

      # discard the ".details"--really should make the UI simpler. Just go
      # into the folder, run splice.py -m, and it finds the .details file and
      # merges everything.  Do that in the next version
      source_root_name = self._sourceFileName[:-8]

      # Cheese-ball work-around for windows:
      if source_root_name[:2] == ".\\":
        source_root_name = source_root_name[2:]

      self.logger.debug("Combining into a file named '" + source_root_name + "'")

      # Make sure all the chunks are there
      count = 0
      files_to_merge = []
      for file_name in list_of_file_names:
        #self.logger.debug("Maybe counting a file named '" + str(file_name) + "'")

        name_pieces = file_name.split('.')
        # ignore the '.###.chunk' part.  Do it this way so I can vary the
        # length of the string that specifies the count
        #self.logger.debug(str(name_pieces))
        if name_pieces[-1] == 'chunk':
          root_name = '.'.join(name_pieces[:-2])
          if root_name == source_root_name:
            files_to_merge.append(file_name)
            count += 1
          else:
            self.logger.debug("Not part of this split")
        else:
          self.logger.debug(file_name + " : Not a chunk")

      if count == chunk_count:
        self.logger.debug("Merging " + str(count) + " chunks into '" + source_root_name + "'")
        # OK, we can at least try to merge the pieces
        files_to_merge.sort() # Seems reasonable to require them to be in alphabetical order

        # FIXME: Allow the user to specify a destination file? What about
        # piping to STDOUT?

        with open(source_root_name, "wb") as destination:
          for file_name in files_to_merge:
            file_path = os.path.join(self._working_directory, file_name)
            #self.logger.info("# " + file_path)
            with open(file_path, "rb") as source:
              while True:
                bytes = source.read()
                if not bytes:
                  break
                digest.update(bytes)
                destination.write(bytes)
        actual_checksum = digest.hexdigest()

        if actual_checksum != expected_checksum:
          self.logger.warning("Checksums don't match!")
        else:
          self.logger.debug("Merge succeeded (checksum: '" + actual_checksum + "')") 
      else:
        self.logger.error("Wrong chunk count. Expected %d. Have %d" % (chunk_count, count))
    elif version == '0.0.1':
      # This should really be easy to fix. The only real difference is
      # that 0.0.1 used md5 for the checksum
      self.logger.error("Currently incompatible with version 0.0.1 chunks")
      raise VersionError("Currently backwards incompatible")
    else:
      raise VersionError("Not smart enough to deal with a version '" + version + "' split")

  def __PickSourceFile(self):
    ''' Caller is responsible for closing '''
    if not self._sourceFileName:
      self._sourceFileName = 'STDIN'
      source = sys.stdin
    else:
      source = open(self._sourceFileName, "rb")

      source.seek(0, 2)
      self.__source_size = source.tell()
      source.seek(0)

    return source

  def __PickBaseName(self):
    return os.path.split(self._sourceFileName)[1]
    
  def __PickDestinationDirectory(self):
    # Just go with the file name
    # Note that this depends on the source file being in a separate
    # directory
    base_name = self.__PickBaseName()

    # Somewhere to put the pieces
    destination_directory = base_name + '.split'

    return destination_directory

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
      self.logger.error("Destination directory already exists")
      raise

  def __CloseIfSafe(self, source):
    if self._sourceFileName != 'STDIN':
      # Shouldn't hurt to call this on an object that's already closed
      source.close()

  def __PickChunkDigits(self):
    ''' How many digits do we need to account for all the chunks? '''
    # Really should memoize this
    # Horrible way to do this
    chunk_count = self.__source_size / self._bufferSize
    if self.__source_size % self._bufferSize != 0:
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
      self.logger.debug( "Source Size: %d BufferSize: %d Chunk Count: %d" % (self.__source_size,
        self._bufferSize, chunk_count,))

      # Getting more than 10000 files in a single directory used
      # to be a horribly bad idea in windows. No idea whether that's
      # still true, but it still seems like a bad idea
      assert False, "Adjust buffer size"

    return result

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
    destination_path = os.path.join(destination_directory, destination_name)

    return destination_path

  def __SaveDetails(self, count, digest, destination_directory):
    # or something similar
    checksum = digest.hexdigest()

    base_name = self.__PickBaseName()
    destination_name = base_name + '.details'
    destination_path = os.path.join(destination_directory, destination_name)
    with open(destination_path, 'w') as destination:
      destination.write("Version: " + self._version + '\n')
      destination.write('Chunk Count: ' + str(count) + '\n')
      destination.write('Checksum: ' + checksum + '\n')
      destination.write('BlockSize: ' + str(self._bufferSize) + '\n')

  def __TryToReadDifficultBlock(self, source, index):
    try:
      source.seek(self._bufferSize * count)

      
      block = source.read(self._bufferSize)
      if not block:
#break
        pass

    finally:
      # And should it really be handled by another, smaller file?
      raise NotImplementedError("What do I want to do here?")

  def _RestartableSplit(self, error_handler):
    source = self.__PickSourceFile()
    destination_directory = self.__PickDestinationDirectory()
    count = 0
    digest = hashlib.sha256()

    try:
      if not os.path.exists(destination_directory):
        self.__CreateDirectory(destination_directory)
      else:
        self.logger.info("Using existing directory, in an attempt to restart")
        # FIXME: If the .details file exists in the directory, read it and hope
        # to find out how many files are supposed to be present

      finished = False

      while True:
        destination_path = self.__PickDestinationFileName(destination_directory,
                                                          count)
        
        if not os.path.exists(destination_path):
          # FIXME: refactor this particular pattern out to its own method
          '''
          assert False, "Obviously don't want this enabled on a first pass"
          '''
          msg = "Missing file # %d. Try to replace?" % (count,)
          s = raw_input(msg)
          if s[0].lower() != 'y':
            continue
          
          # Read another chunk from the source, just like with standard _Split
          try:
            # There are really two very different standpoints from a performance
            # standpoint. The first time through, there won't be any pre-existing
            # destination files. In that case, it really doesn't make any sense
            # to seek between reads.
            # OTOH, hopefully almost all the pieces were read the first time through.
            # On the second pass, we should already have the vast majority of chunks
            # (or we're *really* screwed), so it doesn't make any sense to seek
            # in source file *unless* there's a block to read
            # This should really be controlled by a command-line
            # parameter. Or something along those lines.
            # For now, just use duct tape...comment out whichever assert/seek makes
            # sense

            # FIXME: Actually, when the seek happens should be the difference
            # between the restartable and standard versions. There's no particular
            # reason for the standard not to try to build the broken splice
            '''
            assert False, "Enable a seek depending on where it makes most sense"
            '''
            source.seek(self._bufferSize * count)

            block = source.read(self._bufferSize)
            if not block:
              break
            if finished:
              # This isn't pretty, but I'm in a hurry.
              # Best bet is to just delete the file with the incorrect size
              # and try running this agais
              # (what this means is that a pre-existing destination file
              # had an incorrect bufferSize, but it wasn't the final
              # chunk)
              assert False, "Last destination file has wrong chunk size"
          except IOError:
            if errorHandler(count):
              # Skip to the next block
              count += 1

              # This is problematic. Don't really have any guarantee
              # that each read will get bufferSize bytes.
              # Worry about it if it ever becomes an issue
              source.seek(count * self._bufferSize)
              continue
            else:
              break

          # Save the chunk
          with open(destination_path, "wb") as destination:
            destination.write(block)

        else: # already wrote this chunk
          # Read the destination file.
          bytes = self._bufferSize

          with open(destination_path, "rb") as destination:
            block = destination.read(self._bufferSize)
            bytes = len(block)
            if self._bufferSize != bytes:
              finished = True

          # Seek forward in the source file?
          # Or wait until there's another chunk to read from there?
          # Not optimal, but simple
          # See the comment above in the read section about when you'd
          # want to use which code pegment for a seek
          # It's cheesy, but pragmatic
          '''
          assert False, "Comment out one or the other."
          source.seek(bytes, 1)
          '''
          
        # update the checksum
        digest.update(block)

        count  += 1
        if (count % 1024) == 0:
          sys.stdout.write ("#")

    finally:
      # Don't necessarily want this to happen every time. It's worth
      # contemplating
      self.__SaveDetails(count, digest, destination_directory)

      self.__CloseIfSafe(source)

  def _Split(self):
    # FIXME: These either need to be turned into member variables or
    # assigned as a tuple by a helper method, just to reduce duplicate
    # code
    source = self.__PickSourceFile()
    destination_directory = self.__PickDestinationDirectory()

    # Keep track of which chunk we're on
    count = 0

    # Track the checksum
    digest = hashlib.sha256()

    try:
      self.__CreateDirectory(destination_directory)

      while True:
        #self.logger.info("Writing chunk # " + str(count))

        block = source.read(self._bufferSize)
        if not block:
          break

        # update the checksum
        digest.update(block)

        # output the chunk
        destination_path = self.__PickDestinationFileName(destination_directory,
                                                          count)

        with open(destination_path, "wb") as destination:
          destination.write(block)

        # Remember to switch to the next file
        count += 1

        if (count % 1024) == 0:
          print("#",)
        
    finally:
      self.__CloseIfSafe(source)

      # Save the details
      # This could happen after closing source. But that could
      # choke and die too
      self.__SaveDetails(count, digest, destination_directory)

  def dispose(self):
    # Just a sanity check, really
    try:
      self._source.close()
    except:
      # All kinds of things could go wrong here. Maybe document them later, if
      # they start biting me
      pass

if __name__ == '__main__':
  logging.error ("Use some sort of UI layer, such as Program or the REPL")
  raise NotImplementedError("Not really meant for direct interactivity")
