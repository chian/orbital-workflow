import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tomllib

from .bootstrap import use_method_loop


def main():
    parser = argparse.ArgumentParser(description="Orbital Episode workflow and simulator tools")
    parser.add_argument("--method-loop-source", type=Path,
                        default=Path(__file__).resolve().parents[2] / "OpenChia")
    commands = parser.add_subparsers(dest="command", required=True)
    describe = commands.add_parser("describe", help="Show topology, tool capabilities, and binding status")
    describe.add_argument("--config", type=Path,
                          default=Path(__file__).resolve().parents[1] / "study.toml")
    smoke = commands.add_parser("smoke", help="Run real tools through a finite diagnostic Episode tree")
    smoke.add_argument("--output", type=Path, default=None)
    smoke.add_argument("--config", type=Path,
                       default=Path(__file__).resolve().parents[1] / "study.toml")
    model_probe = commands.add_parser("model-probe", help="Exercise both configured model roles through the existing login")
    model_probe.add_argument("--output", type=Path, default=None)
    model_probe.add_argument("--config", type=Path,
                             default=Path(__file__).resolve().parents[1] / "study.toml")
    simulator_demo = commands.add_parser("simulator-demo", help="Run and plot explicit full/reduced simulator examples")
    simulator_demo.add_argument("--output", type=Path, default=None)
    simulator_demo.add_argument("--config", type=Path,
                                default=Path(__file__).resolve().parents[1] / "study.toml")
    tool = commands.add_parser("tool", help="Execute a JSON tool request against a stored artifact directory")
    tool.add_argument("--artifacts", type=Path, required=True)
    tool.add_argument("--request", type=Path, required=True)
    tool.add_argument("--config", type=Path,
                      default=Path(__file__).resolve().parents[1] / "study.toml")
    run = commands.add_parser("run", help="Run the live adaptive scientific Episode workflow")
    run.add_argument("--output", type=Path, default=None)
    run.add_argument("--config", type=Path,
                     default=Path(__file__).resolve().parents[1] / "study.toml")
    resume = commands.add_parser("resume", help="Restore cached history and continue an interrupted run")
    resume.add_argument("directory", type=Path)
    report = commands.add_parser("report", help="Write plots, measurements and a FAST interpretation of a completed run")
    report.add_argument("directory", type=Path)
    visualize = commands.add_parser("visualize", help="Build an offline interactive player for saved trajectories")
    visualize.add_argument("directory", type=Path)
    visualize.add_argument("--output", type=Path, default=None, help="Output HTML file")
    visualize.add_argument("--serve", action="store_true", help="Serve any active or saved run with live refresh")
    visualize.add_argument("--port", type=int, default=8767, help="Local viewer port (default: 8767)")
    visualize.add_argument("--observation", action="append", help="Observation ID to include in offline export; repeat for a subset (default: all observations)")
    replay_tools = commands.add_parser("replay-tools", help="Freshly execute the saved tool history without changing credit")
    replay_tools.add_argument("directory", type=Path)
    communication_probe = commands.add_parser("communication-probe", help="Exercise typed parent reports with live roles and labelled software fixtures")
    communication_probe.add_argument("--output", type=Path, default=None)
    communication_probe.add_argument("--config", type=Path,
                                     default=Path(__file__).resolve().parents[1] / "study.toml")
    args = parser.parse_args()
    if args.command == "visualize":
        if args.serve:
            if args.output is not None:
                parser.error("--output exports a snapshot; omit --output when using --serve")
            if args.observation:
                parser.error("--observation selects offline exports; choose live observations in the viewer")
            from .viewer_server import serve_viewer
            serve_viewer(args.directory, port=args.port)
            return
        from .visualization import make_viewer
        print(json.dumps(make_viewer(args.directory, args.output, observation_ids=args.observation), indent=2))
        return
    if args.command in {"tool", "simulator-demo"}:
        from .bootstrap import use_method_loop as bootstrap
        bootstrap(args.method_loop_source)
        from .persistence import PersistenceSettings

        settings = PersistenceSettings(**tomllib.loads(args.config.read_text())["persistence"])
        if args.command == "simulator-demo":
            from .simulator_demo import run_demo
            output = args.output or Path(".artifacts") / datetime.now(timezone.utc).strftime("simulator-%Y%m%dT%H%M%S%fZ")
            result = run_demo(output, settings)
        else:
            from .artifacts import Artifacts
            from .tools import ToolDispatcher
            request = json.loads(args.request.read_text())
            result = ToolDispatcher(Artifacts(args.artifacts), settings).execute(
                request["tool"], request["arguments"]).as_record()
        print(json.dumps(result, indent=2))
        return
    if args.command == "model-probe":
        import asyncio
        from .models import probe_models

        output = args.output or Path(".artifacts") / datetime.now(timezone.utc).strftime("models-%Y%m%dT%H%M%S%fZ")
        print(json.dumps(asyncio.run(probe_models(args.config, output)), indent=2))
        return
    method_source = use_method_loop(args.method_loop_source)

    if args.command == "communication-probe":
        import asyncio
        from .communication_probe import probe_communication
        output = args.output or Path(".artifacts") / datetime.now(timezone.utc).strftime("communication-%Y%m%dT%H%M%S%fZ")
        print(json.dumps(asyncio.run(probe_communication(args.config, output)), indent=2))
        return

    if args.command == "replay-tools":
        from .replay import replay_tools
        print(json.dumps(replay_tools(args.directory), indent=2))
        return

    if args.command == "report":
        import asyncio
        from .reporting import report_run
        print(json.dumps(asyncio.run(report_run(args.directory)), indent=2))
        return

    if args.command in {"run", "resume"}:
        import asyncio
        from .scientific import run_scientific
        output = args.directory if args.command == "resume" else args.output or Path(".artifacts") / datetime.now(timezone.utc).strftime("study-%Y%m%dT%H%M%S%fZ")
        config = output / "study.toml" if args.command == "resume" else args.config
        print(json.dumps(asyncio.run(run_scientific(output, config, resume=args.command == "resume")), indent=2))
        return

    from .runtime import CAPABILITIES, Kind

    if args.command == "describe":
        # Describe does not create artifacts or launch simulations.
        available = {"sim.run", "sim.compare", "math.numeric", "math.symbolic", "math.lean"}
        models = tomllib.loads(args.config.read_text())["models"]
        print(json.dumps({
            "method_loop_source": str(method_source),
            "children": {Kind.ROOT: [Kind.MATH, Kind.SIMULATION],
                         Kind.MATH: [Kind.PARTS], Kind.SIMULATION: [Kind.PARTS],
                         Kind.PARTS: [Kind.PARTS]},
            "self_nesting": [Kind.PARTS],
            "capabilities": {kind: [{"tool": name, "implemented": name in available}
                                    for name in names] for kind, names in CAPABILITIES.items()},
            "model_connection": {"transport": models["connection"]["command"],
                                 "FAST": models["FAST"], "REASONING": models["REASONING"],
                                 "routing": models["routing"]},
            "scientific_binding": "run / resume: live decisions, explicit continuous credit, numerical continuation, cached history replay",
            "formal_tool": "Lean is optional; availability and diagnostics are returned as evidence",
        }, indent=2))
        return

    from .smoke import run_probe
    output = args.output or Path(".artifacts") / datetime.now(timezone.utc).strftime("probe-%Y%m%dT%H%M%S%fZ")
    print(json.dumps(run_probe(output, args.config), indent=2))


if __name__ == "__main__":
    main()
