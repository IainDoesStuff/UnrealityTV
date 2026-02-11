import click

@click.group()
def cli():
    """UnrealityTV - Skip unwanted segments in reality TV shows"""
    pass

@cli.command()
def analyze():
    """Analyze a video file for skip segments"""
    click.echo("Analysis not yet implemented")

@cli.command()
def scan():
    """Scan a directory for new video files"""
    click.echo("Scanner not yet implemented")

@cli.command()
def status():
    """Show database status"""
    click.echo("Status not yet implemented")

@cli.command()
def inject():
    """Inject skip markers into Plex"""
    click.echo("Marker injection not yet implemented")