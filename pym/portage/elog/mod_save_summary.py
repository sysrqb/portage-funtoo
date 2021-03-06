# elog/mod_save_summary.py - elog dispatch module
# Copyright 2006-2011 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import io
import time
import portage
from portage import os
from portage import _encodings
from portage import _unicode_decode
from portage import _unicode_encode
from portage.data import portage_gid, portage_uid
from portage.localization import _
from portage.package.ebuild.prepare_build_dirs import _ensure_log_subdirs
from portage.util import apply_permissions, ensure_dirs, normalize_path

def process(mysettings, key, logentries, fulltext):
	if mysettings.get("PORT_LOGDIR"):
		logdir = normalize_path(mysettings["PORT_LOGDIR"])
	else:
		logdir = os.path.join(os.sep, mysettings["EPREFIX"].lstrip(os.sep),
			"var", "log", "portage")

	if not os.path.isdir(logdir):
		# Only initialize group/mode if the directory doesn't
		# exist, so that we don't override permissions if they
		# were previously set by the administrator.
		# NOTE: These permissions should be compatible with our
		# default logrotate config as discussed in bug 374287.
		logdir_uid = -1
		if portage.data.secpass >= 2:
			logdir_uid = portage_uid
		ensure_dirs(logdir, uid=logdir_uid, gid=portage_gid, mode=0o2770)

	elogdir = os.path.join(logdir, "elog")
	_ensure_log_subdirs(logdir, elogdir)

	# TODO: Locking
	elogfilename = elogdir+"/summary.log"
	elogfile = io.open(_unicode_encode(elogfilename,
		encoding=_encodings['fs'], errors='strict'),
		mode='a', encoding=_encodings['content'], errors='backslashreplace')

	# Copy group permission bits from parent directory.
	elogdir_st = os.stat(elogdir)
	elogdir_gid = elogdir_st.st_gid
	elogdir_grp_mode = 0o060 & elogdir_st.st_mode

	# Copy the uid from the parent directory if we have privileges
	# to do so, for compatibility with our default logrotate
	# config (see bug 378451). With the "su portage portage"
	# directive and logrotate-3.8.0, logrotate's chown call during
	# the compression phase will only succeed if the log file's uid
	# is portage_uid.
	logfile_uid = -1
	if portage.data.secpass >= 2:
		logfile_uid = elogdir_st.st_uid
	apply_permissions(elogfilename, uid=logfile_uid, gid=elogdir_gid,
		mode=elogdir_grp_mode, mask=0)

	time_str = time.strftime("%Y-%m-%d %H:%M:%S %Z",
		time.localtime(time.time()))
	# Avoid potential UnicodeDecodeError later.
	time_str = _unicode_decode(time_str,
		encoding=_encodings['content'], errors='replace')
	elogfile.write(_unicode_decode(
		_(">>> Messages generated by process " +
		"%(pid)d on %(time)s for package %(pkg)s:\n\n") %
		{"pid": os.getpid(), "time": time_str, "pkg": key}))
	elogfile.write(_unicode_decode(fulltext))
	elogfile.write(_unicode_decode("\n"))
	elogfile.close()

	return elogfilename
