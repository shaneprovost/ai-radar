# Custom Digest Directory Feature

## Summary

Added `--digest-dir` option to the `ai-radar digest` command to allow users to override the digest output directory on a per-run basis.

## Changes Made

### 1. CLI Update (`src/ai_radar/cli.py`)

**Line 99-105:** Added new option to `digest` command:
```python
@click.option("--digest-dir", default=None, help="Override digest output directory (default: from profile)")
def digest_cmd(force: bool, test_slack: bool, sources: Optional[str], dry_run: bool, digest_dir: Optional[str]):
```

**Line 186:** Pass digest_dir to render_digest function:
```python
digest_path = render_digest(suggestions, profile, total_reviewed, source_names, digest_dir=digest_dir)
```

### 2. Markdown Renderer Update (`src/ai_radar/delivery/markdown.py`)

**Line 12-28:** Updated function signature and directory resolution logic:
```python
def render_digest(
    suggestions: list[Suggestion],
    profile: Profile,
    total_reviewed: int,
    sources_used: list[str],
    date: Optional[datetime] = None,
    digest_dir: Optional[str] = None,
) -> Path:
    """Render digest markdown and write to file. Returns the file path."""
    if date is None:
        date = datetime.now()

    # Use override directory if provided, otherwise fall back to profile config, then default
    if digest_dir:
        output_dir = Path(digest_dir).expanduser()
    else:
        output_dir = Path(profile.delivery.digest_dir).expanduser() if profile.delivery.digest_dir else DIGEST_DIR

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"{date.strftime('%Y-%m-%d')}.md"
```

## Usage

### Default behavior (uses profile config):
```bash
ai-radar digest
```
Output: `~/projects/jamesNotes/digest/YYYY-MM-DD.md` (as configured in profile)

### Override with custom directory:
```bash
ai-radar digest --digest-dir ~/custom/path/to/digests
```
Output: `~/custom/path/to/digests/YYYY-MM-DD.md`

### One-time digest to specific location:
```bash
ai-radar digest --digest-dir /tmp/ai-radar --force
```
Output: `/tmp/ai-radar/YYYY-MM-DD.md`

## Priority Order

1. **Command-line `--digest-dir`** (highest priority)
2. **Profile `delivery.digest_dir`** (from `~/.config/ai-radar/profile.yaml`)
3. **Default `DIGEST_DIR`** (from `config/paths.py`, typically `~/ai-radar/digests`)

## Benefits

- **Flexibility**: Users can generate digests to different locations without modifying their profile
- **Testing**: Easy to test digest generation in temporary directories
- **Organization**: Different digest locations for different purposes (personal, work, etc.)
- **Backwards compatible**: Existing behavior unchanged when option is not used

## Testing

Tested with:
```bash
# Dry run with custom directory
ai-radar digest --dry-run --force --digest-dir /tmp/test-digest

# Help text
ai-radar digest --help
```

## Future Enhancements

Potential additions:
- `--digest-filename` option to customize the filename format
- Environment variable support (e.g., `AI_RADAR_DIGEST_DIR`)
- Multiple digest directories for different profiles
