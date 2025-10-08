from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import TypeAlias

import yaml

try:
    import psutil  # สำหรับ Windows pause/resume
except Exception:  # pragma: no cover
    psutil = None

LOG_DIR = Path("output") / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_python(cmd: list[str]) -> list[str]:
    """
    หากคำสั่งเริ่มด้วย "python" จะพยายามแทนด้วย ENV PYTHON_BIN หรือ sys.executable
    เพื่อให้ Windows ใช้ interpreter ใน venv ได้ถูกต้อง
    """
    if not cmd:
        return cmd
    first = cmd[0].lower()
    if first == "python":
        py = os.getenv("PYTHON_BIN") or sys.executable
        cmd = [py] + cmd[1:]
    return cmd


class ProcessJob:
    def __init__(self, agent_key: str, cmd: list[str]):
        self.agent_key = agent_key
        self.cmd = _resolve_python(cmd)
        self.status = (
            "idle"  # idle|starting|running|paused|stopping|stopped|completed|error
        )
        self.progress = 0
        self.log: list[str] = []
        self.proc: asyncio.subprocess.Process | None = None
        self._stdout_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._log_file_path = LOG_DIR / f"{agent_key}.log"

    def _append_file_log(self, text: str):
        try:
            with open(self._log_file_path, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception:
            pass

    async def _read_stream(self, stream: asyncio.StreamReader, prefix: str):
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode(errors="ignore").rstrip("\n")
            self.log.append(f"{prefix}: {text}")
            self._append_file_log(f"{prefix}: {text}")
            # heuristic progress e.g., "progress=42%"
            if "progress=" in text:
                try:
                    pct_str = text.split("progress=")[-1].strip().rstrip("%")
                    pct = int(pct_str)
                    self.progress = max(0, min(100, pct))
                except Exception:
                    pass

    async def start(self):
        if self.status in ("running", "starting", "paused"):
            return
        self.status = "starting"
        msg = f"เริ่มรันคำสั่ง: {' '.join(self.cmd)}"
        self.log.append(msg)
        self._append_file_log(msg)
        try:
            creationflags = 0
            if os.name == "nt":
                import subprocess as sp

                creationflags = getattr(sp, "CREATE_NEW_PROCESS_GROUP", 0)
            self.proc = await asyncio.create_subprocess_exec(
                *self.cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=creationflags,
            )
            self.status = "running"
            if self.proc.stdout:
                self._stdout_task = asyncio.create_task(
                    self._read_stream(self.proc.stdout, "STDOUT")
                )
            if self.proc.stderr:
                self._stderr_task = asyncio.create_task(
                    self._read_stream(self.proc.stderr, "STDERR")
                )
            rc = await self.proc.wait()
            if self._stdout_task:
                await self._stdout_task
            if self._stderr_task:
                await self._stderr_task
            if rc == 0 and self.status not in ("stopped", "stopping"):
                self.status = "completed"
                self.progress = 100
                self.log.append("งานเสร็จสมบูรณ์")
                self._append_file_log("งานเสร็จสมบูรณ์")
            elif self.status not in ("stopped", "stopping"):
                self.status = "error"
                err = f"งานล้มเหลว exit code={rc}"
                self.log.append(err)
                self._append_file_log(err)
        except FileNotFoundError as e:
            self.status = "error"
            msg = f"ไม่พบคำสั่ง: {e}"
            self.log.append(msg)
            self._append_file_log(msg)
        except Exception as e:
            self.status = "error"
            msg = f"ข้อผิดพลาด: {e!r}"
            self.log.append(msg)
            self._append_file_log(msg)

    def _psutil_proc(self):
        if psutil and self.proc and self.proc.pid:
            try:
                return psutil.Process(self.proc.pid)
            except Exception:
                return None
        return None

    def pause(self):
        if self.status == "running" and self.proc:
            try:
                if os.name == "nt":
                    p = self._psutil_proc()
                    if p:
                        p.suspend()
                        self.status = "paused"
                        self.log.append("พักงาน (psutil.suspend)")
                        self._append_file_log("พักงาน (psutil.suspend)")
                    else:
                        self.log.append("ไม่สามารถพักงานได้: psutil ไม่พร้อม")
                else:
                    os.kill(self.proc.pid, signal.SIGSTOP)
                    self.status = "paused"
                    self.log.append("พักงาน (SIGSTOP)")
                    self._append_file_log("พักงาน (SIGSTOP)")
            except Exception as e:
                err = f"พักไม่สำเร็จ: {e!r}"
                self.log.append(err)
                self._append_file_log(err)

    def resume(self):
        if self.status == "paused" and self.proc:
            try:
                if os.name == "nt":
                    p = self._psutil_proc()
                    if p:
                        p.resume()
                        self.status = "running"
                        self.log.append("ดำเนินการต่อ (psutil.resume)")
                        self._append_file_log("ดำเนินการต่อ (psutil.resume)")
                    else:
                        self.log.append("ไม่สามารถดำเนินการต่อได้: psutil ไม่พร้อม")
                else:
                    os.kill(self.proc.pid, signal.SIGCONT)
                    self.status = "running"
                    self.log.append("ดำเนินการต่อ (SIGCONT)")
                    self._append_file_log("ดำเนินการต่อ (SIGCONT)")
            except Exception as e:
                err = f"ดำเนินการต่อไม่สำเร็จ: {e!r}"
                self.log.append(err)
                self._append_file_log(err)

    def stop(self):
        if self.proc and self.status in ("running", "paused", "starting"):
            self.status = "stopping"
            try:
                if os.name != "nt":
                    self.proc.send_signal(signal.SIGTERM)
                    self.log.append("ส่งสัญญาณหยุด (SIGTERM)")
                    self._append_file_log("ส่งสัญญาณหยุด (SIGTERM)")
                else:
                    self.proc.terminate()
                    self.log.append("ส่งคำสั่งหยุดงาน (terminate)")
                    self._append_file_log("ส่งคำสั่งหยุดงาน (terminate)")
            except Exception as e:
                err = f"หยุดไม่สำเร็จ: {e!r}"
                self.log.append(err)
                self._append_file_log(err)
            finally:
                self.status = "stopped"

    def reset(self):
        self.status = "idle"
        self.progress = 0
        self.log.append("รีเซ็ตสถานะงานแล้ว")
        self._append_file_log("รีเซ็ตสถานะงานแล้ว")


PROCESS_JOB_TYPE: TypeAlias = ProcessJob


class Runner:
    def __init__(self, mapping_path: str = "app/agent_commands.yml"):
        with open(mapping_path, encoding="utf-8") as f:
            self.map: dict = yaml.safe_load(f) or {}
        self.jobs: dict[str, ProcessJob] = {}

    def _get_cmd(self, agent_key: str) -> list[str]:
        entry = self.map.get(agent_key) or self.map.get("default") or {}
        cmd = entry.get("cmd") or [
            "python",
            "-c",
            f"print('ยังไม่ได้กำหนดคำสั่งสำหรับ {agent_key}')",
        ]
        return _resolve_python(cmd)

    def get(self, agent_key: str) -> ProcessJob:
        if agent_key not in self.jobs:
            self.jobs[agent_key] = ProcessJob(agent_key, self._get_cmd(agent_key))
        return self.jobs[agent_key]


RUNNER = Runner()
