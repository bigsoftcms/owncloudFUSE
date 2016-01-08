#!/usr/bin/env python

import errno
import logging
import os
import pwd
from sys import argv, exit
from time import time
import threading

#from fuse import FUSE, Operations, LoggingMixIn, 
import fuse

class Owncloud(fuse.LoggingMixIn, fuse.Operations):
	'''
	Simple owncloud mapper.
	
	'''

	def __init__(self, src, dst, usernameLocation=1, owncloudUser = 'www-data'):
		self.rwlock = threading.Lock()
		self.owncloudUID = pwd.getpwnam(owncloudUser).pw_uid
		self.owncloudGID = pwd.getpwnam(owncloudUser).pw_gid
		self.usernameLocation = usernameLocation
		self.dst = dst
		self.src = src
		self.hideDotFiles = True
		self.specialOwncloudDirs = ['cache', 'files_external']
		self.log.info('startup mirroring %s to %s for user %s' % (src, dst, owncloudUser))

	def isUserRoot(self, path):
		"""call after getPath()"""
		p = os.path.join(path,'.compass')
		if os.path.exists(p):
			return True
		return False

	def getPath(self, path):
		"""fix up path."""
		self.filesHack = False
		self.log.debug('getPath.called: %s' % path)
		#self.log.debug(fuse.fuse_get_context())
		if path.startswith(os.sep):
			path = path[1:]
		p = path.split(os.sep)
		try:
			if p[1] == 'files':
				path = path.replace('/files', '')
				self.filesHack = True
		except IndexError:
			path = path
		ret = os.path.join(self.src, path)
		self.log.debug('getPath returning:%s' % path)
		return ret

	def findRealUser(self, path):
		path = path.replace(self.src, '')
		realUser = path.split(os.sep)
		if len(realUser) < self.usernameLocation:
			# if we don't have a homedir here, then just make root own it.
			self.log.debug("findRealUser: unable to figure out realUser from %s so root will own the file" % (realUser))
			return 0, 0
		realUser = realUser[self.usernameLocation]
		self.log.debug("findRealUser %s: %s" % (path, realUser))
		try:
			realUID = pwd.getpwnam(realUser).pw_uid
			realGID = pwd.getpwnam(realUser).pw_gid
		except KeyError:
			self.log.debug("findRealUser: unable to find %s in password DB so root will own the file" % (realUser))
			return 0, 0
		return realUID, realGID

	def __call__(self, op, path, *args):
		"""wrapper around Owncloud class, that verifies only the owncloudUser can access this copy of the filesystem."""
		ctx = fuse.fuse_get_context()
		if ctx[0] != self.owncloudUID:
			raise fuse.FuseOSError(errno.EACCES)
		return super(Owncloud, self).__call__(op, path, *args)

	# filesystem methods

	def access(self, path, mode):
		"""access"""
		path = self.getPath(path)
		self.log.debug("access:%s %s" % (path, mode))
		if not os.access(path, mode):
			raise fuse.FuseOSError(errno.EACCES)

	def chmod(self, path, mode):
		path = self.getPath(path)
		self.log.debug("chmod(%s, %s)" % (path, mode))
		return os.chmod(path, mode)

	def chown(self, path, uid, gid):
		self.log.debug("called chown(%s, %s, %s)" % (path, uid, gid))
		realUID, realGID = self.findRealUser(path)
		path = self.getPath(path)
		self.log.debug("executing chown(%s, %s, %s)" % (path, realUID, realGID))
		return os.chown(path, realUID, realGID)


	def getattr(self, path, fh=None):
		path = self.getPath(path)
		self.log.debug("getattr: %s" % path)
		st = os.lstat(path)
		ret = dict((key, getattr(st, key)) for key in ('st_atime', 'st_gid',
			'st_mode', 'st_mtime', 'st_size', 'st_uid'))
		ret['st_gid'] = self.owncloudGID
		ret['st_uid'] = self.owncloudUID
		return ret
	
	def readdir(self, path, fh):
		path = self.getPath(path)
		self.log.debug('readdir: %s' % path)
		if self.isUserRoot(path):
			if not self.filesHack:
				ret = ['.', '..', 'files']
				files = os.listdir(path)
				for f in self.specialOwncloudDirs:
					if f in files:
						ret.append(f)
				return ret
		r = os.listdir(path)
		if 'files' in r:
			del r['files']
		if self.hideDotFiles:
			ret = []	
			for f in r:
				if f[:1] == '.':
					continue
				ret.append(f)
			return ret
		return r + ['.', '..']

	def readlink(self, path):
		self.log.debug('readlink: %s' % path)
		path = self.getPath(path)
		return os.path.readlink(path)
	

	getxattr = None
	
	def mkdir(self, path, mode):
		path = self.getPath(path)
		self.log.debug("mkdir %s %s" % (path, mode))
		realUID, realGID = self.findRealUser(path)
		r = os.mkdir(path, mode)
		os.chown(path, realUID, realGID)
		return r
	
	def rmdir(self, path):
		path = self.getPath(path)
		self.log.debug('rmdir %s' % (path))
		return os.rmdir(path)
	
	def statfs(self, path):
		path = self.getPath(path)
		self.log.debug("statfs: %s" % path)
		stv = os.statvfs(path)
		d = dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree', 'f_blocks',
			 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag', 'f_frsize', 'f_namemax'))
		return d


	def rename(self, old, new):
		old = self.getPath(old)
		new = self.getPath(new)
		self.log.debug('rename %s to %s' % (old, new))
		return os.rename(old, new)

	def symlink(self, target, source):
		target = self.getPath(target)
		source = self.getPath(source)
		self.log.debug('symlink %s to %s' % (source, target))
		return os.symlink(source, target)

	
	def link(self, target, name):
		target = self.getPath(target)
		name = self.getPath(name)
		self.log.debug('link %s -> %s' % (target, name))
		return os.link(target, name)

	def unlink(self, path):
		path = self.getPath(path)
		self.log.debug('unlink %s' % (path))
		return os.unlink(path)
		
	def utimens(self, path, times=None):
		path = self.getPath(path)
		self.log.debug('utimens %s' % (path))
		return os.utime(path, times)

	# file methods

	def open(self, path, flags):
		path = self.getPath(path)
		self.log.debug("open %s %s" % (path, flags))
		return os.open(path, flags)
	
	def create(self, path, mode):
		path = self.getPath(path)
		realUID, realGID = self.findRealUser(path)
		self.log.debug("create: %s %s" % (path, mode))
		ret = os.open(path, os.O_WRONLY | os.O_CREAT, mode)
		os.chown(path, realUID, realGID)
		return ret

	def read(self, path, size, offset, fh):
		path = self.getPath(path)
		self.log.debug("read (%s, offset: %s, size: %s)" % ( path, offset, size))
        	with self.rwlock:
			with open(path, 'rb') as fd:
				fd.seek(offset, os.SEEK_SET)
            			return fd.read(size)

	def write(self, path, data, offset, fh):
		path = self.getPath(path)
		self.log.debug('write %s' % (path))
		with self.rwlock:
			with open(path, 'wb') as fd:
				fd.seek(offset, 0)
				fd.write(data)
				return len(data)
	
	def truncate(self, path, length, fh=None):
		path = self.getPath(path)
		self.log.debug('truncate %s to %s' % (path, length))
		with open(path, 'r+') as f:
			f.truncate(length)

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO,
		format='%(name)s %(levelname)s %(message)s',
		)
	if len(argv) != 3:
		print('usage: %s <src> <dst>' % argv[0])
		exit(1)
	src = argv[1]
	dst = argv[2]
	fs = fuse.FUSE(Owncloud(src, dst), dst, foreground=True, nothreads=True, allow_other=True, noexec=True)
