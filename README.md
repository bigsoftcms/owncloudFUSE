# owncloudFUSE
User level filesystem(FUSE) to export /home to owncloud. (aka bindfs mounted mirror with permission handling)


The goal here is to export /home to Owncloud(https://owncloud.org/).  This has
been tested against owncloud stable (8.2).

It works by creating a new filesystem of /home to a new path (say /tmp/home).
`/tmp/home` will become readable and writable by the owncloud www user (by default `www-data`).
This means you are handing over every file in `/home` to owncloud to read and
write.  This code does some magic to make that work better. it exports
the /tmp/home to *look* like an owncloud data/<user> directory, (i.e. all files
under <user>/files/ and <user>/cache available).  It also will silently behind
the scenes for new files, fix up the permissions in /home to be owned by the
actual user (by treatiing the <username> as the user to chown.


## INSTALL:

* Startup owncloudFUSE as root (see examples/owncloudFUSE.conf for a supervisord startup script).
* Tell ownlcoud how to find the new /tmp/home folder for owncloud I do this:
	In owncloud LDAP settings change Advanced/Special Attributes `User Home Folder Naming Rule` to homeDirectory
	my LDAP server is set to return homeDirectory as a full path to
	/tmp/home/<USERNAME>.  This forces owncloud to look in /tmp/home/<username>
	for the user's data directory in owncloud instead of
	owncloud/data/<username>.
* install the updateoc script and edit it (give it a list of users to sync) (examples/updateoc) to `/usr/local/bin` tell crontab to tell owncloud to sync local changes to owncloud every X minutes (here 5):
	` */5 * * * * /usr/local/bin/updateoc`
   NOTE: This needs to become a watchdog (https://github.com/gorakhargosh/watchdog) type script to monitor /home changes.

## STATUS:

This is currently implemented in our development environment.  We plan to bring this to production eventually. Development of this code base is intended to happen here in public.

## SECURITY:

This has severe security issues. You are handing /home to owncloud to be
read/writable by the webserver user, essentially trusting owncloud to keep
/home safe and secure.  You also have to run owncloudFUSE as ROOT, and
trust that this code is safe. Currently no security audit has been performed.

I do a little to mitigate this:

* while FUSE allow_other, is set, I check the context, so that only the owncloud user (www-data) can play in `/tmp/home`.
* I try to keep owncloudFUSE small and simple to reduce complexity/bugs.
