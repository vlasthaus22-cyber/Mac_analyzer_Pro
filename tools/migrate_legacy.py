"""Run every legacy SQLite migration in sequence."""

try:
    from .migrate_legacy_history import main as history
    from .migrate_legacy_mappings import main as mappings
    from .migrate_legacy_movements import main as movements
    from .migrate_legacy_stats import main as stats
except ImportError:
    from migrate_legacy_history import main as history
    from migrate_legacy_mappings import main as mappings
    from migrate_legacy_movements import main as movements
    from migrate_legacy_stats import main as stats


def main():
    history()
    movements()
    mappings()
    stats()
    print("legacy migration completed")


if __name__ == "__main__":
    main()
