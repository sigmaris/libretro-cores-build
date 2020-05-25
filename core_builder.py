#!/usr/bin/env python3
import argparse
from datetime import datetime
from email import utils as email_utils
import fnmatch
import logging
import os
import shlex
import string
import subprocess

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)8s] %(message)s")

DEBIAN_REPOS = (
    "2048-debian",
    "3dengine-debian",
    "4do-debian",
    "81-debian",
    "atari800-debian",
    "beetle-bsnes-debian",
    "beetle-gba-debian",
    "beetle-lynx-debian",
    "beetle-ngp-debian",
    "beetle-pce-fast-debian",
    "beetle-pcfx-debian",
    "beetle-psx-debian",
    "beetle-saturn-debian",
    "beetle-supergrafx-debian",
    "beetle-vb-debian",
    "beetle-wswan-debian",
    "blueMSX-debian",
    "bsnes-debian",
    "bsnes-mercury-debian",
    "citra-debian",
    "Craft-debian",
    # "crawl-ref-debian",  # complicated packaging
    "CrocoDS-debian",
    "desmume-debian",
    "Dinothawr-debian",
    "dolphin-debian",
    "dosbox-debian",
    # "fbalpha-debian",  # May have been renamed to fbneo? or just gone
    "fbalpha2012-debian",
    "fbalpha2012_cps1-debian",
    "fbalpha2012_cps2-debian",
    "fbalpha2012_cps3-debian",
    "fceumm-debian",
    "fmsx-debian",
    "freej2me-debian",
    "fs-uae-debian",
    "fuse-debian",
    "gambatte-debian",
    "Genesis-Plus-GX-debian",
    "gme-debian",
    "gpsp-debian",
    "gw-debian",
    "handy-debian",
    "hatari-debian",
    "lutro-debian",
    "mame-debian",
    "mame2003-debian",
    "mame2010-debian",
    # "mame2014-debian",  # was renamed to "mame2015"
    "mame2016-debian",
    "melonDS-debian",
    "meteor-debian",
    # "mgba-libretro-debian",  # no display_version in info
    "mrboom-debian",
    # "mupen64plus-debian",  # may be renamed to "mupen64plus-next"
    "nestopia-debian",
    "NP2-debian",
    "NP2kai-debian",
    "nxengine-debian",
    "o2em-debian",
    "parallel-n64-debian",
    "pcem-debian",
    "pcsx1-debian",
    "pcsx_rearmed-debian",
    "PicoDrive-debian",
    "PocketCDG-debian",
    "PokeMini-debian",
    "ppsspp-debian",
    "prboom-debian",
    "prosystem-debian",
    # "PSP1-debian",  # info file not found?
    "px68k-debian",
    "QuickNES_Core-debian",
    "redream-debian",
    # "reicast-debian",  # info file not found, renamed to flycast?
    "SameBoy-debian",
    "scummvm-debian",
    "snes9x-debian",
    "snes9x2005-debian",
    "snes9x2010-debian",
    "stella-debian",
    "tgbdual-debian",
    "tyrquake-debian",
    "vba-next-debian",
    "vbam-debian",
    "vecx-debian",
    # "vice3.0-debian",  # not sure which of several info files to use
    "virtualjaguar-debian",
    "xrick-debian",
    "yabause-debian",
)
OVERRIDE_REPOS = {
    "mgba-libretro-debian": "https://github.com/mgba-emu/mgba.git"
}
OVERRIDE_CORE_SONAMES = {
    'bsnes-mercury':     'bsnes_mercury_balanced',
    'beetle-bsnes':      'mednafen_snes',
    'beetle-gba':        'mednafen_gba',
    'beetle-lynx':       'mednafen_lynx',
    'beetle-ngp':        'mednafen_ngp',
    'beetle-pce-fast':   'mednafen_pce_fast',
    'beetle-pcfx':       'mednafen_pcfx',
    'beetle-psx':        'mednafen_psx',
    'beetle-saturn':     'mednafen_saturn',
    'beetle-supergrafx': 'mednafen_supergrafx',
    'beetle-vb':         'mednafen_vb',
    'beetle-wswan':      'mednafen_wswan',
    'fs-uae':            'fsuae',
    'Genesis-Plus-GX':   'genesis_plus_gx',
    'mgba-libretro':     'mgba',
    'NP2':               'nekop2',
    'parallel-n64':      'parallel_n64',
    'QuickNES_Core':     'quicknes',
    'stella':            'stella2014',
    'vba-next':          'vba_next',
    'pcsx-rearmed':      'pcsx_rearmed',
}
META_REPO = "https://github.com/libretro/libretro-super.git"
LIBRETRO_GIT_URL_BASE = "git://git.launchpad.net/~libretro/libretro/+git"
CHANGELOG_TEMPLATE = """{package} ({version}) {distributions}; urgency=low

  * Automated build of Git commit {git_hash}

 -- Hugh Cole-Baker <sigmaris@gmail.com>  {date}

"""


