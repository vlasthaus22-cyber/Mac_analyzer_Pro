from pdf_service import export_pdf


def main():
    pdf = export_pdf(
        [{"mac": "001122334455", "vendor": "Cisco"}],
        [("mac", "MAC"), ("vendor", "Вендор")],
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
    print("pdf export test passed")


if __name__ == "__main__":
    main()
