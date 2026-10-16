from typing import Optional
from colorama import Fore, Style, init
from contextlib import contextmanager
import datetime
import time
import shutil
import re

init()


class Logger:
    levels = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.BLUE,
        "SUCCESS": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
    }

    def __init__(
        self,
        tree: Optional[list] = None,
        levelColorScheme: Optional[dict] = None,
        variables: Optional[dict] = None,
        devider: Optional[str] = None,
    ):
        self.tree: Optional[list] = tree if tree is not None else None
        self.colorScheme: dict = dict(self.levels)
        if levelColorScheme:
            self.colorScheme.update(levelColorScheme)
        self.variables: Optional[dict] = variables if variables is not None else None
        self.devider: str = devider if devider is not None else "-"
        self._indentLevel: int = 0

    def _stripAnsi(self, text: str) -> str:
        return re.sub(r"\x1b\[[0-9;]*m", "", text)

    def _buildLogs(
        self,
        message: str,
        level: str = "INFO",
        useBuiltIns: bool = True,
        groupLevel: Optional[int] = None,
    ):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        message = str(message)
        level = str(level)

        levelColored = (
            f"{self.colorScheme.get(level.upper(), Fore.WHITE)}"
            f"{level.upper()}{Style.RESET_ALL}"
        )

        builtIns = {
            "{message}": message,
            "{time}": timestamp,
            "{level}": levelColored,
            "{resetStyle}": Style.RESET_ALL,
            "{black}": Fore.BLACK,
            "{red}": Fore.RED,
            "{green}": Fore.GREEN,
            "{yellow}": Fore.YELLOW,
            "{blue}": Fore.BLUE,
            "{magenta}": Fore.MAGENTA,
            "{cyan}": Fore.CYAN,
            "{white}": Fore.WHITE,
            "{bold}": Style.BRIGHT,
        }

        replacements = {}
        if useBuiltIns:
            replacements.update(builtIns)
        if self.variables:
            replacements.update({str(k): str(v) for k, v in self.variables.items()})

        parts = []
        if self.tree:
            for branch in self.tree:
                result = str(branch)
                for key, value in replacements.items():
                    result = result.replace(key, value)
                parts.append(result)
            output = " ".join(parts)
        else:
            output = message

        if groupLevel is not None:
            if groupLevel < 0:
                raise ValueError("Invalid value for 'groupLevel': Expected number >= 0")
            indent = "  " * groupLevel
        else:
            indent = "  " * self._indentLevel

        return indent + output

    def setGroupLevel(self, groupLevel: int = 0) -> None:
        if groupLevel < 0:
            raise ValueError("Invalid value for 'groupLevel': Expected number >= 0")
        self._indentLevel = groupLevel

    def console(
        self,
        message: str,
        level: str = "INFO",
        useBuiltIns: bool = True,
        groupLevel: Optional[int] = None,
    ):
        """Send a log to the terminal with the log and the log level.

        builtIns = {
            "{message}": message,
            "{time}": time,
            "{level}": levelColored,
            "{resetStyle}": Style.RESET_ALL,
            "{black}": Fore.BLACK,
            "{red}": Fore.RED,
            "{blue}": Fore.BLUE,
            "{bold}": Style.BRIGHT,
        }
        user-defined variables overwrite builtins.
        """
        output: str = self._buildLogs(message, level, useBuiltIns, groupLevel)
        print(output + Style.RESET_ALL)

    def save(
        self,
        message: str,
        level: str = "INFO",
        logFile: str = "app.log",
        useBuiltIns: bool = True,
        groupLevel: Optional[int] = None,
    ):
        output: str = self._stripAnsi(
            self._buildLogs(message, level, useBuiltIns, groupLevel)
        )
        with open(logFile, "a", encoding="utf-8") as filename:
            filename.write(f"{output}\n")

    def log(
        self,
        message: str,
        level: str = "INFO",
        logFile: str = "app.log",
        useBuiltIns: bool = True,
        groupLevel: Optional[int] = None,
    ):
        if groupLevel is not None:
            self.console(message, level, useBuiltIns, groupLevel=groupLevel)
            self.save(message, level, logFile, useBuiltIns, groupLevel)
        else:
            self.console(message, level, useBuiltIns)
            self.save(message, level, logFile, useBuiltIns)

    def devide(self) -> None:
        cmdSize = shutil.get_terminal_size(fallback=(80, 24))
        line = self.devider * cmdSize.columns
        print(line)

    def divide(self) -> None:
        """Correctly spelled alias for devide()."""
        self.devide()

    @contextmanager
    def timer(
        self, label: str, level: str = "DEBUG", warnAfter: Optional[float] = None
    ):
        start: float = time.perf_counter()
        try:
            yield
        finally:
            elapsed: float = time.perf_counter() - start
            ms: float = elapsed * 1000
            thresholdLevel: str = (
                "WARNING" if (warnAfter is not None and ms > warnAfter) else level
            )
            self.console(f"{label} took {ms}ms", level=thresholdLevel)