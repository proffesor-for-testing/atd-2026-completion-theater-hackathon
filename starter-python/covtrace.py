"""Line-coverage launcher (stdlib only): python covtrace.py app.py [args...]

Runs the target script like `python app.py`, recording which of its lines execute
(including request-handler threads). Data goes to COVERAGE_DIR/<pid>.json. It is
flushed periodically, so a process stopped with a hard kill still leaves data.
Use coverage_report.py rather than calling this directly.
"""
import atexit
import json
import os
from pathlib import Path
import runpy
import signal
import sys
import threading
import time


def main():
    target = str(Path(sys.argv[1]).resolve())
    out = Path(os.environ['COVERAGE_DIR']) / ('%d.json' % os.getpid())
    executed = set()

    def local(frame, event, arg):
        if event == 'line':
            executed.add(frame.f_lineno)
        return local

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != target:
            return None  # other files are not traced: keeps the overhead small
        executed.add(frame.f_lineno)
        return local

    def flush():
        tmp = out.with_suffix('.tmp')
        tmp.write_text(json.dumps({'file': target, 'lines': sorted(list(executed))}))
        os.replace(tmp, out)

    def flusher():
        while True:
            time.sleep(0.2)
            flush()

    atexit.register(flush)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # POSIX: lets atexit run
    threading.Thread(target=flusher, daemon=True).start()
    sys.argv = [target] + sys.argv[2:]
    threading.settrace(tracer)
    sys.settrace(tracer)
    runpy.run_path(target, run_name='__main__')


if __name__ == '__main__':
    main()
