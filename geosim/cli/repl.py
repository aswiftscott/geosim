"""Interactive CLI for geosim."""
from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style

from geosim.core.world import World, WorldConfig
from geosim.io import store

_STYLE = Style.from_dict({"prompt": "ansigreen bold"})

_GLOBAL_COMMANDS = ["new", "open", "list", "help", "exit", "quit"]
_WORLD_COMMANDS = ["status", "close", "branch", "help", "exit", "quit"]

_GLOBAL_HELP = """\
Commands:
  new <name>          create a new world
  open <name>         open an existing world
  list                list all saved worlds
  help                show this message
  exit / quit         exit geosim"""

_WORLD_HELP = """\
Commands (world open):
  status              show world summary
  branch <t> <name>   create a new world branching from time t
  close               close current world without exiting
  help                show this message
  exit / quit         exit geosim"""


class GeoSimREPL:
    def __init__(self) -> None:
        self._world: World | None = None
        self._session: PromptSession = PromptSession()

    @property
    def _prompt(self) -> str:
        if self._world:
            return f"geosim [{self._world.name}] >>> "
        return "geosim >>> "

    @property
    def _completer(self) -> WordCompleter:
        cmds = _WORLD_COMMANDS if self._world else _GLOBAL_COMMANDS
        return WordCompleter(cmds, ignore_case=True)

    def run(self) -> None:
        print("geosim  —  type 'help' for available commands\n")
        while True:
            try:
                text = self._session.prompt(
                    self._prompt,
                    completer=self._completer,
                    style=_STYLE,
                ).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not text:
                continue

            parts = text.split()
            cmd, args = parts[0].lower(), parts[1:]

            if cmd in ("exit", "quit"):
                print("Exiting.")
                break
            elif cmd == "help":
                print(_WORLD_HELP if self._world else _GLOBAL_HELP)
            elif cmd == "list":
                self._cmd_list()
            elif cmd == "new":
                self._cmd_new(args)
            elif cmd == "open":
                self._cmd_open(args)
            elif cmd == "close":
                self._cmd_close()
            elif cmd == "status":
                self._cmd_status()
            elif cmd == "branch":
                self._cmd_branch(args)
            else:
                print(f"Unknown command: '{cmd}'. Type 'help' for available commands.")

    # --- global commands ---

    def _cmd_list(self) -> None:
        worlds = store.list_worlds()
        if worlds:
            print("\n".join(f"  {w}" for w in worlds))
        else:
            print("No saved worlds found.")

    def _cmd_new(self, args: list[str]) -> None:
        if not args:
            print("Usage: new <name>")
            return
        name = args[0]
        if store.world_exists(name):
            print(f"A world named '{name}' already exists. Use 'open {name}' to open it.")
            return
        config = WorldConfig()  # TODO: prompt for config options
        world = World(name=name, config=config)
        store.save_world(world)
        self._world = world
        print(f"Created and opened world '{name}'.")

    def _cmd_open(self, args: list[str]) -> None:
        if not args:
            print("Usage: open <name>")
            return
        name = args[0]
        if not store.world_exists(name):
            print(f"No world named '{name}' found. Use 'new {name}' to create it.")
            return
        self._world = store.load_world(name)
        print(f"Opened world '{name}'.")

    # --- world commands ---

    def _cmd_close(self) -> None:
        if not self._world:
            print("No world is currently open.")
            return
        print(f"Closed world '{self._world.name}'.")
        self._world = None

    def _cmd_status(self) -> None:
        if not self._world:
            print("No world is currently open.")
            return
        print(self._world.status())

    def _cmd_branch(self, args: list[str]) -> None:
        if not self._world:
            print("No world is currently open.")
            return
        # TODO: implement branching
        print("branch: not yet implemented.")


def main() -> None:
    GeoSimREPL().run()


if __name__ == "__main__":
    main()
