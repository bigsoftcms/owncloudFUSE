import os
def getPath(path):
	"""fix up path."""
	#self.log.debug('getPath.called: %s' % path)
	if path.startswith(os.sep):
		path = path[1:]
	p = path.split(os.sep)
	if len(p) > 0:
		if p[1] == 'files':
			path = path.replace('files/','')
	return path

print getPath('/craig/files/blah')
assert getPath('/craig/files/blah') == 'craig/blah'

