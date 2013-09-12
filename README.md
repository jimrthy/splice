splice
======

Sometimes you need to temporarily split a file into multiple pieces

Overview
========

Started years ago because I needed to copy some massive file (it might
have been an entire 10 MiB, hard as that might be to believe) over
sneakernet.

Brought back to life a few years ago because I had a SSD die, and I
wanted to try to save as much as I could of a VHD on it with bad
sectors. (The backup was a week old!)

Usage
=====

Honestly, it's been a while since I touched this myself. The
basic idea is

splice.py -s file-to-split

will create a directory of file chunks and a descriptor file that
describes putting them back together.

splice.py -m merge-descriptor

I don't remember off the top of my head whether the merge-descriptor
is the directory with all the chunks or the path to the descriptor
file. I suspect it should be the latter, but I don't have the
spare minutes it would take just now to look it up.

Status
======

This project's mostly "done." And not really all that useful in
the age of the internet. So don't expect a lot of activity.

It isn't even a particularly interesting project, for that matter,
but it has proved useful on occasion.

License
=======

I'm releasing this as AGPL, though I haven't updated the individual
files yet.

