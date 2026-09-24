from pathlib import Path


DATASET_ROOT = Path(
    "data/chest_xray_validator"
)

SPLITS = (
    "train",
    "validation",
    "test",
)

CLASSES = (
    "NOT_CHEST_XRAY",
    "CHEST_XRAY",
)

EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
}


def count_images(
    directory: Path,
) -> int:

    return sum(
        1
        for path in directory.rglob("*")
        if (
            path.is_file()
            and path.suffix.lower()
            in EXTENSIONS
        )
    )


def main() -> None:

    total = 0

    for split in SPLITS:

        print(
            f"\n[{split.upper()}]"
        )

        for class_name in CLASSES:

            directory = (
                DATASET_ROOT
                / split
                / class_name
            )

            if not directory.is_dir():
                raise RuntimeError(
                    "Missing directory: "
                    f"{directory}"
                )

            count = count_images(
                directory
            )

            total += count

            print(
                f"{class_name}: {count}"
            )

    print(
        "\nTotal:",
        total,
    )


if __name__ == "__main__":
    main()