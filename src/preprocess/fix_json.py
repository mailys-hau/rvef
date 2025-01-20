"""
JSON files we got with miscalleneous information are invalid... Fixing it
"""

import click as cli
import json
import re

from pathlib import Path



@cli.command(context_settings={"help_option_names": ["-h", "--help"], "show_default": True})
@cli.argument("jdir", type=cli.Path(exists=True, resolve_path=True, path_type=Path))
@cli.option("--output-directory", "-o", "opath", default="fixed-json",
            type=cli.Path(resolve_path=True, path_type=Path),
            help="Where to store fixed JSONs.")
def fix_json(jdir, opath):
    """
    Reparsing invalid JSONs to make them valid

    \b
    JDIR    PATH    Directory containing broken JSONs.
    """
    opath.mkdir(exist_ok=True, parents=True)
    for subdir in jdir.iterdir():
        # Files are nested
        try:
            jname = next(subdir.glob("*.json"))
        except StopIteration:
            print(f"No JSON found in {subdir.name}, skipping.")
            continue
        with open(jname, 'r') as fd:
            broken = fd.read().split('\n')
            problem = broken[11].replace('}', ']')
            problem = problem.split('{')
            problem[1] = problem[1].replace('"', '')
            fixed = '['.join(problem)
            broken[11] = fixed
            for i in range(11, 14):
                broken[i] += ','
            fixed = '\n'.join(broken)
            oname = opath.joinpath(jname.parent.name)
            oname.mkdir(exist_ok=True)
            with open(oname.joinpath(jname.name), 'w') as fd:
                json.dump(json.loads(fixed), fd, indent=4)



if __name__ == "__main__":
    fix_json()
