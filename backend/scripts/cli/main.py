from __future__ import annotations

import typer

from scripts.cli.cmd_data import app as data_app
from scripts.cli.cmd_doctor import doctor
from scripts.cli.cmd_snapshot import app as snapshot_app
from scripts.cli.cmd_status import status
from scripts.cli.cmd_trial import app as trial_app

app = typer.Typer(
    help="BacktestStation operator CLI.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode=None,
)
app.command()(doctor)
app.command()(status)
app.add_typer(data_app, name="data")
app.add_typer(snapshot_app, name="snapshot")
app.add_typer(trial_app, name="trial")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
