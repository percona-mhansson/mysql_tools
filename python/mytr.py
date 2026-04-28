"""Runs mysql-test-run from the root of the git clone"""

from shutil import which
import argparse
import logging
import os
import subprocess
import sys

import mysql

MTR = "mysql-test-run.pl"


def main():
    """All the work"""

    parser = argparse.ArgumentParser(description="Starts mysqld in the background.")

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=1,
        help="verbose",
    )

    parser.add_argument(
        "-H",
        "--build-home",
        default=mysql.Defaults.BUILD_HOME,
        help="home directory for mysql builds (default: %(default)s)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="don't actually start mysqld, only print how it would have started and then exit",
    )

    build_specific_args = parser.add_mutually_exclusive_group()

    build_specific_args.add_argument(
        "-B",
        "--build-dir",
        help="lets you specify the build directory directly, instead of inferring it from the "
        "build type (see --build-type)",
    )

    parser.add_argument(
        "-C",
        "--workdir",
        default=os.getcwd(),
        help="change to DIR before doing anything else",
    )

    args, mtr_args = parser.parse_known_args()

    mysql.setup_logging(args.verbose)

    logging.debug(f"mtr args: {" ".join(mtr_args)}")

    build = mysql.Build(args.workdir, args.build_dir, mysql.Defaults.BUILD_TYPE, args.build_home)

    cwd = os.path.abspath(f"{build.build_dir}/mysql-test")

    exe = f"{build.build_dir}/mysql-test/{MTR}"
    mtr_args = [exe] + mtr_args

    if args.dry_run:
        logging.info(f"Would have run {MTR} like this: {" ".join(mtr_args)}")
        sys.exit(0)

    logging.debug(f"Running {MTR} like this: {" ".join(mtr_args)}")

    if which("colordiff"):
        with subprocess.Popen(
            mtr_args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ) as mtr_proc:
            with subprocess.Popen(["colordiff"], stdin=mtr_proc.stdout) as cd:
                # Allow p to receive a SIGPIPE if colordiff exits.
                mtr_proc.stdout.close()
                cd.wait()
                rc = cd.returncode
    else:
        with subprocess.Popen(mtr_args, cwd=cwd) as mtr_proc:
            mtr_proc.wait()
            rc = mtr_proc.returncode

    sys.exit(rc)


if __name__ == "__main__":
    main()
