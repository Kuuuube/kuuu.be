import hashlib
import os
import re
import shutil
import sys

import comrak

BASE_DIRS = ["src"]
BUILD_DIR = "dist"
DIST_SHIFT_DIRS = ["src"]
INDEX_BLACKLIST_DIRS = ["assets"]
BUILD_ASSETS_DIR = "build_deps"
PAGE_ASSETS_DIR = os.path.join(BUILD_ASSETS_DIR, "page_deps")
PAGE_ASSETS_BUILD_DIR = os.path.join(BUILD_DIR, "assets")
COPY_DIRS = []

def walk_dirs(start_dirs):
    files = []
    dirs = start_dirs
    while len(dirs) > 0:
        for item in os.scandir(dirs.pop()):
            if item.is_dir():
                dirs.append(item.path)
            elif item.is_file():
                files.append(item.path)
    return files

def shift_dirs(directory_path):
    for shift_dir in DIST_SHIFT_DIRS:
        directory_path = re.sub("/+", "/", directory_path.replace(shift_dir, "/"))
    return directory_path

def get_html_head(output_html_path):
    replacements = [
        {"target": r"{page_title}", "replacement": output_html_path.split("/")[-1].split(".")[0].replace("_", " ").title()},
        {"target": r"{./styles.css}", "replacement": os.path.relpath(os.path.join(PAGE_ASSETS_BUILD_DIR, "styles.css"), os.path.dirname(output_html_path))},
    ]
    head_html = open("./" + BUILD_ASSETS_DIR + "/head.html").read()
    for replacement in replacements:
        head_html = head_html.replace(replacement["target"], replacement["replacement"])
    return head_html

def markdown_to_html(markdown_string):
    markdown_string = re.sub("(\n|\r){2,}", "\n\n", markdown_string) # remove excessive blank lines
    markdown_string_hash = hashlib.sha256(markdown_string.encode("utf-8")).hexdigest()
    markdown_lines = list(map(str.rstrip, markdown_string.split("\n"))) # strip excess whitespace only on right, left side whitespace is sytactically important

    relative_md_link_regex = r"(?:\]\((?:\.\/[^\s.]*\.md)(?:#[\S]*)?\))" # convert relative linked `.md` links pointing at other markdown files into `.html` links to allow them to function after being converted to html
    subscript_regex = "^-# "
    i = 0
    while i < len(markdown_lines):
        if re.search(subscript_regex, markdown_lines[i]):
            markdown_lines[i] = re.sub(subscript_regex, "<sub>", markdown_lines[i]) + "</sub>"

        relative_md_link_regex_search = re.search(relative_md_link_regex, markdown_lines[i])
        if relative_md_link_regex_search:
            link_span = relative_md_link_regex_search.span()
            markdown_lines[i] = markdown_lines[i][:link_span[0]] + relative_md_link_regex_search[0].replace(".md", ".html") + markdown_lines[i][link_span[1]:]

        i += 1


    # https://docs.rs/comrak/latest/comrak/options/struct.Extension.html
    opts = comrak.ExtensionOptions()
    render = comrak.RenderOptions()
    opts.table = True
    opts.header_id_prefix = ""
    opts.subscript = True
    render.unsafe_ = True

    result_html = comrak.render_markdown("\n".join(markdown_lines), extension_options = opts, render_options = render)

    result_html = "<span id=\"markdown-hash\" title=\"" + markdown_string_hash + "\">" + markdown_string_hash[:7] + "</span>\n" + result_html

    return result_html

def render_html_page(output_html_path, markdown_data):
    output_html = ""
    output_html += get_html_head(output_html_path)
    output_html += "<body>\n"
    output_html += markdown_to_html(markdown_data)
    output_html += "</body>\n"
    return output_html

def get_noindex_dirs(start_dirs):
    dirs = start_dirs
    noindex_dirs = []
    while len(dirs) > 0:
        index_found = False
        current_dir = dirs.pop()
        for item in os.scandir(current_dir):
            if item.is_dir() and item.name not in INDEX_BLACKLIST_DIRS:
                dirs.append(item.path)
            elif item.is_file() and item.name == "index.html":
                index_found = True
        if not index_found:
            noindex_dirs.append(current_dir)
    return noindex_dirs

if __name__ == "__main__":
    if "build.py" not in os.listdir():
        print("Aborting build, build.py not found in cwd. Navigate to build.py's parent directory and try again.")
        sys.exit()
    shutil.rmtree(BUILD_DIR, ignore_errors = True)
    os.makedirs(BUILD_DIR, exist_ok = True)
    shutil.copytree(PAGE_ASSETS_DIR, PAGE_ASSETS_BUILD_DIR, dirs_exist_ok = True)

    for file_path in walk_dirs(BASE_DIRS):
        if file_path.split(".")[-1] == "md":
            markdown_data = open(file_path).read()
            output_html_path = shift_dirs(os.path.join(BUILD_DIR, file_path.split(".")[0] + ".html"))
            os.makedirs("/".join(output_html_path.split("/")[:-1]), exist_ok = True)
            with open(output_html_path, "w") as output_html:
                output_html.write(render_html_page(output_html_path, markdown_data))
        else:
            output_file_path = shift_dirs(os.path.join(BUILD_DIR, file_path))
            os.makedirs("/".join(output_file_path.split("/")[:-1]), exist_ok = True)
            shutil.copyfile(file_path, output_file_path)
