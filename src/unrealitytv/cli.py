"""CLI entry point for UnrealityTV."""

import click

from unrealitytv import __version__
from unrealitytv.config import Settings


@click.group()
@click.version_option(__version__, "--version", "-v", help="Show version and exit.")
@click.option(
    "--config",
    type=click.Path(exists=False),
    default=None,
    help="Path to configuration file.",
)
@click.pass_context
def cli(ctx, config):
    """UnrealityTV - automatically detect and skip repetitive segments in reality TV."""
    ctx.ensure_object(dict)
    if config:
        ctx.obj["config"] = Settings(_env_file=config)
    else:
        ctx.obj["config"] = Settings()


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--output", type=click.Path(), default=None, help="Output JSON file path."
)
@click.option(
    "--model-size",
    type=click.Choice(["base", "small", "medium", "large"]),
    default="base",
    help="Transcription model size.",
)
@click.pass_context
def analyze(ctx, file_path, output, model_size):
    """Analyze a video file for skip segments."""
    click.echo("Analysis not yet implemented")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.pass_context
def scan(ctx, directory):
    """Scan a directory for new episodes and analyze them."""
    click.echo("Scanner not yet implemented")


@cli.command()
@click.pass_context
def status(ctx):
    """Show database status - episode and segment counts."""
    click.echo("Episode count: 0")
    click.echo("Segment count: 0")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Show what would be injected without doing it.")
@click.pass_context
def inject(ctx, file_path, dry_run):
    """Inject skip markers into Plex for an analyzed episode."""
    click.echo("Marker injection not yet implemented")
