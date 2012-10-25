#! /usr/bin/env python

# This really isn't the appropriate parent class
class VersionError(IOError):
  pass

# Again, poor choice of parent class
class ObsoleteMethod(NotImplementedError):
    pass
