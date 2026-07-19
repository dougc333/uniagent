# Extract CSS from a model response

extract_css(text) must accept plain CSS or the first ```css/``` fenced block, remove a leading "Here is...:" introduction, strip surrounding whitespace, reject an empty stylesheet with ValueError, and return exactly one trailing newline.
