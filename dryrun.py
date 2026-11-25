import os, runpy
os.environ["DRY"] = "1"
runpy.run_path("course_collect.py", run_name="__main__")
runpy.run_path("station_collect.py", run_name="__main__")
