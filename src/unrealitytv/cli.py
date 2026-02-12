"""CLI entry point for UnrealityTV."""

import logging
from pathlib import Path

import click

from unrealitytv import __version__
from unrealitytv.analysis import AnalysisPipeline, AnalysisPipelineError
from unrealitytv.config import Settings
from unrealitytv.parsers import parse_episode

logger = logging.getLogger(__name__)


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
    help="Transcription model size (not yet used).",
)
@click.option(
    "--gpu/--no-gpu", default=False, help="Enable GPU acceleration for transcription."
)
@click.pass_context
def analyze(ctx, file_path: str, output: str, model_size: str, gpu: bool) -> None:
    """Analyze a video file for skip segments (recaps and previews)."""
    try:
        file_path_obj = Path(file_path)

        # Parse episode metadata from filename
        logger.info(f"Parsing episode metadata from {file_path}")
        episode = parse_episode(file_path_obj)

        # Create and run analysis pipeline
        click.echo(
            click.style(f"Analyzing: {episode.show_name}", fg="cyan", bold=True)
        )
        pipeline = AnalysisPipeline(gpu_enabled=gpu)
        logger.info(f"Starting analysis pipeline for {episode.file_path}")

        try:
            result = pipeline.analyze(episode)
        finally:
            pipeline.close()

        # Display results
        _display_analysis_results(result)

        # Save to JSON if requested
        if output:
            output_path = Path(output)
            result.to_file(output_path)
            click.echo(
                click.style(
                    f"✓ Analysis results saved to {output_path}",
                    fg="green",
                )
            )
            logger.info(f"Analysis results saved to {output_path}")

    except FileNotFoundError as e:
        logger.error(f"File not found: {file_path}")
        raise click.ClickException(f"File not found: {file_path}") from e
    except AnalysisPipelineError as e:
        logger.error(f"Analysis failed: {e}")
        raise click.ClickException(f"Analysis failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
        raise click.ClickException(f"Unexpected error: {e}") from e


def _display_analysis_results(result) -> None:
    """Display analysis results in a formatted way.

    Args:
        result: AnalysisResult object with episode and segments
    """
    # Episode information
    click.echo()
    click.echo(click.style("Episode Information:", fg="blue", bold=True))
    click.echo(f"  Show: {result.episode.show_name}")
    if result.episode.season:
        click.echo(f"  Season: {result.episode.season}")
    if result.episode.episode:
        click.echo(f"  Episode: {result.episode.episode}")
    if result.episode.duration_ms:
        duration_sec = result.episode.duration_ms // 1000
        duration_str = _format_duration(duration_sec)
        click.echo(f"  Duration: {duration_str}")

    # Segments found
    click.echo()
    click.echo(
        click.style(
            f"Detected {len(result.segments)} skip segment(s):",
            fg="blue",
            bold=True,
        )
    )

    if result.segments:
        click.echo()
        for i, segment in enumerate(result.segments, 1):
            start_str = _format_duration(segment.start_ms // 1000)
            end_str = _format_duration(segment.end_ms // 1000)
            duration = (segment.end_ms - segment.start_ms) // 1000
            duration_str = _format_duration(duration)
            confidence_pct = int(segment.confidence * 100)

            click.echo(
                f"  {i}. [{start_str} - {end_str}] "
                f"({duration_str}) "
                f"{click.style(segment.segment_type.upper(), fg='yellow')} "
                f"{confidence_pct}%"
            )
            click.echo(f"     {segment.reason}")
    else:
        click.echo(click.style("  No segments detected", fg="green"))

    click.echo()


def _format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


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
