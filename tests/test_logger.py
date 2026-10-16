"""
test_blog.py — Tests for the Logger class in blog.py

Run with:
    python -m unittest test_blog.py -v
or:
    python test_blog.py
"""

import os
import re
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from io import StringIO

from colorama import Fore, Style, init

from beautylog import Logger

init(autoreset=False)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


class TestLevelColorScheme(unittest.TestCase):
    """levelColorScheme should MERGE with defaults, not replace them."""

    def test_defaults_preserved_when_no_custom_scheme(self):
        logger = Logger()
        self.assertEqual(logger.colorScheme["INFO"], Fore.BLUE)
        self.assertEqual(logger.colorScheme["ERROR"], Fore.RED)
        self.assertEqual(logger.colorScheme["DEBUG"], Fore.CYAN)

    def test_custom_scheme_merges_with_defaults(self):
        logger = Logger(levelColorScheme={"INFO": Fore.MAGENTA})
        # Overridden
        self.assertEqual(logger.colorScheme["INFO"], Fore.MAGENTA)
        # Defaults still present
        self.assertEqual(logger.colorScheme["ERROR"], Fore.RED)
        self.assertEqual(logger.colorScheme["WARNING"], Fore.YELLOW)
        self.assertEqual(logger.colorScheme["DEBUG"], Fore.CYAN)

    def test_custom_scheme_can_add_new_levels(self):
        logger = Logger(levelColorScheme={"TRACE": Fore.LIGHTBLACK_EX})
        self.assertEqual(logger.colorScheme["TRACE"], Fore.LIGHTBLACK_EX)
        self.assertEqual(logger.colorScheme["INFO"], Fore.BLUE)

    def test_class_level_dict_not_mutated(self):
        original = dict(Logger.levels)
        Logger(levelColorScheme={"INFO": Fore.MAGENTA, "TRACE": Fore.WHITE})
        self.assertEqual(Logger.levels, original)


class TestVariables(unittest.TestCase):
    """variables should MERGE with builtIns and override duplicates."""

    def test_user_variable_replaces_builtin(self):
        logger = Logger(
            tree=["{time} {level} {message}"],
            variables={"{time}": "FAKE_TIME"},
        )
        out = logger._buildLogs("hello", "INFO")
        plain = strip_ansi(out)
        self.assertIn("FAKE_TIME", plain)
        self.assertNotRegex(plain, r"\d{2}:\d{2}:\d{2}")

    def test_user_variable_adds_new_key(self):
        logger = Logger(
            tree=["{custom} {message}"],
            variables={"{custom}": "CUSTOM_VALUE"},
        )
        out = logger._buildLogs("hi", "INFO")
        self.assertIn("CUSTOM_VALUE", out)
        self.assertIn("hi", out)

    def test_user_variable_overrides_message_placeholder(self):
        logger = Logger(
            tree=["prefix {message} suffix"],
            variables={"{message}": "OVERRIDDEN"},
        )
        out = logger._buildLogs("original", "INFO")
        self.assertIn("OVERRIDDEN", out)
        self.assertNotIn("original", out)

    def test_builtins_disabled_still_applies_user_vars(self):
        logger = Logger(
            tree=["{message} {custom}"],
            variables={"{custom}": "USER"},
        )
        out = logger._buildLogs("msg", "INFO", useBuiltIns=False)
        # {message} is a builtin placeholder -> should NOT be substituted
        self.assertIn("{message}", out)
        self.assertIn("USER", out)


class TestGroupLevel(unittest.TestCase):
    def test_set_group_level(self):
        logger = Logger()
        logger.setGroupLevel(2)
        out = logger._buildLogs("hello")
        self.assertTrue(out.startswith("    hello"))

    def test_negative_group_level_raises(self):
        logger = Logger()
        with self.assertRaises(ValueError):
            logger.setGroupLevel(-1)
        with self.assertRaises(ValueError):
            logger._buildLogs("hi", groupLevel=-1)

    def test_explicit_group_level_overrides_indent_level(self):
        logger = Logger()
        logger.setGroupLevel(3)
        out = logger._buildLogs("hi", groupLevel=1)
        self.assertTrue(out.startswith("  hi"))
        self.assertFalse(out.startswith("      hi"))

    def test_group_level_zero_is_respected(self):
        logger = Logger()
        logger.setGroupLevel(3)
        out = logger._buildLogs("hi", groupLevel=0)
        self.assertEqual(out, "hi")


class TestBuildLogs(unittest.TestCase):
    def test_default_message_only(self):
        logger = Logger()
        self.assertEqual(logger._buildLogs("hello"), "hello")

    def test_tree_is_joined_with_space(self):
        logger = Logger(tree=["[A]", "{message}"])
        out = logger._buildLogs("body")
        self.assertEqual(out, "[A] body")

    def test_level_appears_uppercased(self):
        logger = Logger(tree=["{level} {message}"])
        out = logger._buildLogs("hi", level="info")
        self.assertIn("INFO", strip_ansi(out))

    def test_time_is_replaced(self):
        logger = Logger(tree=["{time}"])
        out = logger._buildLogs("ignored")
        self.assertRegex(out, r"\d{2}:\d{2}:\d{2}")

    def test_message_is_str_coerced(self):
        logger = Logger()
        self.assertEqual(logger._buildLogs(12345), "12345")

    def test_non_string_tree_branches_are_coerced(self):
        logger = Logger(tree=[1, "{message}"])
        self.assertEqual(logger._buildLogs("x"), "1 x")


