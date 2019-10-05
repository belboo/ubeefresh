portal = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">

    <title>Freshdesk Articles Preview: {{portal}}</title>

    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.4.1.min.js" integrity="sha256-CSXorXvZcTkaix6Yvo6HppcZGetbYMGWSFlBw8HfCJo=" crossorigin="anonymous"></script>
    <link rel="stylesheet" href="static/fresh.css">
    <link rel="shortcut icon" type="image/png" href="https://global.ubeeqo.com/_nuxt/pwaIcons/icon_64.de227d.png">
</head>
<body>
    <div id="article-preview-parent">
        <div class="article-preview" nlang="{{width}}">
            <div class="accordion">
                {{body}}
            </div>
        </div>
    </div>
    <script>
        $(".accordion-header").each( function() {
            $( this ).click(function() {
                if($( this ).parent().attr("accordion-state") == "open") {
                    $( this ).parent().attr("accordion-state", "closed")
                } else {
                    $( this ).parent().attr("accordion-state", "open")
                }
            })
        });
    </script>
</body>
</html>
"""

category = '''
        <div class="accordion-item" accordion-state="closed">
            <div class="accordion-header">
                <div class="accordion-icon"></div>
                <div class="h1">{category_name}</div>
            </div>
            <div class="accordion-collapsible">
                <div class="category-container">
                    {category_contents}
                </div>
            </div>
        </div>'''

category_header = '''
                    <div class="translation-block">
                        <div class="h1">
                            <a class="gs-link" href={href}>{category_name}</a>
                        </div>
                        <div class="category-desc">
                            {category_desc}
                        </div>
                    </div>
'''

row_start_category = '''
                    <div class="row-category">
'''

row_start_article = '''
                    <div class="row-article">
'''

row_start_folder = '''
                    <div class="row-folder">
'''

row_end = '''
                    </div>
'''

folder = '''
                        <div class="translation-block">
                            <h2 class="h2"><a class="gs-link" href={href}>{folder_name}</a></h1>
                        </div>
'''

article = '''
                        <div class="translation-block">
                            <h3 class="h3"><a class="gs-link" href={href}>{article_title}</a></h1>
                            <div class="article-desc">
                                {article_desc}
                            </div>
                        </div>
'''