from pathlib import Path

import pytest

from api.sources import Source, find_sources

# Names like the real ones: spaces, a comma, an ampersand, and one name inside another.
NAMES = [
    "Technical Best Practice.pdf",
    "JavaScript, TypeScript & Node.js.pdf",
    "AI Agents.pdf",
    "Generative AI LLMs & AI Agents.pdf",
    "overview.md",
]


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    for name in NAMES:
        (tmp_path / name).touch()
    (tmp_path / "notes.txt").touch()  # not a type that can be shown
    return tmp_path


def test_cited_page_is_found(folder: Path) -> None:
    text = "A model maps to a table [Technical Best Practice.pdf, page 12]."

    assert find_sources(text, folder) == [Source(file="Technical Best Practice.pdf", page=12)]


def test_markdown_file_has_no_page(folder: Path) -> None:
    assert find_sources("See [overview.md].", folder) == [Source(file="overview.md", page=None)]


def test_file_name_with_comma_and_ampersand(folder: Path) -> None:
    text = "[JavaScript, TypeScript & Node.js.pdf, page 3]"

    assert find_sources(text, folder) == [
        Source(file="JavaScript, TypeScript & Node.js.pdf", page=3)
    ]


def test_a_name_inside_another_name_is_not_confused(folder: Path) -> None:
    sources = find_sources("[Generative AI LLMs & AI Agents.pdf, page 2]", folder)

    assert sources == [Source(file="Generative AI LLMs & AI Agents.pdf", page=2)]


def test_several_citations_keep_their_order_without_repeats(folder: Path) -> None:
    text = (
        "[AI Agents.pdf, page 4] and [Technical Best Practice.pdf, page 1] "
        "and again [AI Agents.pdf, page 4] and [AI Agents.pdf, page 5]"
    )

    assert find_sources(text, folder) == [
        Source(file="AI Agents.pdf", page=4),
        Source(file="Technical Best Practice.pdf", page=1),
        Source(file="AI Agents.pdf", page=5),
    ]


def test_citations_joined_with_a_semicolon(folder: Path) -> None:
    sources = find_sources("[AI Agents.pdf, page 1; overview.md]", folder)

    assert sources == [Source(file="AI Agents.pdf", page=1), Source(file="overview.md")]


def test_case_of_the_name_does_not_matter(folder: Path) -> None:
    assert find_sources("[ai agents.PDF, Page 7]", folder) == [Source(file="AI Agents.pdf", page=7)]


@pytest.mark.parametrize(
    "text",
    [
        "[Made Up.pdf, page 1]",  # not in the folder
        "[official docs: https://docs.python.org/3/]",  # not a course file
        "[notes.txt]",  # a type that can not be shown
        "AI Agents.pdf without brackets",
        "numbers[0] and items[1]",
        "",
    ],
)
def test_things_that_are_not_course_files_are_ignored(folder: Path, text: str) -> None:
    assert find_sources(text, folder) == []


def test_missing_folder_gives_no_sources(tmp_path: Path) -> None:
    assert find_sources("[AI Agents.pdf]", tmp_path / "nope") == []
