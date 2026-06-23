"""Starts the MySQL server"""

import argparse
import logging
import os
import pathlib
import sys

import mysql


class _Verbosity(argparse.Action):
    """Keeps a single integer: -v adds 1, -q subtracts 1."""

    def __call__(self, parser, namespace, values, option_string=None):
        current = getattr(namespace, self.dest)
        print(f"self {self}")
        print(f"nejmspejs {namespace}")
        print(f"kurrent {current}")
        if not current:
            current = self.default
        setattr(namespace, self.dest, current + self.const)


class ExpandPath(argparse.Action):
    """Because mysqld has this annoying habit of not expanding ~"""

    def __init__(self, *args, **kwargs):
        argparse.Action.__init__(self, *args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, option_string.replace("--", ""), values.expanduser())


def make_parser():
    """Sets up the complete commandline parser"""

    mixin_parser = argparse.ArgumentParser(add_help=False)
    build_specific_args = mixin_parser.add_mutually_exclusive_group()

    build_specific_args.add_argument(
        "-H",
        "--build-home",
        default=mysql.Defaults.BUILD_HOME,
        help="home directory for mysql builds (default: %(default)s)",
    )

    build_specific_args.add_argument(
        "-B",
        "--build-dir",
        help="lets you specify the build directory directly, instead of inferring it from the "
        "build type (see --build-type)",
    )

    build_specific_args.add_argument(
        "-b",
        "--build-type",
        help="assumes that you have built mysql in a directory named "
        "`build/<build type>` in the current directory. You can specify an "
        "arbitrary build directory using --build-dir",
    )

    mixin_parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="debug this script",
    )

    mixin_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="don't actually start mysqld, only print how it would have started and then exit",
    )

    mixin_parser.add_argument(
        "-q",
        action=_Verbosity,
        nargs=0,
        const=-1,
        dest="verbose",
        help="decrease verbosity (repeatable)",
    )

    mixin_parser.add_argument(
        "-v",
        action=_Verbosity,
        nargs=0,
        const=1,
        default=1,
        dest="verbose",
        help="increase verbosity (repeatable)",
    )

    mixin_parser.add_argument(
        "-C",
        "--workdir",
        default=os.getcwd(),
        help="change to DIR before doing anything else",
    )

    mixin_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Answer every question with 'yes'",
    )

    parser = argparse.ArgumentParser(
        description="Manages a mysqld server/client/regression test built from source.",
        parents=[mixin_parser],
    )

    subparsers = parser.add_subparsers(
        title="subcommands", description="valid subcommands", help="additional help"
    )

    server_parser = subparsers.add_parser(
        "server", description="Starts mysqld in the background.", parents=[mixin_parser]
    )
    server_parser.set_defaults(func=handle_server)

    mysqld_args = server_parser.add_argument_group(
        "mysqld options", "Passed verbatim to mysqld."
    )

    # All arguments added here must be manually added to mysqld_args
    mysqld_args.add_argument(
        "--datadir",
        type=pathlib.Path,
        action=ExpandPath,
        help="passed to mysqld, but expands the `~' character",
    )
    mysqld_args.add_argument(
        "--lower-case-table-names",
        type=int,
        default=mysql.Defaults.LOWER_CASE_TABLE_NAMES,
    )
    mysqld_args.add_argument("--no-defaults", action="store_true")
    mysqld_args.add_argument("--port", type=int, default=mysql.Defaults.PORT)
    mysqld_args.add_argument("--socket", type=str)

    server_parser.add_argument(
        "--create",
        action="store_true",
        help="Creates a database before starting.",
    )

    server_parser.add_argument(
        "--stop",
        action="store_true",
        help="Stops this mysqld.",
    )

    server_parser.add_argument(
        "--get-pid",
        action="store_true",
        help="Prints this mysqld's pid .",
    )

    return parser


def main():
    """Guts of the script"""
    parser = make_parser()
    args, mysqld_args = parser.parse_known_args()
    print(f"args {args}")

    # Workaround because default arguments values don't work in parent parsers
    if not args.verbose:
        setattr(args, "verbose", 1)

    mysql.setup_logging(args.verbose)
    build = mysql.Build(args.workdir, args.build_dir, args.build_type, args.build_home)
    args.func(args, mysqld_args, build)


def get_data_dir(args):
    """Determines the data directory"""
    if args.datadir:
        if os.path.isabs(args.datadir):
            datadir = args.datadir
        else:
            datadir = os.path.abspath(f"{args.datadir}")
    else:
        datadir = f"{args.workdir}/{mysql.Defaults.DATADIR}"

    if not os.path.isabs(datadir):
        datadir = os.path.abspath(datadir)

    return datadir


def handle_server(args, mysqld_args, build):

    datadir = get_data_dir(args)
    os.makedirs(datadir, exist_ok=True)
    print(f"build { build}")

    try:
        server = mysql.Server(datadir, build)
    except FileNotFoundError as fnfe:
        print(f"Error: Failed to find file {fnfe.filename}.")
        exit(1)

    if args.get_pid:
        pid = server.get_pid()
        if pid is None:
            logging.critical("Failed to find running mysqld", file=sys.stderr)
            sys.exit(1)
        print(pid)
        sys.exit(0)

    if args.stop:
        server.stop()
        sys.exit(0)

    mysqld_args += [
        f"--lower_case_table_names={args.lower_case_table_names}",
        f"--port={args.port}",
    ]

    if args.no_defaults:
        mysqld_args += ["--no-defaults"]

    socket = args.socket if args.socket else server.make_socket_path()

    mysqld_args += [f"--socket={socket}"]

    build_type = build.get_build_type()

    if build_type and build_type.lower() == "debug":
        mysqld_args += ["--gdb"]

    lockfile = f"{socket}.lock"
    if not args.dry_run and os.path.isfile(lockfile):
        if args.yes:
            os.remove(lockfile)
        else:
            answer = input(f"Found lock file {lockfile}. Delete? [y/n/Q]: ")
            if answer.lower().strip() == "y":
                os.remove(lockfile)
            elif answer.lower().strip() == "q" or answer == "":
                sys.exit(0)

    if args.create:
        server.create_database(args, mysqld_args)

    server.start(args, mysqld_args)


if __name__ == "__main__":
    main()
