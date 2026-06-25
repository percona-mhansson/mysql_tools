"""Starts the MySQL server"""

import logging
import os
import signal
import subprocess
import sys

from abc import abstractmethod

import psutil

from daemon import Daemon


def setup_logging(verbosity):
    """Configure logging based on verbosity level."""
    if verbosity >= 2:
        level = logging.DEBUG
    elif verbosity >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(level=level, format="%(message)s")


# pylint: disable=too-few-public-methods
class Defaults:
    """Should probably be loaded from a file"""

    BUILD_HOME = "build"
    BUILD_TYPE = "debug"
    DATABASE = "mysql"
    DATADIR = "mydata"
    LOWER_CASE_TABLE_NAMES = 1
    PORT = 11211
    USER = "root"


class Build:
    """Represents the specifics of how a binary was built"""

    def __init__(
        self, workdir, build_dir=None, build_type=None, build_home=Defaults.BUILD_HOME
    ):
        self.workdir = workdir
        self._build_type = build_type

        logging.debug("workdir %s", self.workdir)
        logging.debug("build_dir %s", build_dir)
        logging.debug("build_type %s", build_type)
        logging.debug("build_home %s", build_home)

        if build_dir:
            self.build_dir = os.path.abspath(build_dir)
            logging.debug(
                "--build-dir specified, setting build directory to %s", self.build_dir
            )
            return

        if self._build_type:
            self.build_dir = f"{workdir}/{build_home}/{self._build_type}"
            logging.debug(
                "--build-type %s specified, setting build directory to %s",
                self._build_type,
                self.build_dir,
            )
            return

        self._build_type = Defaults.BUILD_TYPE
        self.build_dir = f"{workdir}/{build_home}/{self._build_type}"
        logging.debug(
            "Defaulting build type to %s and build directory to %s",
            self._build_type,
            self.build_dir,
        )

    def get_build_type(self):
        """Determines the build type"""
        if not self._build_type:
            self._build_type = search_cmake_cache(
                self.build_dir, "CMAKE_BUILD_TYPE:STRING"
            )
            logging.debug("inferring build type to %s", self._build_type)

        return self._build_type


class Binary:
    """Base class for all mysql executables (client, server)"""

    def __init__(self, build):
        self.build = build
        self.version = read_version(build.build_dir)

    @abstractmethod
    def get_binary_dir(self):
        """The concrete binary's directory given version and build directory."""

    def make_socket_path(self):
        """Generates a socket file name from the version and build type."""
        major_version = self.version["MYSQL_VERSION_MAJOR"]
        minor_version = self.version["MYSQL_VERSION_MINOR"]

        return f"/tmp/mysql-{major_version}.{minor_version}-{self.build.get_build_type()}.sock"


