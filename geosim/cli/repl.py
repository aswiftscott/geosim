"""Interactive CLI for geosim."""
from __future__ import annotations

import shlex

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style

from geosim.atmosphere.atmosphere import Atmosphere
from geosim.geology.geology import Geology
from geosim.io import store
from geosim.planetology.planetology import Planetology
from geosim.core.world import World, WorldConfig

from .help import GLOBAL_HELP, WORLD_HELP
from .cmd_object import cmd_object
from .cmd_topography import cmd_topography
from .cmd_climate import cmd_climate

_STYLE = Style.from_dict({"prompt": "ansigreen bold"})

_GLOBAL_COMMANDS = ["new", "open", "list", "delete", "help", "exit", "quit"]
_WORLD_COMMANDS = [
    "status", "save", "delete", "planetology", "geology", "topography",
    "atmosphere", "climate", "close", "branch", "help", "exit", "quit",
]


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
                if self._confirm_close():
                    print("\nExiting.")
                    break
                print()  # newline after ^C

            if not text:
                continue

            try:
                parts = shlex.split(text)
            except ValueError as exc:
                print(f"Parse error: {exc}")
                continue

            cmd, args = parts[0].lower(), parts[1:]

            if cmd in ("exit", "quit"):
                if not self._confirm_close():
                    continue
                print("Exiting.")
                break
            elif cmd == "help":
                print(WORLD_HELP if self._world else GLOBAL_HELP)
            elif cmd == "list":
                self._cmd_list()
            elif cmd == "delete":
                self._cmd_delete(args)
            elif cmd == "new":
                self._cmd_new(args)
            elif cmd == "open":
                self._cmd_open(args)
            elif cmd == "close":
                self._cmd_close()
            elif cmd == "status":
                self._cmd_status()
            elif cmd == "save":
                self._cmd_save()
            elif not self._world:
                print("No world open. Use 'new' or 'open' first.")
            elif cmd == "planetology":
                cmd_object(self._world, "planetology", Planetology, args)
            elif cmd == "geology":
                cmd_object(self._world, "geology", Geology, args)
            elif cmd == "atmosphere":
                cmd_object(self._world, "atmosphere", Atmosphere, args)
            elif cmd == "topography":
                cmd_topography(self._world, args)
            elif cmd == "climate":
                cmd_climate(self._world, args)
            elif cmd == "branch":
                print("branch: not yet implemented.")
            else:
                print(f"Unknown command: '{cmd}'. Type 'help' for available commands.")

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
        self._world = World(name=name, config=config)
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

    def _confirm_close(self) -> bool:
        """Prompt the user to save if a world is open. Returns True if it's safe to proceed."""
        if not self._world:
            return True
        confirm = input(
            f"World '{self._world.name}' may have unsaved changes. "
            "Close without saving? [y/N] "
        ).strip().lower()
        return confirm == "y"

    def _cmd_close(self) -> None:
        if not self._world:
            print("No world is currently open.")
            return
        if not self._confirm_close():
            print("Cancelled. Use 'save' to save first.")
            return
        print(f"Closed world '{self._world.name}'.")
        self._world = None

    def _cmd_status(self) -> None:
        if not self._world:
            print("No world is currently open.")
            return
        print(self._world.status())

    def _cmd_save(self) -> None:
        if not self._world:
            print("No world is currently open.")
            return
        store.save_world(self._world)
        print(f"World '{self._world.name}' saved.")

    def _cmd_delete(self, args: list[str]) -> None:
        if self._world:
            self._cmd_delete_object(args)
        else:
            self._cmd_delete_world(args)

    def _cmd_delete_world(self, args: list[str]) -> None:
        if not args:
            print("Usage: delete <world-name>")
            return
        name = args[0]
        if not store.world_exists(name):
            print(f"No world named '{name}' found.")
            return
        confirm = input(f"Delete world '{name}'? This cannot be undone. [y/N] ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return
        store.delete_world(name)
        print(f"World '{name}' deleted.")

    def _cmd_delete_object(self, args: list[str]) -> None:
        _DELETABLE = ("planetology", "geology", "topography", "atmosphere", "climate")
        if not args:
            print(f"Usage: delete <object>  (one of: {', '.join(_DELETABLE)})")
            return
        name = args[0].lower()
        if name not in _DELETABLE:
            print(f"Unknown object '{name}'. Deletable objects: {', '.join(_DELETABLE)}")
            return
        if getattr(self._world, name) is None:
            print(f"This world has no {name} to delete.")
            return
        confirm = input(f"Delete {name} from '{self._world.name}'? This cannot be undone. [y/N] ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return
        setattr(self._world, name, None)
        print(f"Deleted {name} from '{self._world.name}'. Use 'save' to persist.")


def main() -> None:
    GeoSimREPL().run()


if __name__ == "__main__":
    main()
