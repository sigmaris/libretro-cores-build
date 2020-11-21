#!/usr/bin/env python3
import argparse
import ctypes
from datetime import datetime
from email import utils as email_utils
import fnmatch
import glob
import logging
import os
import shlex
import string
import subprocess

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)8s] %(message)s")

PROJECT_REPOS = (
    "2048",
    "3dengine",
    "4do",
    "81",
    "atari800",
    "beetle-bsnes",
    "beetle-gba",
    "beetle-lynx",
    "beetle-ngp",
    "beetle-pce-fast",
    "beetle-pcfx",
    "beetle-psx",
    "beetle-saturn",
    "beetle-supergrafx",
    "beetle-vb",
    "beetle-wswan",
    "blueMSX",
    "bsnes",
    "bsnes-mercury",
    "citra",
    "Craft",
    # "crawl-ref",  # complicated packaging
    "CrocoDS",
    "desmume",
    "Dinothawr",
    "dolphin",
    "dosbox",
    "fbneo",
    "fbalpha2012",
    "fbalpha2012_cps1",
    "fbalpha2012_cps2",
    "fbalpha2012_cps3",
    "fceumm",
    "fmsx",
    "freej2me",
    "fs-uae",
    "fuse",
    "gambatte",
    "Genesis-Plus-GX",
    "gme",
    "gpsp",
    "gw",
    "handy",
    "hatari",
    "lutro",
    "mame",
    "mame2003",
    "mame2010",
    # "mame2014",  # was renamed to "mame2015"
    "mame2016",
    "melonDS",
    "meteor",
    # "mgba-libretro",  # no display_version in info
    "mrboom",
    # "mupen64plus",  # may be renamed to "mupen64plus-next"
    "nestopia",
    "NP2",
    "NP2kai",
    "nxengine",
    "o2em",
    "parallel-n64",
    "pcem",
    "pcsx1",
    "pcsx_rearmed",
    "PicoDrive",
    "PocketCDG",
    "PokeMini",
    "ppsspp",
    "prboom",
    "prosystem",
    # "PSP1",  # info file not found?
    "px68k",
    "QuickNES_Core",
    "redream",
    # "reicast",  # info file not found, renamed to flycast?
    "SameBoy",
    "scummvm",
    "snes9x",
    "snes9x2005",
    "snes9x2010",
    "stella",
    "tgbdual",
    "tyrquake",
    "vba-next",
    "vbam",
    "vecx",
    # "vice3.0",  # not sure which of several info files to use
    "virtualjaguar",
    "xrick",
    "yabause",
)
OVERRIDE_REPOS = {
    "mgba-libretro": "https://github.com/mgba-emu/mgba.git",
    "fbneo": "https://github.com/libretro/FBNeo.git"
}
OVERRIDE_DEBIAN_REPOS = {
    "beetle-saturn": "https://github.com/sigmaris/beetle-saturn-debian.git",
    "bsnes": "https://github.com/sigmaris/bsnes2014-debian.git",
    "fbneo": "https://github.com/sigmaris/fbneo-debian.git",
    "NP2kai": "https://github.com/sigmaris/NP2kai-debian.git",
    "parallel-n64": "https://github.com/sigmaris/parallel-n64-debian.git",
    "pcsx_rearmed": "https://github.com/sigmaris/pcsx_rearmed-debian.git",
    "ppsspp": "https://github.com/sigmaris/ppsspp-debian.git",
}
OVERRIDE_CORE_SONAMES = {
    'bsnes':             'bsnes2014_balanced',
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
    'redream':           'retrodream',
}
META_REPO = "https://github.com/libretro/libretro-super.git"
LIBRETRO_GIT_URL_BASE = "git://git.launchpad.net/~libretro/libretro/+git"
CHANGELOG_TEMPLATE = """{package} ({version}) {distributions}; urgency=low

  * Automated build of Git commit {git_hash}

 -- Hugh Cole-Baker <sigmaris@gmail.com>  {date}

"""


class RetroSystemInfo(ctypes.Structure):
    """ struct retro_system_type """
    _fields_ = [
        ('library_name', ctypes.c_char_p),
        ('library_version', ctypes.c_char_p),
        ('valid_extensions', ctypes.c_char_p),
        ('need_fullpath', ctypes.c_bool),
        ('block_extract', ctypes.c_bool)
    ]


def build_one_core(meta_dir, main_name, debian_name, distro, build_number):
    if main_name in OVERRIDE_REPOS:
        main_repo = OVERRIDE_REPOS[main_name]
    else:
        main_repo = "/".join((LIBRETRO_GIT_URL_BASE, main_name))

    if main_name in OVERRIDE_CORE_SONAMES:
        meta_name = OVERRIDE_CORE_SONAMES[main_name]
    else:
        meta_name = main_name.lower()
    meta_version = get_meta_version(meta_dir, meta_name)
    logging.info("Core %s at version %s", main_name, meta_version)

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

    if main_name in OVERRIDE_DEBIAN_REPOS:
        debian_repo = OVERRIDE_DEBIAN_REPOS[main_name]
    else:
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
    pkg_version = deb_version(meta_version, git_dt, short_hash, build_number)

    patches_dir = os.path.join(os.path.dirname(__file__), "patches")
    core_patch_dir = os.path.join(patches_dir, main_name)
    if os.path.isdir(core_patch_dir):
        for patch in os.listdir(core_patch_dir):
            subprocess.check_call(
                ("git", "am", os.path.join(core_patch_dir, patch)),
                cwd=main_dir
            )

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
    subprocess.call(("dpkg-checkbuilddeps",), cwd=main_dir)

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

    packages = identify_packages(debian_dir)
    return fixup_versions(packages, meta_version, git_dt, short_hash, build_number)


