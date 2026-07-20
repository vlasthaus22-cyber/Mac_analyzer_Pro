try:
    from ._bootstrap import ROOT
except ImportError:
    from _bootstrap import ROOT

from backend.services.system.parity_service import write_parity_status_file


def main() -> None:
    output = write_parity_status_file(ROOT)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