def build_one_core(meta_dir, main_name, debian_name, distro, build_number=1):
    if debian_name in OVERRIDE_REPOS:
        main_repo = OVERRIDE_REPOS[debian_name]
    else:
        main_repo = "/".join((LIBRETRO_GIT_URL_BASE, main_name))

    if main_name in OVERRIDE_CORE_SONAMES:
        meta_name = OVERRIDE_CORE_SONAMES[main_name]
    else:
        meta_name = main_name.lower()
    main_version = get_meta_version(meta_dir, meta_name)
    logging.info("Core %s at version %s", main_name, main_version)

    # checkout main repo
    logging.info("Checking out %s", main_name)
    proc = subprocess.Popen(
        ("git", "clone", "--recurse-submodules", main_repo, main_name),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    stdout, _ = proc.communicate()
    if proc.returncode != 0:
        return (False, f"{main_name} checkout", stdout, None)

    # checkout debian repo into main repo debian directory
    main_dir = os.path.join(os.getcwd(), main_name)
    debian_repo = "/".join((LIBRETRO_GIT_URL_BASE, debian_name))
    logging.info("Checking out %s", debian_name)
    proc = subprocess.Popen(
        ("git", "clone", debian_repo, "debian"),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=main_dir
    )
    stdout, _ = proc.communicate()
    if proc.returncode != 0:
        return (False, f"{debian_name} checkout", stdout, None)

    debian_dir = os.path.join(main_dir, "debian")
    if os.path.isdir(os.path.join(debian_dir, "debian")):
        logging.warning("%s has nested debian directory!", debian_name)
        os.rename(debian_dir, "nested-debian")
        os.rename(os.path.join(os.getcwd(), main_name, "nested-debian", "debian"), debian_dir)
    proc = subprocess.Popen(
        ("git", "log", "-1", "--format=%h %H %cd", "--date=rfc2822"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=main_dir
    )
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        return (False, f"Git log of {main_name}", stdout, stderr)
    short_hash, long_hash, rfc2822_date = stdout.decode().split(" ", 2)
    ts = email_utils.mktime_tz(email_utils.parsedate_tz(rfc2822_date))
    git_dt = datetime.utcfromtimestamp(ts)
    core_version = main_version.lower().lstrip(string.ascii_letters)
    if not core_version:
        core_version = "0.0.1"
    core_version = core_version.split()[0]
    pkg_version = f"{core_version}+git{git_dt:%Y%m%d.%H%M}-{build_number}"

    with open(os.path.join(debian_dir, "changelog"), "r") as changelog_in:
        chlog_existing = changelog_in.read()
        pkg_name = chlog_existing.split()[0]
        chlog_head = CHANGELOG_TEMPLATE.format(
            package=pkg_name, version=pkg_version, distributions=distro,
            git_hash=long_hash, date=rfc2822_date
        )
    with open(os.path.join(debian_dir, "changelog"), "w") as changelog_out:
        changelog_out.write(chlog_head)
        changelog_out.write(chlog_existing)

    # Build the package!
    logging.info("*** %s build deps ***", pkg_name)
    subprocess.call(("dpkg-checkbuilddeps",), cwd=main_dir)
    logging.info("*** %s build deps end ***", pkg_name)

    logging.info("Installing build deps for %s", pkg_name)
    proc = subprocess.Popen(
        ("mk-build-deps", "--install", "--tool",
         "apt-get -y -o Debug::pkgProblemResolver=yes --no-install-recommends"),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=main_dir
    )
    stdout, _ = proc.communicate()
    if proc.returncode != 0:
        return (False, f"Installing build deps for {pkg_name}", stdout, None)

    logging.info("Building Debian package %s", pkg_name)
    proc = subprocess.Popen(
        ("dpkg-buildpackage", "-us", "-uc", "-b", "--jobs=auto"),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=main_dir
    )
    stdout, _ = proc.communicate()
    if proc.returncode != 0:
        return (False, f"Building package {pkg_name}", stdout, None)

    return (True, None, None, None)


def get_meta_version(meta_dir, meta_name):
    with open(os.path.join(meta_dir, "dist", "info", f"{meta_name}_libretro.info"), "r") as infile:
        lexer = shlex.shlex(infile, posix=True)
        tok = lexer.get_token()
        while tok is not None:
            if tok == "display_version":
                if lexer.get_token() != "=":
                    raise Exception(f"Got unexpected token parsing display_version for {meta_name}")
                return lexer.get_token()
            tok = lexer.get_token()
        raise Exception(f"display_version for {meta_name} not found")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--include', help='Only include cores matching these patterns')
    parser.add_argument('--exclude', help='Exclude cores matching these patterns')
    parser.add_argument('distro', help='Distribution codename')
    args = parser.parse_args()
    includes = args.include.split(',') if args.include else ["*"]
    excludes = args.exclude.split(',') if args.exclude else []
    failed_builds = {}

    subprocess.check_call(("git", "clone", META_REPO))
    meta_dir = os.path.join(os.getcwd(), "libretro-super")
    for index, debian_name in enumerate(DEBIAN_REPOS):
        main_name = debian_name.rsplit("-", 1)[0]

        if (
            not any(fnmatch.fnmatch(main_name, pattern) for pattern in includes)
            or any(fnmatch.fnmatch(main_name, pattern) for pattern in excludes)
        ):
            continue

        logging.info("Building %s ...", main_name)
        success, stage, stdout, stderr = build_one_core(meta_dir, main_name, debian_name, args.distro)
        if not success:
            logging.error("Failed to build %s", main_name)
            failed_builds[stage] = (stdout, stderr)
        else:
            logging.info("Successfully built %s", main_name)

    if failed_builds:
        logging.error("*** Failed builds ***")
        for key, (out, stderr) in failed_builds.items():
            logging.error("Failure in stage: %s", key)
            for line in out.decode('utf-8', errors='ignore').splitlines():
                logging.debug("out: %s", line)
            if stderr:
                for line in stderr.decode('utf-8', errors='ignore').splitlines():
                    logging.debug("stderr: %s", line)


if __name__ == "__main__":
    main()