class TestConsoleOutput(unittest.TestCase):
    def test_console_prints_with_reset(self):
        logger = Logger()
        buf = StringIO()
        with redirect_stdout(buf):
            logger.console("hello")
        out = buf.getvalue()
        self.assertIn("hello", strip_ansi(out))
        self.assertTrue(out.rstrip("\n").endswith(Style.RESET_ALL))

    def test_console_respects_group_level(self):
        logger = Logger()
        buf = StringIO()
        with redirect_stdout(buf):
            logger.console("hi", groupLevel=2)
        self.assertTrue(strip_ansi(buf.getvalue()).startswith("    hi"))


class TestSaveAndLog(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.logfile = os.path.join(self.tmpdir, "test.log")

    def tearDown(self):
        if os.path.exists(self.logfile):
            os.remove(self.logfile)
        os.rmdir(self.tmpdir)

    def test_save_strips_ansi(self):
        logger = Logger(tree=["{level}", "{message}"])
        logger.save("hello", level="INFO", logFile=self.logfile)
        with open(self.logfile, encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("\x1b[", content)
        self.assertIn("INFO", content)
        self.assertIn("hello", content)

    def test_save_appends(self):
        logger = Logger()
        logger.save("first", logFile=self.logfile)
        logger.save("second", logFile=self.logfile)
        with open(self.logfile, encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertEqual(len(lines), 2)

    def test_save_uses_utf8(self):
        logger = Logger()
        logger.save("héllo → 世界", logFile=self.logfile)
        with open(self.logfile, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("héllo → 世界", content)

    def test_log_writes_to_both_stdout_and_file(self):
        logger = Logger()
        buf = StringIO()
        with redirect_stdout(buf):
            logger.log("both", logFile=self.logfile, groupLevel=1)
        stdout_out = strip_ansi(buf.getvalue())
        with open(self.logfile, encoding="utf-8") as f:
            file_out = f.read()

        self.assertIn("both", stdout_out)
        self.assertIn("both", file_out)
        # groupLevel=1 should have been applied to both
        self.assertTrue(stdout_out.startswith("  both"))
        self.assertTrue(file_out.startswith("  both"))

    def test_log_with_group_level_zero_applies_indent(self):
        """Regression: groupLevel=0 must not be treated as 'unset'."""
        logger = Logger()
        logger.setGroupLevel(3)  # would normally indent by 3
        buf = StringIO()
        with redirect_stdout(buf):
            logger.log("flat", logFile=self.logfile, groupLevel=0)
        stdout_out = strip_ansi(buf.getvalue())
        self.assertEqual(stdout_out.strip(), "flat")
        self.assertFalse(stdout_out.startswith("  "))


class TestDevide(unittest.TestCase):
    def test_devide_prints_line(self):
        logger = Logger(devider="=")
        buf = StringIO()
        with redirect_stdout(buf):
            logger.devide()
        out = buf.getvalue().strip()
        self.assertGreater(len(out), 0)
        self.assertEqual(set(out), {"="})

    def test_divide_alias(self):
        logger = Logger(devider="#")
        buf = StringIO()
        with redirect_stdout(buf):
            logger.divide()
        self.assertGreater(len(buf.getvalue().strip()), 0)


class TestTimer(unittest.TestCase):
    def test_timer_logs_at_given_level(self):
        logger = Logger(tree=["{level} {message}"])
        buf = StringIO()
        with redirect_stdout(buf):
            with logger.timer("work", level="DEBUG"):
                time.sleep(0.01)
        out = strip_ansi(buf.getvalue())
        self.assertIn("work took", out)
        self.assertIn("DEBUG", out)

    def test_timer_escalates_to_warning_when_threshold_exceeded(self):
        logger = Logger(tree=["{level} {message}"])
        buf = StringIO()
        with redirect_stdout(buf):
            with logger.timer("slow", level="DEBUG", warnAfter=0.001):
                time.sleep(0.01)
        out = strip_ansi(buf.getvalue())
        self.assertIn("WARNING", out)
        self.assertNotIn("DEBUG", out)

    def test_timer_warn_after_zero_still_escalates(self):
        """Regression: warnAfter=0 must be treated as a valid threshold."""
        logger = Logger(tree=["{level} {message}"])
        buf = StringIO()
        with redirect_stdout(buf):
            with logger.timer("fast", level="DEBUG", warnAfter=0):
                time.sleep(0.005)
        out = strip_ansi(buf.getvalue())
        self.assertIn("WARNING", out)

    def test_timer_logs_even_if_body_raises(self):
        """Regression: exceptions inside the context must still log."""
        logger = Logger()
        buf = StringIO()
        with self.assertRaises(RuntimeError):
            with redirect_stdout(buf):
                with logger.timer("boom", level="DEBUG"):
                    raise RuntimeError("kaboom")
        self.assertIn("boom took", strip_ansi(buf.getvalue()))


if __name__ == "__main__":
    unittest.main(verbosity=2)