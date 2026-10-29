"""One isolated process per queued job; safe with multiprocessing on Windows."""
from __future__ import annotations

import json
import os
import re
import multiprocessing
import sys
import time
import traceback
from pathlib import Path

from config import APP_VERSION, CPU_WORKERS, MEMORY_PERCENT
from engine import crossmatch_engine as engine
from services.session_manager import atomic_json


def main(request_path):
    path = Path(request_path)
    request = json.loads(path.read_text(encoding="utf-8"))
    status_path = path.with_name("job.json")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    # The web server and the scoring subprocess share Docker's CPU quota.
    # Reduce Linux scheduler priority of the heavy matching job so health,
    # login and progress endpoints can respond under full CPU pressure.
    # This is best effort, never a prerequisite for processing.
    if os.name == "posix" and os.getenv("CROSSMATCH_BACKGROUND_NICE", "1") == "1":
        try:
            os.nice(5)
        except OSError:
            pass
    status.update(state="running", started_at=time.time(), message="Reading input files.")
    atomic_json(status_path, status)
    def log(message):
        message = str(message)
        print(time.strftime("[%H:%M:%S]"), message, flush=True)
        status.update(message=message, updated_at=time.time())
        indexed = re.search(r"^([AB]): staged ([\d,]+) rows \(([\d,]+) rows/sec\)", message)
        if indexed:
            side, count, speed = indexed.groups()
            status[f"indexed_rows_{side.lower()}"] = int(count.replace(",", ""))
            status[f"rows_per_second_{side.lower()}"] = int(speed.replace(",", ""))
            status["phase"] = f"Indexing File {side}"
        elif 'fast excel conversion' in message.casefold():
            status["phase"] = "Preparing Excel input"
        elif "fuzzy" in message.casefold() and not message.startswith(("A: ", "B: ")):
            status["phase"] = "Fuzzy candidate matching"
        elif 'condition evaluation' in message.casefold():
            status['phase'] = 'Evaluating advanced conditions'
        elif "export" in message.casefold() or "workbook" in message.casefold():
            status["phase"] = "Writing result files"
        elif "verification" in message.casefold():
            status["phase"] = "Verifying exact matches"
        atomic_json(status_path, status)
    try:
        options = engine.ScaleOptions(
            mode=engine.MODE_CROSS if request["mode"] == "cross" else engine.MODE_FILE_A,
            exhaustive=False,  # Web always uses indexed candidate discovery.
            fuzzy=request["fuzzy"], enable_swap=request["swap"],
            keep_one_true_duplicate=bool(request.get("keep_one_true_duplicate",True)) if request["mode"]=="file-a" else False,
            fuzzy_threshold=request["fuzzy_threshold"], min_age=request["min_age"], max_age=request["max_age"],
            cpu_workers=CPU_WORKERS, memory_limit_percent=MEMORY_PERCENT,
            fuzzy_block_limit=0, fuzzy_max_candidates=-1, fuzzy_birth_year_window=-1,
            output_folder=request["output_folder"],
            output_file=str(Path(request["output_folder"]) / "CrossMatch_v6_31_Results.xlsx"),
            source_a_label=request["source_a_name"], source_b_label=request["source_b_name"],
            export_format=request.get("export_format", "xlsx"),
            advanced_conditions=request.get("advanced_conditions"),
        )
        log(
            f"Runtime verification: app_version={APP_VERSION}; engine={engine.ENGINE_VERSION}; "
            f"engine_build={getattr(engine, 'ENGINE_SOURCE_SHA256', 'unknown')}; "
            f"mode={request['mode']}; threshold={options.fuzzy_threshold}; "
            f"effective_workers={engine._safe_process_workers(options)}; "
            f"fuzzy={options.fuzzy}; swap={options.enable_swap}; "
            f"keep_one_p1={('ON' if options.keep_one_true_duplicate else 'OFF') if request['mode']=='file-a' else ('ON' if bool(request.get('keep_one_true_duplicate',True)) else 'OFF') if request['mode']=='sequential' else 'NOT APPLICABLE'}; "
            f"keep_one_p2=NOT APPLICABLE; candidate_strategy=indexed_multi_pass; "
            f"reserve_web_cpu={os.getenv('CROSSMATCH_RESERVE_WEB_CPU', '0')}; "
            f"process_nice={os.nice(0) if os.name == 'posix' else 'not-available'}."
        )
        if request['mode']=='sequential':
            from services.sequential import run_sequential
            result=run_sequential(request,log)
        else:
            result = engine.run_engine(
                request["file_a"], request.get("file_b"), request["sheet_a"], request["sheet_b"],
                request["mapping_a_path"], request.get("mapping_b_path"), options, log,
            )
        status.update(state="completed", phase="Complete", finished_at=time.time(), result=result, message="Completed. Download the result file.")
        atomic_json(status_path, status)
        return 0
    except Exception as exc:
        traceback.print_exc()
        status.update(state="failed", finished_at=time.time(), message=f"{type(exc).__name__}: {exc}")
        atomic_json(status_path, status)
        return 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main(sys.argv[1]))
