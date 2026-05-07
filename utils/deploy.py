"""
פריסת מסמכי קרן ל-Google Drive (מותקן כתיקייה מקומית).
Deployment = shutil.copy2 to mirrored directory structure.
"""

import shutil
import logging
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table

from config import settings

logger = logging.getLogger(__name__)
console = Console()


def deploy_fund_docs(output_dir: Path) -> None:
    """
    מעתיק קבצי .md מ-output_dir לנתיב Google Drive המקומי.
    Silent no-op if GOOGLE_DRIVE_DEPLOY_PATH is not configured.
    Never raises — build success is never affected.
    """
    deploy_root: Path | None = settings.GOOGLE_DRIVE_DEPLOY_PATH
    if not deploy_root:
        return

    try:
        _do_deploy(output_dir, deploy_root)
    except Exception as exc:
        logger.warning(f"Google Drive deploy failed (non-fatal): {exc}")
        console.print(
            f"[yellow]⚠ Google Drive deploy warning:[/yellow] {exc}\n"
            "[dim]Build succeeded — files were NOT copied to Google Drive.[/dim]"
        )


def _do_deploy(output_dir: Path, deploy_root: Path) -> None:
    """Internal deploy logic. May raise; caller handles exceptions."""

    # Mirror: output_dir relative to Fund_Docs/ → under deploy_root
    relative_subdir = output_dir.relative_to(settings.OUTPUT_DIR)
    target_dir = deploy_root / relative_subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy all .md files from output_dir
    md_files: List[Path] = sorted(output_dir.glob("*.md"))
    deployed: List[tuple[str, str]] = []
    for src in md_files:
        dst = target_dir / src.name
        shutil.copy2(src, dst)
        deployed.append((src.name, str(dst)))

    # Copy CHANGELOG.md to deploy root
    changelog_src = settings.OUTPUT_DIR / "CHANGELOG.md"
    if changelog_src.exists():
        changelog_dst = deploy_root / "CHANGELOG.md"
        shutil.copy2(changelog_src, changelog_dst)
        deployed.append(("CHANGELOG.md", str(changelog_dst)))

    # Rich output
    if deployed:
        console.print()
        table = Table(
            title="[bold green]Deployed to Google Drive[/bold green]",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("File", style="white")
        table.add_column("Destination", style="dim")
        for name, dst_path in deployed:
            table.add_row(name, dst_path)
        console.print(table)
        console.print(
            f"[green]✓[/green] {len(deployed)} file(s) deployed to "
            f"[cyan]{deploy_root}[/cyan]"
        )
