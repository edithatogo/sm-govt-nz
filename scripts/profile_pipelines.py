#!/usr/bin/env python
"""Profile the social media archiving feed/archive ingestion and dedupe."""

import cProfile
import pstats
import io
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console

console = Console()

# Base directory for this repo
BASE_DIR = Path(__file__).parent.parent


def profile_cli():
    """Profile the CLI entry point."""
    console.print("[bold cyan]Profiling CLI...[/bold cyan]")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        from scripts.cli import main as cli_main
        console.print("[yellow]CLI imported (full run requires CLI args)[/yellow]")
    except ImportError as e:
        console.print(f"[red]Could not import CLI: {e}[/red]")
    
    profiler.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(30)
    console.print(s.getvalue())
    
    output_path = BASE_DIR / "logs" / "profile_cli.txt"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(s.getvalue())
    console.print(f"[green]Profile saved to {output_path}[/green]")

def profile_archive_bluesky():
    """Profile Bluesky archiving."""
    console.print("[bold cyan]Profiling archive_bluesky...[/bold cyan]")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        from scripts.archive_bluesky_history import main as bluesky_main
        from scripts.archive_bluesky_profiles import main as profiles_main
        console.print("[yellow]Bluesky archive modules imported[/yellow]")
    except ImportError as e:
        console.print(f"[red]Could not import Bluesky modules: {e}[/red]")
    
    profiler.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(30)
    console.print(s.getvalue())
    
    output_path = BASE_DIR / "logs" / "profile_archive_bluesky.txt"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(s.getvalue())
    console.print(f"[green]Profile saved to {output_path}[/green]")


def profile_archive_rss():
    """Profile RSS archiving."""
    console.print("[bold cyan]Profiling archive_rss...[/bold cyan]")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        from scripts.archive_rss_history import main as rss_main
        console.print("[yellow]RSS archive module imported[/yellow]")
    except ImportError as e:
        console.print(f"[red]Could not import RSS module: {e}[/red]")
    
    profiler.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(30)
    console.print(s.getvalue())
    
    output_path = BASE_DIR / "logs" / "profile_archive_rss.txt"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(s.getvalue())
    console.print(f"[green]Profile saved to {output_path}[/green]")

def profile_compile_registry():
    """Profile registry compilation."""
    console.print("[bold cyan]Profiling compile_registry...[/bold cyan]")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        from scripts.compile_registry import main as registry_main
        console.print("[yellow]compile_registry imported[/yellow]")
    except ImportError as e:
        console.print(f"[red]Could not import compile_registry: {e}[/red]")
    
    profiler.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(30)
    console.print(s.getvalue())
    
    output_path = BASE_DIR / "logs" / "profile_compile_registry.txt"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(s.getvalue())
    console.print(f"[green]Profile saved to {output_path}[/green]")


def profile_dedupe():
    """Profile dedupe logic."""
    console.print("[bold cyan]Profiling dedupe/check_noop_diff...[/bold cyan]")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        from scripts.check_noop_diff import main as noop_main
        console.print("[yellow]check_noop_diff imported[/yellow]")
    except ImportError as e:
        console.print(f"[red]Could not import check_noop_diff: {e}[/red]")
    
    profiler.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(30)
    console.print(s.getvalue())
    
    output_path = BASE_DIR / "logs" / "profile_dedupe.txt"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(s.getvalue())
    console.print(f"[green]Profile saved to {output_path}[/green]")

def profile_publish_archives():
    """Profile archive publishing."""
    console.print("[bold cyan]Profiling publish_archives...[/bold cyan]")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        from scripts.publish_archives import main as publish_main
        console.print("[yellow]publish_archives imported[/yellow]")
    except ImportError as e:
        console.print(f"[red]Could not import publish_archives: {e}[/red]")
    
    profiler.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(30)
    console.print(s.getvalue())
    
    output_path = BASE_DIR / "logs" / "profile_publish_archives.txt"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(s.getvalue())
    console.print(f"[green]Profile saved to {output_path}[/green]")


def profile_verify_mirrors():
    """Profile mirror verification."""
    console.print("[bold cyan]Profiling verify_archive_mirror...[/bold cyan]")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        from scripts.verify_archive_mirror_posts import main as verify_main
        console.print("[yellow]verify_archive_mirror_posts imported[/yellow]")
    except ImportError as e:
        console.print(f"[red]Could not import verify_archive_mirror_posts: {e}[/red]")
    
    profiler.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(30)
    console.print(s.getvalue())
    
    output_path = BASE_DIR / "logs" / "profile_verify_mirrors.txt"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(s.getvalue())
    console.print(f"[green]Profile saved to {output_path}[/green]")


def main():
    """Run all profiling tasks."""
    console.print("[bold]Starting sm-govt-nz profiling[/bold]")
    
    # Ensure logs directory exists
    (BASE_DIR / "logs").mkdir(exist_ok=True)
    
    # Run profiles
    profile_cli()
    profile_archive_bluesky()
    profile_archive_rss()
    profile_compile_registry()
    profile_dedupe()
    profile_publish_archives()
    profile_verify_mirrors()
    
    console.print("[bold green]Profiling complete![/bold green]")


if __name__ == "__main__":
    main()
