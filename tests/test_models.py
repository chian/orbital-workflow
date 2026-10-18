"""App-server maintenance events preserve the workflow-owned execution boundary."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, call, patch

from orbital_workflow.bootstrap import use_method_loop
use_method_loop(Path(__file__).resolve().parents[2] / "OpenChia")

from orbital_workflow.models import ModelCallError, _SessionConnection
from orbital_workflow.tools import ToolDispatcher


CONFIG = {
    "connection": {"command": ["codex", "app-server", "--stdio"]},
    "FAST": {"model": "gpt-6-luna", "reasoning_effort": "none"},
    "REASONING": {"model": "gpt-6-sol", "reasoning_effort": "medium"},
    "routing": {"decide": "REASONING", "synthesize_report": "FAST"},
}


def item_notification(lifecycle, item):
    # Shape verified against local `codex app-server generate-json-schema`:
    # v2/ItemStartedNotification.json and v2/ItemCompletedNotification.json.
    params = {"threadId": "thread-fixture", "turnId": "turn-fixture", "item": item}
    params["startedAtMs" if lifecycle == "started" else "completedAtMs"] = 0
    return {"method": "item/" + lifecycle, "params": params}


class ModelTransportMaintenance(unittest.IsolatedAsyncioTestCase):
    def connection(self, directory):
        connection = _SessionConnection(CONFIG, directory / "transport", directory)
        connection._session = AsyncMock(return_value="thread-fixture")
        connection._rpc = AsyncMock(return_value={"turn": {"id": "turn-fixture"}})
        return connection

    async def test_context_compaction_is_logged_without_response_fragments_or_scientific_execution(self):
        response = {"action": "child", "child_kind": "simulation_investigation"}
        events = [
            item_notification("started", {"type": "contextCompaction", "id": "compaction-fixture"}),
            item_notification("completed", {"type": "contextCompaction", "id": "compaction-fixture"}),
            item_notification("completed", {"type": "agentMessage", "id": "answer-fixture",
                "text": json.dumps(response), "phase": "final_answer"}),
            {"method": "turn/completed", "params": {"threadId": "thread-fixture",
                "turn": {"id": "turn-fixture", "status": "completed"}}},
        ]
        for buffered in (False, True):
            with self.subTest(buffered=buffered), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                connection = self.connection(directory)
                if buffered:
                    connection.pending.extend(events)
                    connection._read = AsyncMock(side_effect=AssertionError("No more events expected"))
                else:
                    connection._read = AsyncMock(side_effect=events)
                # Model completion may return one proposed action. It never
                # acquires a scientific tool or advances an Episode itself.
                with patch.object(ToolDispatcher, "execute") as execute:
                    actual = await connection.complete("episode-fixture", "REASONING", "instructions",
                        {"task": "propose one action"}, {"type": "object"})
                self.assertEqual(actual, response)
                self.assertEqual(connection.call_index, 1)
                execute.assert_not_called()
                connection._rpc.assert_awaited_once()
                self.assertEqual(connection._rpc.await_args.args[0], "turn/start")
                call_directory = directory / "transport/call-00001"
                self.assertEqual((call_directory / "response.txt").read_text(), json.dumps(response))
                self.assertEqual([json.loads(line) for line in
                    (call_directory / "events.jsonl").read_text().splitlines()], events)
                self.assertFalse((call_directory / "error.json").exists())

    async def test_command_execution_is_still_interrupted_and_refused(self):
        for lifecycle in ("started", "completed"):
            with self.subTest(lifecycle=lifecycle), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                connection = self.connection(directory)
                connection._read = AsyncMock(side_effect=[item_notification(lifecycle,
                    {"type": "commandExecution", "id": "command-fixture"})])
                with self.assertRaisesRegex(ModelCallError, "Model attempted commandExecution"):
                    await connection.complete("episode-fixture", "REASONING", "instructions", {}, {})
                self.assertEqual(connection._rpc.await_count, 2)
                self.assertEqual(connection._rpc.await_args,
                    call("turn/interrupt", {"threadId": "thread-fixture", "turnId": "turn-fixture"}))
                call_directory = directory / "transport/call-00001"
                self.assertFalse((call_directory / "response.json").exists())
                self.assertIn("commandExecution", json.loads(
                    (call_directory / "error.json").read_text())["message"])


if __name__ == "__main__":
    unittest.main()
