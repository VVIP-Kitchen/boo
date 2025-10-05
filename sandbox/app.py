import os
import signal
import resource
import tempfile
import subprocess
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class RunRequest(BaseModel):
  code: str
  timeout: int = 5


def run_safely(code: str, timeout: int = 5):
  if timeout > 10:
    timeout = 10

  with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as file:
    file.write(code.encode())
    file_name = file.name

  try:

    def limit_resources():
      resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout))
      mem = 512 * 1024 * 1024
      resource.setrlimit(resource.RLIMIT_AS, (mem, mem))

    result = subprocess.run(
      ["python3", file_name],
      capture_output=True,
      text=True,
      timeout=timeout,
      preexec_fn=limit_resources,
    )

    return {
      "stdout": result.stdout,
      "stderr": result.stderr,
      "exit_code": result.returncode,
    }
  except subprocess.TimeoutExpired:
    return {"error": "Execution timed out"}
  except Exception as e:
    return {"error": str(e)}
  finally:
    os.remove(file_name)


@app.post("/run")
def run_code(req: RunRequest):
  return run_safely(req.code, req.timeout)
