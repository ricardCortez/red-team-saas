"""Subprocess executor with timeout and streaming output"""
import subprocess
import sys
import time
import os
import signal
import logging
from typing import Optional, List, Callable
from app.core.tool_engine.base_tool import BaseTool, ToolCategory, ToolResult

logger = logging.getLogger(__name__)


class SubprocessExecutor:
    def __init__(
        self,
        timeout: Optional[int] = None,
        output_callback: Optional[Callable[[str], None]] = None,
    ):
        self.timeout = timeout
        self.output_callback = output_callback

    def execute(self, tool: BaseTool, target: str, options: dict) -> ToolResult:
        if not tool.validate_target(target):
            return ToolResult(
                success=False,
                raw_output="",
                error=f"Invalid target: {target}",
            )

        # Safety check: block excessively large brute force attempts
        if tool.category == ToolCategory.BRUTE_FORCE:
            max_attempts = options.get("max_attempts", 0)
            if max_attempts and max_attempts > 10000:
                return ToolResult(
                    success=False,
                    raw_output="",
                    error=f"max_attempts {max_attempts} exceeds safety limit of 10000",
                )

        command = tool.build_command(target, options)
        timeout = options.get("timeout", tool.default_timeout)
        if self.timeout is not None:
            timeout = self.timeout

        start_time = time.time()
        raw_output = ""
        exit_code = -1

        # Build Popen kwargs — preexec_fn is Linux-only
        popen_kwargs: dict = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
        }
        if sys.platform != "win32":
            popen_kwargs["preexec_fn"] = os.setsid

        try:
            process = subprocess.Popen(command, **popen_kwargs)

            lines: List[str] = []
            for line in iter(process.stdout.readline, ""):
                lines.append(line)
                if self.output_callback:
                    try:
                        self.output_callback(line.rstrip())
                    except Exception:
                        pass
                if time.time() - start_time > timeout:
                    self._kill_process(process)
                    return ToolResult(
                        success=False,
                        raw_output="".join(lines),
                        error=f"Timeout after {timeout}s",
                        exit_code=-9,
                        duration_seconds=time.time() - start_time,
                    )

            process.wait()
            raw_output = "".join(lines)
            exit_code = process.returncode

        except FileNotFoundError:
            return ToolResult(
                success=False,
                raw_output="",
                error=f"Binary not found: {tool.binary}",
                exit_code=-1,
                duration_seconds=time.time() - start_time,
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                raw_output=raw_output,
                error=str(exc),
                exit_code=-1,
                duration_seconds=time.time() - start_time,
            )

        duration = time.time() - start_time
        parsed = tool.parse_output(raw_output, exit_code)
        risk_score = tool.get_risk_score(parsed)

        return ToolResult(
            success=exit_code == 0,
            raw_output=raw_output,
            parsed_output=parsed,
            exit_code=exit_code,
            duration_seconds=duration,
            findings=parsed.get("findings", []),
            risk_score=risk_score,
        )

    @staticmethod
    def _kill_process(process: subprocess.Popen) -> None:
        try:
            if sys.platform != "win32":
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.terminate()
        except Exception:
            pass
