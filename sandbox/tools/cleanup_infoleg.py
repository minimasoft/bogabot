from bs4 import BeautifulSoup
from sys import argv

def clean_html(input_file):
    # Read the content of the input file
    with open(input_file, 'r', encoding='utf-8') as infile:
        html_content = infile.read()

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove <script>, <meta> and <link> tags
    for script in soup(['script', 'meta', 'link']):
        script.decompose()  # Removes the tag completely from the tree

    # Remove comments from the HTML content
    for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.startswith('<!--')):
        comment.extract()
    head_tag = soup.head
    if not head_tag:
        head_tag = soup.new_tag("head")
        soup.html.insert(0, head_tag)

    link_tag = soup.new_tag('link', rel='stylesheet', href='../style.css')
    head_tag.append(link_tag)
    return str(soup)

if __name__ == "__main__":
    input_html = argv[1]  # Path to your input HTML file
    output_html = argv[2]  # Desired path for the cleaned output
    print(f"{input_html} -> {output_html}")

    with open(output_html, 'w', encoding='utf-8') as outfile:
        outfile.write(clean_html(input_html))
