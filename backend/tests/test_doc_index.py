from src.doc_index import split_page


def test_split_page_packs_paragraphs_and_cuts_long_ones():
    text = "Heavy rain in Swat.\n\nRoads closed in Buner.\n\n" + ("Rescue teams deployed. " * 80)
    chunks = split_page(text, max_chars=200)
    assert chunks[0].startswith("Heavy rain in Swat. Roads closed in Buner.")
    assert all(len(c) <= 200 for c in chunks)
    assert "".join(chunks).replace(" ", "") == text.replace("\n", "").replace(" ", "")
