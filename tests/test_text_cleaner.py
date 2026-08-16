from app.services.text_cleaner import clean_html


def test_clean_html():

    raw_html = (
        "&lt;div&gt;"
        "&lt;p&gt;Python &amp; SQL&lt;/p&gt;"
        "&lt;/div&gt;"
    )

    result = clean_html(raw_html)

    assert result == "Python & SQL"


def test_clean_html_empty():

    assert clean_html("") == ""