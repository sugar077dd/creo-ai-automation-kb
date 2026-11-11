"""
run_plan_from_json.py
閻犲洩顕цぐ鍥ㄧ▔閳ь剚绋?plan JSON 闁哄倸娲ｅ▎銏ゆ晬鐏炴儳绲瑰ù婧垮€楃划?MCP_CREO_MechDog 闁圭瑳鍡╂斀闁挎稑鐭侀悿鍡欐嫚閵忕姴鐓傜紓浣规尰濞碱偊鐛捄鍝勬櫢闁哄啨鍎辩换鏃堝Υ?
闁活潿鍔嶇涵?
    python run_plan_from_json.py <plan.json> [--model NAME]
"""
import asyncio
import json
import os
import sys
import traceback

LOG_PATH = r"D:\deepseek\CreoAuto\logs\plan_run.log"

ROOT = r"D:\deepseek\mechdog_extract\MCP_CREO_MechDog-main"
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
SERVER = os.path.join(ROOT, "server.py")


class _Tee:
    """Write both to the original stream and to the log file."""

    def __init__(self, stream, path):
        self._stream = stream
        self._fh = open(path, "a", encoding="utf-8", buffering=1)

    def write(self, s):
        try:
            self._stream.write(s)
        except Exception:
            pass
        try:
            self._fh.write(s)
        except Exception:
            pass
        return len(s)

    def flush(self):
        try:
            self._stream.flush()
        except Exception:
            pass
        try:
            self._fh.flush()
        except Exception:
            pass

    def fileno(self):
        return self._stream.fileno()

    def isatty(self):
        try:
            return self._stream.isatty()
        except Exception:
            return False

    @property
    def encoding(self):
        return getattr(self._stream, "encoding", "utf-8")


async def main(plan_path: str, model_override):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    with open(plan_path, "r", encoding="utf-8") as fh:
        plan = json.load(fh)
    if model_override:
        plan["model_name"] = model_override
    plan.setdefault("model_type", "part")
    # unique model name per run (avoids "already exists in session")
    import time as _time

    _base = plan.get("model_name") or "model"
    plan["model_name"] = _base + "_" + _time.strftime("%H%M%S")
    print("MODEL_NAME", plan["model_name"])

    env = dict(os.environ)
    state = r"D:\deepseek\CreoAuto\run_state"
    os.makedirs(state, exist_ok=True)
    env["LOCALAPPDATA"] = state
    env["TEMP"] = state
    env["TMP"] = state

    params = StdioServerParameters(command=PY, args=[SERVER], cwd=ROOT, env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, args=None):
                res = await session.call_tool(name, args or {})
                return "".join(getattr(c, "text", "") for c in res.content)

            for i in range(15):
                st = await call("creo_session_status")
                try:
                    if json.loads(st).get("connected"):
                        print("CONNECTED (try %d)" % i)
                        break
                except Exception:
                    pass
                await asyncio.sleep(3)
            else:
                print("NOT_CONNECTED", st[:400])
                return 2

            # wait until the startup guard reports ready
            for i in range(30):
                st = await call("creo_startup_status")
                try:
                    j = json.loads(st)
                except Exception:
                    break
                state = j.get("state")
                if i % 3 == 0:
                    print("STARTUP", i, state)
                if state == "ready" and j.get("connected"):
                    break
                if state in ("launch_failed", "configuration_error", "timeout"):
                    print("STARTUP_NOT_READY", st[:400])
                    return 6
                await asyncio.sleep(4)

            res = await call("creo_execute_plan", plan)
            try:
                data = json.loads(res)
            except Exception:
                print("SUBMIT_RAW", res[:1500])
                return 7
            job_id = data.get("job_id")
            print("JOB", job_id, data.get("status"))
            if not job_id:
                print("SUBMIT_FAILED", res[:1000])
                return 3

            for i in range(120):
                await asyncio.sleep(2)
                jr = await call("creo_get_job", {"job_id": job_id})
                try:
                    j = json.loads(jr)
                except Exception:
                    continue
                status = j.get("status")
                stage = j.get("stage")
                if i % 5 == 0:
                    print("POLL", i, status, stage)
                if status in ("succeeded", "failed", "unknown_outcome", "cancelled"):
                    print("FINAL_STATUS", status, stage)
                    print("FINAL_JSON", json.dumps(j, ensure_ascii=False)[:1500])
                    return 0 if status == "succeeded" else 4

            print("TIMEOUT_WAITING_JOB")
            return 5


if __name__ == "__main__":
    try:
        with open(LOG_PATH, "w", encoding="utf-8") as _f:
            _f.write("")
        sys.stdout = _Tee(sys.stdout, LOG_PATH)
        sys.stderr = _Tee(sys.stderr, LOG_PATH)

        if len(sys.argv) < 2:
            print(__doc__)
            raise SystemExit(1)
        plan_file = sys.argv[1]
        model = None
        if "--model" in sys.argv:
            model = sys.argv[sys.argv.index("--model") + 1]
        code = asyncio.run(main(plan_file, model))
    except SystemExit:
        raise
    except BaseException:
        traceback.print_exc()
        code = 9
    raise SystemExit(code)