class Server(Binary):
    """Represents the server binary"""

    def __init__(self, datadir, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datadir = datadir
        self.executable = f"{self.get_binary_dir()}/mysqld"
        self.mysqld_args = [
            f"--datadir={datadir}",
        ]
        if self.version["MYSQL_VERSION_MAJOR"] <= 5:
            self.mysqld_args.append(
                f"--lc-messages-dir={self.build.build_dir}/share/english"
            )

    def get_binary_dir(self):
        """The binary directory given version and build directory."""
        if self.version["MYSQL_VERSION_MAJOR"] < 8:
            return f"{self.build.build_dir}/sql"
        return f"{self.build.build_dir}/runtime_output_directory"

    def create_database(self, args: dict, mysqld_args: list):
        """Creates the database."""

        subprocess_args = (
            [
                self.executable,
                f"--datadir={self.datadir}",
                "--initialize-insecure",
            ]
            + self.mysqld_args
            + mysqld_args
        )

        logging.info("Creating database in %s", self.datadir)

        if args.dry_run:
            logging.info(
                "Would have run mysqld like this: %s", " ".join(subprocess_args)
            )
            return

        logging.info("Running mysqld like this: %s", " ".join(subprocess_args))

        try:
            subprocess.run(subprocess_args, check=True)
        except subprocess.CalledProcessError as err:
            logging.critical("Failed to create database: %s", err)
            sys.exit(1)

    def start(self, args, mysqld_args):
        """Starts the mysqld process."""

        logging.debug("starting mysqld(%s, %s, %s)", self.executable, args, mysqld_args)
        subprocess_args = [self.executable] + self.mysqld_args + mysqld_args

        if args.dry_run:
            logging.info(
                "Would have run mysqld like this: %s", " ".join(subprocess_args)
            )
            return
        logging.info("Running mysqld like this: %s", " ".join(subprocess_args))

        if args.verbose >= 1:
            daemon = Daemon(
                self.executable, subprocess_args, stdout=sys.stdout, stderr=sys.stderr
            )
        else:
            devnull = open(os.devnull, "w", encoding=ascii)
            daemon = Daemon(
                self.executable, subprocess_args, stdout=devnull, stderr=devnull
            )
        daemon.daemonize()

    def get_pid(self):
        """Returns the pid of the mysqld process"""
        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                if (
                    proc.info["cmdline"] is not None
                    and self.executable in proc.info["cmdline"]
                ):
                    return proc.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        logging.debug("No process found for %s", self.executable)
        return None

    def stop(self):
        """Signals the server and waits until the process has stopped"""
        pid = self.get_pid()
        if pid is None:
            logging.critical("Failed to find running mysqld")
            return

        logging.debug("Killing mysql with pid %s", pid)

        os.kill(pid, signal.SIGTERM)
        try:
            psutil.Process(pid).wait()
        except psutil.NoSuchProcess:
            logging.critical("Failed to find running mysqld")


class Client(Binary):
    """Represents the client binary"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executable = f"{self.get_binary_dir()}/mysql"

    def get_binary_dir(self):
        """The executable directory given version and build directory."""
        if self.version["MYSQL_VERSION_MAJOR"] < 8:
            return f"{self.build.build_dir}/client"
        return f"{self.build.build_dir}/runtime_output_directory"

    def start(self, args, client_args):
        """Starts the MySQL client."""

        subprocess_args = [self.executable] + client_args

        if args.dry_run:
            logging.info(
                "Would have run mysql like this: %s", " ".join(subprocess_args)
            )
            return

        logging.info("Running mysql like this: %s", " ".join(subprocess_args))

        os.execv(self.executable, subprocess_args)


def determine_build_specifics(args) -> (str, str):
    """This is the complex part of these scripts. Basically, there are two
    modes of working. Either you specify the build type, in which case mysql
    gets built in `build/<build type>` under the source director. The other
    option is to specify the full build path (doesn't have to be absolute
    though)"""

    if args.build_dir:
        build_dir = args.build_dir
        logging.debug("--build-dir specified, setting build directory to %s", build_dir)
        return None, build_dir

    if args.build_type:
        build_type = args.build_type
        build_dir = f"{args.workdir}/build/{build_type}"
        logging.debug(
            "--build-type %s specified, setting build directory to %s",
            build_type,
            build_dir,
        )
        return build_type, build_dir

    build_type = Defaults.BUILD_TYPE
    build_dir = f"{args.workdir}/build/{build_type}"
    logging.debug(
        "Neither --build-type nor --build-dir specified, defaulting build type to "
        "%s and build directory to %s",
        build_type,
        build_dir,
    )
    return build_type, build_dir


def search_cmake_cache(build_dir, variable):
    """Searches the cmake cache"""
    search_str = f"{variable}="
    with open(f"{build_dir}/CMakeCache.txt", "r", encoding="ascii") as cmake_cache:
        for line in cmake_cache:
            if line[: len(search_str)] == search_str:
                return line[len(search_str) :].strip().lower()
    return None


def read_version(build_dir):
    """Picks up the MySQL version from the build"""
    version_string = search_cmake_cache(build_dir, "MYSQL_BASE_VERSION:INTERNAL")
    version_list = version_string.split(".")
    return {
        "MYSQL_VERSION_MAJOR": int(version_list[0]),
        "MYSQL_VERSION_MINOR": int(version_list[1]),
    }


def read_version_file(workdir):
    """Parses the version file to a dict."""
    version = {}
    found_version_file_name = None

    for version_file_name in ["MYSQL_VERSION", "VERSION"]:
        if os.path.isfile(f"{workdir}/{version_file_name}"):
            logging.debug("Found version file %s", version_file_name)
            found_version_file_name = version_file_name
            break

    if found_version_file_name is None:
        logging.critical(
            "Warning, can't find a version file in %s!",
            workdir,
        )

    try:
        with open(
            f"{workdir}/{found_version_file_name}", "r", encoding="ascii"
        ) as version_file:
            for line in version_file:
                data = line.split("=")
                value = data[1].strip()
                version[data[0]] = int(value) if value.isdigit() else value
    except FileNotFoundError:
        logging.critical(
            "Warning, failed to open %s in %s!",
            found_version_file_name,
            workdir,
        )
        raise
    return version
