"""Blog Authorship Corpus preprocessing (docs/DEVIATIONS.md GAP-10)."""

from data.blogs import PREPROCESSING, _posts


def test_posts_are_whitespace_normalised_and_nul_counts_as_whitespace():
    raw = (b"<Blog><post>\n  first\tpost  </post><post>a\x00b \x00\x00 c</post>"
           b"<post>caf\xe9</post></Blog>")
    assert _posts(raw) == ["first post", "a b c", "café"]


def test_preprocessing_version_is_part_of_the_contract():
    assert PREPROCESSING == 2