def deb_version(meta_version, git_dt, short_hash, build_number):
    core_version = meta_version.lower().lstrip(string.ascii_letters).strip(string.punctuation)
    if not core_version:
        core_version = "0.0.1"
    core_version = core_version.split()[0]

    return f"{core_version}-r{git_dt:%Y%m%d.%H%M}-{short_hash}-{build_number}"


def identify_packages(debian_dir):
    packages = []
    with open(os.path.join(debian_dir, 'control')) as controlfile:
        for line in controlfile:
            if line.strip().startswith("Package: "):
                packages.append(line.split(':')[1].strip())
    return packages


def fixup_versions(packages, meta_version, git_dt, short_hash, build_number):
    pkg_version = deb_version(meta_version, git_dt, short_hash, build_number)

    for package in packages:
        pkg_file = f"{package}_{pkg_version}_arm64.deb"
        if os.path.isfile(pkg_file):
            unpack_dir = f"{package}-unpack"

            proc = subprocess.Popen(
                ("dpkg-deb", "-R", pkg_file, unpack_dir),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            stdout, _ = proc.communicate()
            if proc.returncode != 0:
                return (False, f"Unpacking package {package}", stdout, None)

            try:
                so_file = next(glob.iglob(
                    os.path.join(unpack_dir, "usr/lib/aarch64-linux-gnu/libretro", "*_libretro.so")
                ))

                lib = ctypes.cdll.LoadLibrary(so_file)
            except Exception as exc:
                logging.exception(f"Exception finding or opening .so file: {exc}")
                continue

            retro_get_system_info = lib.retro_get_system_info
            retro_get_system_info.argtypes = [ctypes.POINTER(RetroSystemInfo)]
            retro_get_system_info.restype = None

            system_info = RetroSystemInfo()
            retro_get_system_info(ctypes.byref(system_info))
            if system_info.library_version is None:
                logging.warning("%s has NULL library_version", so_file)
                continue

            real_version = str(system_info.library_version, 'utf-8')

            if real_version.strip().endswith(short_hash):
                real_version = real_version.strip()[:-len(short_hash)].strip()

            real_pkg_version = deb_version(real_version, git_dt, short_hash, build_number)

            if pkg_version != real_pkg_version:
                logging.info("%s version fixup %s -> %s", package, pkg_version, real_pkg_version)
                version_change(package, unpack_dir, pkg_version, real_pkg_version)

                dbgsym_pkg_file = f"{package}-dbgsym_{pkg_version}_arm64.deb"
                dbg_unpack_dir = f"{package}-dbgsym-unpack"

                if os.path.isfile(dbgsym_pkg_file):

                    proc = subprocess.Popen(
                        ("dpkg-deb", "-R", dbgsym_pkg_file, dbg_unpack_dir),
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    )
                    stdout, _ = proc.communicate()
                    if proc.returncode != 0:
                        return (False, f"Unpacking package {package}-dbgsym", stdout, None)

                    version_change(f"{package}-dbgsym", dbg_unpack_dir, pkg_version, real_pkg_version)

    return (True, None, None, None)


def version_change(package, unpack_dir, old_version, new_version):
    repack_dir = f"{package}-repack"

    with open(os.path.join(unpack_dir, "DEBIAN", "control"), "r") as control_in:
        control_content = control_in.read()
        control_modified_lines = []
        for line in control_content.splitlines(keepends=True):
            if line.strip() == f"Version: {old_version}":
                control_modified_lines.append(f"Version: {new_version}\n")
            else:
                control_modified_lines.append(line)
    with open(os.path.join(unpack_dir, "DEBIAN", "control"), "w") as control_out:
        control_out.write("".join(control_modified_lines))

    os.mkdir(repack_dir)
    proc = subprocess.Popen(
        ("dpkg-deb", "-b", unpack_dir, repack_dir),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    stdout, _ = proc.communicate()
    if proc.returncode != 0:
        return (False, f"Repacking package {package}", stdout, None)

    new_pkg_file = f"{package}_{new_version}_arm64.deb"
    os.rename(os.path.join(repack_dir, new_pkg_file), new_pkg_file)
    os.remove(f"{package}_{old_version}_arm64.deb")


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
    parser.add_argument('--build-number', default=1, type=int, help='.deb package build number')
    parser.add_argument('distro', help='Distribution codename')
    args = parser.parse_args()
    includes = args.include.split(',') if args.include else ["*"]
    excludes = args.exclude.split(',') if args.exclude else []
    failed_builds = {}

    subprocess.check_call(("git", "clone", META_REPO))
    meta_dir = os.path.join(os.getcwd(), "libretro-super")
    for index, main_name in enumerate(PROJECT_REPOS):
        debian_name = f"{main_name}-debian"

        if (
            not any(fnmatch.fnmatch(main_name, pattern) for pattern in includes)
            or any(fnmatch.fnmatch(main_name, pattern) for pattern in excludes)
        ):
            continue

        logging.info("Building %s ...", main_name)
        success, stage, stdout, stderr = build_one_core(meta_dir, main_name, debian_name, args.distro, args.build_number)
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
