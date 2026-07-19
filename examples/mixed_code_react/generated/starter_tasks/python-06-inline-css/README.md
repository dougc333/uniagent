# Inline exactly one stylesheet

html_with_inline_css(html, css) must replace exactly one link element whose rel is stylesheet with a style element containing css. Support single or double quotes and an optional self-closing slash. Raise ValueError unless exactly one stylesheet link was replaced.
